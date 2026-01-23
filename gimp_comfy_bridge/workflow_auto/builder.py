"""
Workflow Builder for automatic ComfyUI workflow generation.

This module provides the main WorkflowBuilder class that assembles ComfyUI
node graphs based on templates, styles, and user requirements.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass, field

from ..shared.config import Config
from ..shared.types import WorkflowTemplate, Style, WorkflowGraph
from .graph import NodeGraph, Node, Connection
from .rules import RuleEngine
from .validator import WorkflowValidator
from .cache import WorkflowCache

# Import brand kit components
from ..brandkit import BrandKitApplier, load_brandkit

logger = logging.getLogger(__name__)


@dataclass
class BuildOptions:
    """Options for workflow building."""
    optimize: bool = True
    validate: bool = True
    cache_enabled: bool = True
    max_nodes: int = 100
    timeout: float = 30.0
    include_previews: bool = True
    style_strength: float = 1.0
    template_variation: str = "default"
    brand_kit_id: Optional[str] = None
    # Remote execution options
    prefer_remote: bool = False
    force_remote: bool = False
    remote_node_id: Optional[str] = None
    remote_fallback: bool = True  # Fall back to local if remote fails


@dataclass
class BuildResult:
    """Result of workflow building."""
    success: bool
    workflow: Optional[WorkflowGraph] = None
    graph: Optional[NodeGraph] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    build_time: float = 0.0
    node_count: int = 0
    cache_hit: bool = False


class WorkflowBuilder:
    """
    Main workflow builder for automatic ComfyUI workflow generation.

    This class orchestrates the creation of ComfyUI workflows by combining
    templates, styles, and user options using rule-based assembly.
    """

    def __init__(self, config: Config):
        """
        Initialize the workflow builder.

        Args:
            config: Application configuration
        """
        self.config = config
        self.rule_engine = RuleEngine(config)
        self.validator = WorkflowValidator(config)
        self.cache = WorkflowCache(config)

        # Node type mappings for different operations
        self.node_mappings = self._load_node_mappings()

    def _load_node_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Load ComfyUI node type mappings."""
        return {
            "loaders": {
                "CheckpointLoaderSimple": "4.1",
                "CLIPTextEncode": "4.6",
                "VAELoader": "4.2",
                "LoraLoader": "4.3"
            },
            "samplers": {
                "KSampler": "3.1",
                "SamplerCustom": "3.2"
            },
            "image_processors": {
                "ImageScale": "5.1",
                "ImageComposite": "5.2",
                "ImageBlur": "5.3"
            },
            "outputs": {
                "SaveImage": "9.1",
                "PreviewImage": "9.2"
            }
        }

    async def build_workflow(
        self,
        template: WorkflowTemplate,
        style: Optional[Style] = None,
        options: Optional[BuildOptions] = None
    ) -> BuildResult:
        """
        Build a ComfyUI workflow from template and style.

        Args:
            template: Workflow template to build from
            style: Optional style to apply
            options: Build options

        Returns:
            BuildResult with workflow or errors
        """
        import time
        start_time = time.time()

        if options is None:
            options = BuildOptions()

        try:
            # Check if remote execution is requested
            if options.force_remote or options.prefer_remote:
                remote_result = await self._try_remote_build(template, style, options)
                if remote_result:
                    remote_result.build_time = time.time() - start_time
                    return remote_result
                elif options.force_remote:
                    return BuildResult(
                        success=False,
                        errors=["Remote execution failed and force_remote=True"],
                        build_time=time.time() - start_time
                    )
                # Fall back to local execution if prefer_remote and fallback enabled

            # Check cache first
            cache_key = self._generate_cache_key(template, style, options)
            if options.cache_enabled:
                cached_result = await self.cache.get(cache_key)
                if cached_result:
                    logger.info(f"Cache hit for workflow: {cache_key}")
                    return BuildResult(
                        success=True,
                        workflow=cached_result,
                        cache_hit=True,
                        build_time=time.time() - start_time
                    )

            # Create node graph
            graph = NodeGraph()

            # Apply template structure
            await self._apply_template(graph, template, options)

            # Apply style modifications
            if style:
                await self._apply_style(graph, style, options)

            # Apply brand kit if specified
            if options.brand_kit_id:
                try:
                    brand_kit = await load_brandkit(options.brand_kit_id)
                    if brand_kit:
                        applier = BrandKitApplier()
                        await applier.apply_to_workflow(graph, brand_kit, options)
                        logger.info(f"Applied brand kit '{options.brand_kit_id}' to workflow")
                    else:
                        logger.warning(f"Brand kit '{options.brand_kit_id}' not found")
                except Exception as e:
                    logger.error(f"Failed to apply brand kit '{options.brand_kit_id}': {e}")
                    if options.strict_mode:
                        return BuildResult(
                            success=False,
                            errors=[f"Brand kit application failed: {e}"],
                            build_time=time.time() - start_time
                        )

            # Optimize graph if requested
            if options.optimize:
                await self._optimize_graph(graph)

            # Validate graph
            if options.validate:
                validation_result = await self.validator.validate_graph(graph)
                if not validation_result.valid:
                    return BuildResult(
                        success=False,
                        errors=validation_result.errors,
                        warnings=validation_result.warnings,
                        build_time=time.time() - start_time
                    )

            # Convert to ComfyUI workflow format
            workflow = await self._graph_to_workflow(graph)

            # Cache result
            if options.cache_enabled:
                await self.cache.set(cache_key, workflow)

            return BuildResult(
                success=True,
                workflow=workflow,
                graph=graph,
                warnings=[],  # Could collect warnings during build
                build_time=time.time() - start_time,
                node_count=len(graph.nodes)
            )

        except Exception as e:
            logger.error(f"Workflow build failed: {e}")
            return BuildResult(
                success=False,
                errors=[f"Build failed: {str(e)}"],
                build_time=time.time() - start_time
            )

    async def _try_remote_build(
        self,
        template: WorkflowTemplate,
        style: Optional[Style] = None,
        options: BuildOptions = None
    ) -> Optional[BuildResult]:
        """
        Attempt to build workflow remotely.

        Args:
            template: Workflow template
            style: Optional style
            options: Build options

        Returns:
            BuildResult if successful, None if remote execution not available
        """
        try:
            # Import remote execution components
            from ..async_engine.api import submit_remote_task, is_remote_available

            if not is_remote_available():
                logger.debug("Remote execution not available")
                return None

            # Prepare build parameters
            build_params = {
                'template': template.__dict__,
                'style': style.__dict__ if style else None,
                'options': {
                    'optimize': options.optimize,
                    'validate': options.validate,
                    'cache_enabled': options.cache_enabled,
                    'max_nodes': options.max_nodes,
                    'timeout': options.timeout,
                    'include_previews': options.include_previews,
                    'style_strength': options.style_strength,
                    'template_variation': options.template_variation,
                }
            }

            # Submit remote build task
            task_id = submit_remote_task(
                operation='build_workflow',
                parameters=build_params,
                node_id=options.remote_node_id,
                timeout_seconds=options.timeout,
                metadata={'build_type': 'remote', 'template_id': template.id}
            )

            # Wait for completion (with timeout)
            import time
            start_wait = time.time()
            while time.time() - start_wait < options.timeout:
                from ..async_engine.api import get_task_status
                status = get_task_status(task_id)
                if status and status['state'] in ['completed', 'failed']:
                    break
                await asyncio.sleep(0.5)

            # Get final result
            from ..async_engine.api import get_task_status
            final_status = get_task_status(task_id)

            if final_status and final_status['state'] == 'completed' and final_status['result']:
                result_data = final_status['result']
                workflow_data = result_data.get('workflow')
                if workflow_data:
                    # Convert back to WorkflowGraph
                    from ..shared.types import WorkflowGraph
                    workflow = WorkflowGraph(**workflow_data)
                    return BuildResult(
                        success=True,
                        workflow=workflow,
                        node_count=result_data.get('node_count', 0)
                    )
            elif final_status and final_status['state'] == 'failed':
                logger.warning(f"Remote build failed: {final_status.get('result', {}).get('error', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Remote build attempt failed: {e}")

        return None

    async def _apply_template(
        self,
        graph: NodeGraph,
        template: WorkflowTemplate,
        options: BuildOptions
    ) -> None:
        """Apply template structure to the graph."""
        # Add base nodes from template
        for node_data in template.nodes:
            node = Node(
                id=node_data.get("id", f"node_{len(graph.nodes)}"),
                type=node_data["type"],
                position=node_data.get("position", {"x": 0, "y": 0}),
                properties=node_data.get("properties", {}),
                inputs=node_data.get("inputs", {}),
                outputs=node_data.get("outputs", {})
            )
            graph.add_node(node)

        # Add connections from template
        for conn_data in template.connections:
            connection = Connection(
                source=conn_data["source"],
                target=conn_data["target"],
                source_output=conn_data.get("source_output", 0),
                target_input=conn_data.get("target_input", 0)
            )
            graph.add_connection(connection)

    async def _apply_style(
        self,
        graph: NodeGraph,
        style: Style,
        options: BuildOptions
    ) -> None:
        """Apply style modifications to the graph."""
        # Apply style-specific node modifications
        style_mods = await self.rule_engine.get_style_modifications(style)

        for mod in style_mods:
            if mod["type"] == "add_node":
                node = Node(
                    id=mod["node_id"],
                    type=mod["node_type"],
                    properties=mod.get("properties", {}),
                    position=mod.get("position", {"x": 0, "y": 0})
                )
                graph.add_node(node)

            elif mod["type"] == "modify_node":
                if mod["node_id"] in graph.nodes:
                    node = graph.nodes[mod["node_id"]]
                    if "properties" in mod:
                        node.properties.update(mod["properties"])

            elif mod["type"] == "add_connection":
                connection = Connection(
                    source=mod["source"],
                    target=mod["target"],
                    source_output=mod.get("source_output", 0),
                    target_input=mod.get("target_input", 0)
                )
                graph.add_connection(connection)

    async def _optimize_graph(self, graph: NodeGraph) -> None:
        """Optimize the node graph for performance."""
        # Remove unused nodes
        used_nodes = set()
        for conn in graph.connections:
            used_nodes.add(conn.source)
            used_nodes.add(conn.target)

        unused_nodes = set(graph.nodes.keys()) - used_nodes
        for node_id in unused_nodes:
            if not self._is_output_node(graph.nodes[node_id]):
                del graph.nodes[node_id]

        # Optimize node ordering (simple topological sort)
        # This is a simplified version - real implementation would be more sophisticated
        pass

    def _is_output_node(self, node: Node) -> bool:
        """Check if node is an output node that should be preserved."""
        return node.type in ["SaveImage", "PreviewImage", "VHS_VideoCombine"]

    async def _graph_to_workflow(self, graph: NodeGraph) -> WorkflowGraph:
        """Convert NodeGraph to ComfyUI workflow format."""
        workflow = WorkflowGraph(
            nodes=[],
            connections=[],
            metadata={
                "version": "1.0",
                "generated_by": "comfy-gimpy-studio",
                "node_count": len(graph.nodes)
            }
        )

        # Convert nodes
        for node_id, node in graph.nodes.items():
            workflow.nodes.append({
                "id": node_id,
                "type": node.type,
                "pos": [node.position["x"], node.position["y"]],
                "properties": node.properties,
                "inputs": node.inputs,
                "outputs": node.outputs
            })

        # Convert connections
        for conn in graph.connections:
            workflow.connections.append({
                "source": conn.source,
                "source_output": conn.source_output,
                "target": conn.target,
                "target_input": conn.target_input
            })

        return workflow

    def build_workflow_for_template(self, category: str,
                                   layout_elements: List[Dict[str, Any]],
                                   style_requirements: List[str],
                                   dimensions: Tuple[int, int],
                                   quality: str = "standard") -> Dict[str, Any]:
        """
        Build a workflow specifically for template generation.

        Args:
            category: Template category
            layout_elements: Layout elements from template
            style_requirements: Required styles
            dimensions: Template dimensions
            quality: Quality level

        Returns:
            Workflow data dictionary
        """
        try:
            logger.info(f"Building workflow for {category} template")

            # Create basic workflow structure
            workflow = {
                "nodes": {},
                "links": [],
                "groups": [],
                "config": {
                    "category": category,
                    "dimensions": dimensions,
                    "quality": quality,
                    "style_requirements": style_requirements
                }
            }

            # Add loader nodes
            self._add_template_loaders(workflow, quality)

            # Add processing nodes based on layout elements
            self._add_template_processors(workflow, layout_elements, dimensions)

            # Add style application nodes
            self._add_template_styles(workflow, style_requirements)

            # Add output nodes
            self._add_template_outputs(workflow, dimensions)

            # Create connections
            self._connect_template_workflow(workflow)

            logger.info(f"Template workflow built with {len(workflow['nodes'])} nodes")
            return workflow

        except Exception as e:
            logger.error(f"Template workflow building failed: {e}")
            return {}

    def _add_template_loaders(self, workflow: Dict[str, Any], quality: str):
        """Add loader nodes to template workflow."""
        nodes = workflow["nodes"]

        # Model loader
        model_name = self._get_model_for_quality(quality)
        nodes["1"] = {
            "id": "1",
            "type": "CheckpointLoaderSimple",
            "pos": [100, 100],
            "properties": {"model": model_name}
        }

        # CLIP text encoder
        nodes["2"] = {
            "id": "2",
            "type": "CLIPTextEncode",
            "pos": [100, 200],
            "properties": {"text": "professional template"}
        }

        # VAE loader
        nodes["3"] = {
            "id": "3",
            "type": "VAELoader",
            "pos": [100, 300],
            "properties": {"vae": "vae-ft-mse-840000-ema-pruned.safetensors"}
        }

    def _add_template_processors(self, workflow: Dict[str, Any],
                               layout_elements: List[Dict[str, Any]],
                               dimensions: Tuple[int, int]):
        """Add processing nodes based on layout elements."""
        nodes = workflow["nodes"]
        node_id = 4

        width, height = dimensions

        # KSampler for main generation
        nodes[str(node_id)] = {
            "id": str(node_id),
            "type": "KSampler",
            "pos": [400, 100],
            "properties": {
                "seed": 0,
                "steps": 20,
                "cfg": 8.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "width": width,
                "height": height
            }
        }
        node_id += 1

        # Add image processors based on layout elements
        for element in layout_elements:
            if element.get("type") == "image":
                nodes[str(node_id)] = {
                    "id": str(node_id),
                    "type": "ImageScale",
                    "pos": [700, 100 + (node_id - 4) * 100],
                    "properties": {
                        "width": element.get("width", 300),
                        "height": element.get("height", 200),
                        "method": "lanczos"
                    }
                }
                node_id += 1

    def _add_template_styles(self, workflow: Dict[str, Any], style_requirements: List[str]):
        """Add style application nodes."""
        nodes = workflow["nodes"]
        node_id = len(nodes) + 1

        # Add LoRA loaders for styles
        for style in style_requirements[:3]:  # Limit to 3 styles
            nodes[str(node_id)] = {
                "id": str(node_id),
                "type": "LoraLoader",
                "pos": [200, 100 + (node_id - len(nodes)) * 100],
                "properties": {
                    "lora_name": f"{style}.safetensors",
                    "strength_model": 1.0,
                    "strength_clip": 1.0
                }
            }
            node_id += 1

    def _add_template_outputs(self, workflow: Dict[str, Any], dimensions: Tuple[int, int]):
        """Add output nodes."""
        nodes = workflow["nodes"]
        node_id = len(nodes) + 1

        # Save image node
        nodes[str(node_id)] = {
            "id": str(node_id),
            "type": "SaveImage",
            "pos": [1000, 200],
            "properties": {
                "filename_prefix": "template_generated",
                "output_path": "output"
            }
        }

        # Preview image node
        nodes[str(node_id + 1)] = {
            "id": str(node_id + 1),
            "type": "PreviewImage",
            "pos": [1000, 300],
            "properties": {}
        }

    def _connect_template_workflow(self, workflow: Dict[str, Any]):
        """Create connections between template workflow nodes."""
        links = workflow["links"]

        # Basic connections for template generation
        # Model -> KSampler
        links.append(["1", 0, "4", 0])  # Checkpoint -> KSampler.model

        # CLIP -> KSampler
        links.append(["2", 0, "4", 1])  # CLIP -> KSampler.positive

        # VAE -> KSampler
        links.append(["3", 0, "4", 2])  # VAE -> KSampler.vae

        # KSampler -> SaveImage
        links.append(["4", 0, "5", 0])  # KSampler -> SaveImage

        # KSampler -> PreviewImage
        links.append(["4", 0, "6", 0])  # KSampler -> PreviewImage

    def _get_model_for_quality(self, quality: str) -> str:
        """Get appropriate model for quality level."""
        models = {
            "draft": "sdxl_base_0.9.safetensors",
            "standard": "sdxl_base_1.0.safetensors",
            "high": "sdxl_refiner_1.0.safetensors"
        }
        return models.get(quality, models["standard"])

    def _generate_cache_key(
        self,
        template: WorkflowTemplate,
        style: Optional[Style],
        options: BuildOptions
    ) -> str:
        """Generate cache key for workflow."""
        import hashlib

        key_parts = [
            template.id,
            template.version,
            style.id if style else "no-style",
            str(options.style_strength),
            options.template_variation
        ]

        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    async def get_available_templates(self) -> List[Dict[str, Any]]:
        """Get list of available workflow templates."""
        # This would integrate with template system
        return []

    async def get_template_info(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a template."""
        # This would integrate with template system
        return None

    async def validate_template(self, template: WorkflowTemplate) -> Dict[str, Any]:
        """Validate a workflow template."""
        return await self.validator.validate_template(template)