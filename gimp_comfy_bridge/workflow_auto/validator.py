"""
Workflow Validator for ComfyUI workflow validation.

This module provides validation logic for ComfyUI workflows and node graphs
to ensure they are well-formed and executable.
"""

import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from pathlib import Path

from ..shared.config import Config
from ..shared.types import WorkflowTemplate, WorkflowGraph
from .graph import NodeGraph, Node, Connection

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of workflow validation."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class NodeTypeInfo:
    """Information about a ComfyUI node type."""
    name: str
    category: str
    inputs: Dict[str, Dict[str, Any]]
    outputs: Dict[str, Dict[str, Any]]
    properties: Dict[str, Any]
    required_inputs: Set[str] = field(default_factory=set)


class WorkflowValidator:
    """
    Validator for ComfyUI workflows and node graphs.

    This class provides comprehensive validation for workflows including
    node connectivity, type checking, and execution feasibility.
    """

    def __init__(self, config: Config):
        """
        Initialize workflow validator.

        Args:
            config: Application configuration
        """
        self.config = config
        self.node_types = self._load_node_types()

    def _load_node_types(self) -> Dict[str, NodeTypeInfo]:
        """Load ComfyUI node type definitions."""
        # This would typically load from ComfyUI's node definitions
        # For now, we'll define some common node types
        return {
            "CheckpointLoaderSimple": NodeTypeInfo(
                name="CheckpointLoaderSimple",
                category="loaders",
                inputs={},
                outputs={"MODEL": {"type": "MODEL"}, "CLIP": {"type": "CLIP"}, "VAE": {"type": "VAE"}},
                properties={"ckpt_name": {"type": "string", "required": True}},
                required_inputs=set()
            ),
            "CLIPTextEncode": NodeTypeInfo(
                name="CLIPTextEncode",
                category="conditioning",
                inputs={"clip": {"type": "CLIP"}},
                outputs={"CONDITIONING": {"type": "CONDITIONING"}},
                properties={"text": {"type": "string", "required": True}},
                required_inputs={"clip"}
            ),
            "VAELoader": NodeTypeInfo(
                name="VAELoader",
                category="loaders",
                inputs={},
                outputs={"VAE": {"type": "VAE"}},
                properties={"vae_name": {"type": "string", "required": True}},
                required_inputs=set()
            ),
            "KSampler": NodeTypeInfo(
                name="KSampler",
                category="sampling",
                inputs={
                    "model": {"type": "MODEL"},
                    "positive": {"type": "CONDITIONING"},
                    "negative": {"type": "CONDITIONING"},
                    "latent_image": {"type": "LATENT"}
                },
                outputs={"LATENT": {"type": "LATENT"}},
                properties={
                    "seed": {"type": "int", "default": 0},
                    "steps": {"type": "int", "default": 20},
                    "cfg": {"type": "float", "default": 8.0},
                    "sampler_name": {"type": "string", "default": "euler"},
                    "scheduler": {"type": "string", "default": "normal"},
                    "denoise": {"type": "float", "default": 1.0}
                },
                required_inputs={"model", "positive", "negative"}
            ),
            "VAEDecode": NodeTypeInfo(
                name="VAEDecode",
                category="latent",
                inputs={"samples": {"type": "LATENT"}, "vae": {"type": "VAE"}},
                outputs={"IMAGE": {"type": "IMAGE"}},
                properties={},
                required_inputs={"samples", "vae"}
            ),
            "SaveImage": NodeTypeInfo(
                name="SaveImage",
                category="image",
                inputs={"images": {"type": "IMAGE"}, "filename_prefix": {"type": "string"}},
                outputs={},
                properties={"filename_prefix": {"type": "string", "default": "ComfyUI"}},
                required_inputs={"images"}
            ),
            "LoraLoader": NodeTypeInfo(
                name="LoraLoader",
                category="loaders",
                inputs={"model": {"type": "MODEL"}, "clip": {"type": "CLIP"}},
                outputs={"MODEL": {"type": "MODEL"}, "CLIP": {"type": "CLIP"}},
                properties={
                    "lora_name": {"type": "string", "required": True},
                    "strength_model": {"type": "float", "default": 1.0},
                    "strength_clip": {"type": "float", "default": 1.0}
                },
                required_inputs={"model", "clip"}
            ),
            "EmptyLatentImage": NodeTypeInfo(
                name="EmptyLatentImage",
                category="latent",
                inputs={},
                outputs={"LATENT": {"type": "LATENT"}},
                properties={
                    "width": {"type": "int", "default": 512},
                    "height": {"type": "int", "default": 512},
                    "batch_size": {"type": "int", "default": 1}
                },
                required_inputs=set()
            )
        }

    async def validate_graph(self, graph: NodeGraph) -> ValidationResult:
        """
        Validate a node graph.

        Args:
            graph: NodeGraph to validate

        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []
        suggestions = []

        # Basic graph structure validation
        graph_result = graph.validate_graph()
        if not graph_result["valid"]:
            errors.extend(graph_result["errors"])

        # Node type validation
        for node_id, node in graph.nodes.items():
            node_result = await self._validate_node(node)
            errors.extend([f"Node {node_id}: {err}" for err in node_result.errors])
            warnings.extend([f"Node {node_id}: {warn}" for warn in node_result.warnings])

        # Connection validation
        for conn in graph.connections:
            conn_result = await self._validate_connection(graph, conn)
            errors.extend([f"Connection {conn.source}->{conn.target}: {err}" for err in conn_result.errors])
            warnings.extend([f"Connection {conn.source}->{conn.target}: {warn}" for warn in conn_result.warnings])

        # Workflow execution validation
        exec_result = await self._validate_execution_order(graph)
        errors.extend(exec_result.errors)
        warnings.extend(exec_result.warnings)
        suggestions.extend(exec_result.suggestions)

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )

    async def validate_workflow(self, workflow: WorkflowGraph) -> ValidationResult:
        """
        Validate a ComfyUI workflow.

        Args:
            workflow: WorkflowGraph to validate

        Returns:
            ValidationResult with errors and warnings
        """
        # Convert workflow to graph and validate
        graph = await self._workflow_to_graph(workflow)
        return await self.validate_graph(graph)

    async def validate_template(self, template: WorkflowTemplate) -> ValidationResult:
        """
        Validate a workflow template.

        Args:
            template: Template to validate

        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []
        suggestions = []

        # Check required template fields
        if not template.id:
            errors.append("Template ID is required")
        if not template.name:
            errors.append("Template name is required")
        if not template.type:
            errors.append("Template type is required")

        # Validate version format (semver)
        if not self._is_valid_version(template.version):
            errors.append(f"Invalid version format: {template.version}")

        # Validate nodes
        if not template.nodes:
            errors.append("Template must contain at least one node")
        else:
            for i, node in enumerate(template.nodes):
                if not node.get("type"):
                    errors.append(f"Node {i} missing type")
                if not node.get("id"):
                    warnings.append(f"Node {i} missing ID (will be auto-generated)")

        # Validate connections
        for i, conn in enumerate(template.connections):
            if not conn.get("source"):
                errors.append(f"Connection {i} missing source")
            if not conn.get("target"):
                errors.append(f"Connection {i} missing target")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )

    async def _validate_node(self, node: Node) -> ValidationResult:
        """Validate a single node."""
        errors = []
        warnings = []

        # Check if node type exists
        if node.type not in self.node_types:
            errors.append(f"Unknown node type: {node.type}")
            return ValidationResult(valid=False, errors=errors)

        node_info = self.node_types[node.type]

        # Check required properties
        for prop_name, prop_info in node_info.properties.items():
            if prop_info.get("required", False) and prop_name not in node.properties:
                errors.append(f"Missing required property: {prop_name}")

        # Check required inputs
        for required_input in node_info.required_inputs:
            if required_input not in node.inputs:
                errors.append(f"Missing required input: {required_input}")

        # Validate property types
        for prop_name, prop_value in node.properties.items():
            if prop_name in node_info.properties:
                expected_type = node_info.properties[prop_name]["type"]
                if not self._validate_property_type(prop_value, expected_type):
                    warnings.append(f"Property {prop_name} type mismatch (expected {expected_type})")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    async def _validate_connection(self, graph: NodeGraph, connection: Connection) -> ValidationResult:
        """Validate a connection between nodes."""
        errors = []
        warnings = []

        source_node = graph.nodes.get(connection.source)
        target_node = graph.nodes.get(connection.target)

        if not source_node:
            errors.append(f"Source node {connection.source} does not exist")
            return ValidationResult(valid=False, errors=errors)

        if not target_node:
            errors.append(f"Target node {connection.target} does not exist")
            return ValidationResult(valid=False, errors=errors)

        # Check if nodes have the required input/output slots
        source_info = self.node_types.get(source_node.type)
        target_info = self.node_types.get(target_node.type)

        if source_info and target_info:
            # Check output exists
            if connection.source_output >= len(source_info.outputs):
                errors.append(f"Source node has no output slot {connection.source_output}")

            # Check input exists
            if connection.target_input >= len(target_info.inputs):
                errors.append(f"Target node has no input slot {connection.target_input}")

            # Check type compatibility
            source_outputs = list(source_info.outputs.values())
            target_inputs = list(target_info.inputs.values())

            if (connection.source_output < len(source_outputs) and
                connection.target_input < len(target_inputs)):
                source_type = source_outputs[connection.source_output]["type"]
                target_type = target_inputs[connection.target_input]["type"]

                if source_type != target_type:
                    warnings.append(f"Type mismatch: {source_type} -> {target_type}")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    async def _validate_execution_order(self, graph: NodeGraph) -> ValidationResult:
        """Validate that the workflow can be executed in topological order."""
        errors = []
        warnings = []
        suggestions = []

        try:
            execution_order = graph.get_topological_order()

            # Check for potential execution issues
            output_nodes = []
            for node_id in execution_order:
                node = graph.nodes[node_id]
                if self._is_output_node(node):
                    output_nodes.append(node_id)

            if not output_nodes:
                warnings.append("No output nodes found (SaveImage, etc.)")

            # Suggest optimizations
            if len(execution_order) > 50:
                suggestions.append("Consider breaking large workflows into smaller components")

        except ValueError as e:
            errors.append(f"Execution order validation failed: {e}")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )

    def _is_output_node(self, node: Node) -> bool:
        """Check if node is an output node."""
        return node.type in ["SaveImage", "PreviewImage", "VHS_VideoCombine"]

    def _validate_property_type(self, value: Any, expected_type: str) -> bool:
        """Validate property type."""
        if expected_type == "string":
            return isinstance(value, str)
        elif expected_type == "int":
            return isinstance(value, int)
        elif expected_type == "float":
            return isinstance(value, (int, float))
        elif expected_type == "boolean":
            return isinstance(value, bool)
        return True  # Unknown types pass validation

    def _is_valid_version(self, version: str) -> bool:
        """Check if version string is valid semver."""
        import re
        semver_pattern = r'^\d+\.\d+\.\d+(-[\w\.\-]+)?(\+[\w\.\-]+)?$'
        return bool(re.match(semver_pattern, version))

    async def _workflow_to_graph(self, workflow: WorkflowGraph) -> NodeGraph:
        """Convert WorkflowGraph to NodeGraph."""
        graph = NodeGraph()

        # Add nodes
        for node_data in workflow.nodes:
            node = Node(
                id=node_data["id"],
                type=node_data["type"],
                position=node_data.get("pos", [0, 0]),
                properties=node_data.get("properties", {}),
                inputs=node_data.get("inputs", {}),
                outputs=node_data.get("outputs", {})
            )
            graph.add_node(node)

        # Add connections
        for conn_data in workflow.connections:
            connection = Connection(
                source=conn_data["source"],
                target=conn_data["target"],
                source_output=conn_data.get("source_output", 0),
                target_input=conn_data.get("target_input", 0)
            )
            graph.add_connection(connection)

        return graph

    async def get_node_type_info(self, node_type: str) -> Optional[NodeTypeInfo]:
        """
        Get information about a node type.

        Args:
            node_type: Node type name

        Returns:
            NodeTypeInfo if found, None otherwise
        """
        return self.node_types.get(node_type)

    async def list_available_node_types(self) -> List[str]:
        """
        Get list of available node types.

        Returns:
            List of node type names
        """
        return list(self.node_types.keys())

    def add_custom_node_type(self, node_info: NodeTypeInfo) -> None:
        """
        Add a custom node type definition.

        Args:
            node_info: Node type information
        """
        self.node_types[node_info.name] = node_info
        logger.info(f"Added custom node type: {node_info.name}")