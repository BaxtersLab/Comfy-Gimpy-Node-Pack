"""
Template Generator for Comfy Gimpy Studio (Phase 12)

Main entry point for AI-assisted template generation, coordinating
layout building, metadata generation, preview creation, and saving.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

from ..shared.types import TemplateCategory, StyleMetadata
from ..shared.config import Config
from ..templates import TemplateRegistry
from ..styles import StyleRegistry
from ..workflow_auto import WorkflowBuilder
from ..fusion import FusionEngine
from ..async_engine import submit_task, TaskPriority

# Import brand kit components
from ..brandkit import BrandKitApplier, load_brandkit

# Import layout optimization components
from ..layout_opt import LayoutAnalyzer, LayoutOptimizer, LayoutVariants, OverlayGenerator

from .layout_builder import LayoutBuilder
from .metadata_builder import MetadataBuilder
from .preview_builder import PreviewBuilder
from .variants import VariantGenerator
from .save import TemplateSaver

logger = logging.getLogger(__name__)


@dataclass
class GenerationOptions:
    """Options for template generation."""

    category: TemplateCategory
    base_style: Optional[str] = None
    brand_kit: Optional[str] = None
    dimensions: tuple[int, int] = (1920, 1080)
    generate_variants: bool = True
    variant_count: int = 3
    include_previews: bool = True
    include_workflow: bool = True
    quality: str = "high"  # "draft", "standard", "high"
    seed: Optional[int] = None

    # Advanced options
    layout_complexity: str = "medium"  # "simple", "medium", "complex"
    color_variations: bool = True
    typography_variations: bool = True
    style_blend_ratio: float = 0.7

    # Layout optimization options
    optimize_layout: bool = True
    layout_optimization_level: str = "standard"  # "basic", "standard", "advanced"
    generate_layout_overlays: bool = False
    layout_variant_strategies: Optional[List[str]] = None


class TemplateGenerator:
    """Main template generator coordinating all generation steps."""

    def __init__(self,
                 template_registry: TemplateRegistry,
                 style_registry: StyleRegistry,
                 workflow_builder: WorkflowBuilder,
                 fusion_engine: FusionEngine,
                 config: Config):
        """
        Initialize the template generator.

        Args:
            template_registry: Template registry for accessing existing templates
            style_registry: Style registry for accessing styles
            workflow_builder: Workflow auto-generation builder
            fusion_engine: Style fusion engine
            config: Application configuration
        """
        self.template_registry = template_registry
        self.style_registry = style_registry
        self.workflow_builder = workflow_builder
        self.fusion_engine = fusion_engine
        self.config = config

        # Initialize sub-components
        self.layout_builder = LayoutBuilder(config)
        self.metadata_builder = MetadataBuilder()
        self.preview_builder = PreviewBuilder(workflow_builder, fusion_engine, config)
        self.variant_generator = VariantGenerator()
        self.template_saver = TemplateSaver(config)

        # Initialize layout optimization components
        self.layout_analyzer = LayoutAnalyzer()
        self.layout_optimizer = LayoutOptimizer()
        self.layout_variants = LayoutVariants()
        self.overlay_generator = OverlayGenerator()

        logger.info("Template generator initialized")

    def generate_template(self, options: GenerationOptions) -> Dict[str, Any]:
        """
        Generate a new template from scratch.

        Args:
            options: Generation options

        Returns:
            Dictionary with generation results and metadata
        """
        try:
            logger.info(f"Generating template for category: {options.category.value}")

            # Step 1: Generate base layout
            layout_data = self._generate_base_layout(options)

            # Step 1.5: Optimize layout if requested
            layout_overlays = None
            if options.optimize_layout:
                layout_data, layout_overlays = await self._optimize_layout(options, layout_data)

            # Step 2: Apply brand kit if specified
            brand_kit = None
            if options.brand_kit:
                try:
                    brand_kit = load_brandkit(options.brand_kit)
                    logger.info(f"Loaded brand kit '{options.brand_kit}' for template generation")
                except Exception as e:
                    logger.warning(f"Failed to load brand kit '{options.brand_kit}': {e}")

            # Step 3: Generate metadata
            metadata = self._generate_metadata(options, layout_data, brand_kit)

            # Step 3: Generate workflow
            workflow_data = self._generate_workflow(options, layout_data, metadata)

            # Step 4: Generate previews
            previews = self._generate_previews(options, layout_data, workflow_data)

            # Step 5: Save template
            template_path = self._save_template(options, layout_data, metadata, workflow_data, previews)

            # Step 6: Generate variants if requested
            variants = []
            if options.generate_variants:
                variants = self._generate_variants(options, template_path)

            result = {
                "success": True,
                "template_path": str(template_path),
                "metadata": metadata,
                "layout_elements": len(layout_data.get("elements", [])),
                "previews_generated": len(previews),
                "variants_generated": len(variants),
                "variants": variants,
                "generation_time": datetime.now().isoformat(),
                "layout_optimized": options.optimize_layout,
                "layout_overlays": layout_overlays.to_dict() if layout_overlays else None,
                "options": options
            }

            logger.info(f"Template generated successfully: {metadata.name}")
            return result

        except Exception as e:
            logger.error(f"Template generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "options": options
            }

    def generate_variants(self, template_path: Union[str, Path], count: int = 3) -> List[Dict[str, Any]]:
        """
        Generate variants of an existing template.

        Args:
            template_path: Path to existing template
            count: Number of variants to generate

        Returns:
            List of variant generation results
        """
        try:
            template_path = Path(template_path)
            logger.info(f"Generating {count} variants for template: {template_path.name}")

            variants = self.variant_generator.generate_variants(template_path, count)

            logger.info(f"Generated {len(variants)} variants")
            return variants

        except Exception as e:
            logger.error(f"Variant generation failed: {e}")
            return []

    def _generate_base_layout(self, options: GenerationOptions) -> Dict[str, Any]:
        """
        Generate the base layout structure.

        Args:
            options: Generation options

        Returns:
            Layout data dictionary
        """
        logger.debug("Generating base layout")

        # Get style information if specified
        style_data = None
        if options.base_style:
            style_data = self.style_registry.get_style(options.base_style)

        # Generate layout
        layout_data = self.layout_builder.build_layout(
            category=options.category,
            dimensions=options.dimensions,
            style_data=style_data,
            complexity=options.layout_complexity,
            brand_kit=options.brand_kit
        )

        return layout_data

    def _generate_metadata(self, options: GenerationOptions, layout_data: Dict[str, Any], brand_kit=None) -> Any:
        """
        Generate template metadata.

        Args:
            options: Generation options
            layout_data: Generated layout data
            brand_kit: Optional brand kit to apply

        Returns:
            TemplateMetadata object
        """
        logger.debug("Generating metadata")

        # Apply brand kit to layout data if available
        if brand_kit:
            applier = BrandKitApplier(brand_kit)
            layout_data = applier.apply_to_template(layout_data)

        # Get style information
        style_info = None
        if options.base_style:
            style_info = self.style_registry.get_style_metadata(options.base_style)

        # Generate metadata
        metadata = self.metadata_builder.build_metadata(
            category=options.category,
            layout_data=layout_data,
            style_info=style_info,
            brand_kit=options.brand_kit,
            quality=options.quality
        )

        return metadata

    def _generate_workflow(self, options: GenerationOptions,
                          layout_data: Dict[str, Any],
                          metadata: Any) -> Dict[str, Any]:
        """
        Generate ComfyUI workflow for the template.

        Args:
            options: Generation options
            layout_data: Layout data
            metadata: Template metadata

        Returns:
            Workflow data dictionary
        """
        logger.debug("Generating workflow")

        if not options.include_workflow:
            return {}

        # Use workflow builder to generate appropriate workflow
        workflow_data = self.workflow_builder.build_workflow_for_template(
            category=options.category,
            layout_elements=layout_data.get("elements", []),
            style_requirements=metadata.recommended_styles,
            dimensions=options.dimensions,
            quality=options.quality
        )

        return workflow_data

    def _generate_previews(self, options: GenerationOptions,
                          layout_data: Dict[str, Any],
                          workflow_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate preview images.

        Args:
            options: Generation options
            layout_data: Layout data
            workflow_data: Workflow data

        Returns:
            List of preview data
        """
        logger.debug("Generating previews")

        if not options.include_previews:
            return []

        previews = self.preview_builder.generate_previews(
            layout_data=layout_data,
            workflow_data=workflow_data,
            style_name=options.base_style,
            dimensions=options.dimensions,
            quality=options.quality
        )

        return previews

    def _save_template(self, options: GenerationOptions,
                      layout_data: Dict[str, Any],
                      metadata: Any,
                      workflow_data: Dict[str, Any],
                      previews: List[Dict[str, Any]]) -> Path:
        """
        Save the generated template.

        Args:
            options: Generation options
            layout_data: Layout data
            metadata: Template metadata
            workflow_data: Workflow data
            previews: Preview data

        Returns:
            Path to saved template
        """
        logger.debug("Saving template")

        template_path = self.template_saver.save_template(
            layout_data=layout_data,
            metadata=metadata,
            workflow_data=workflow_data,
            previews=previews,
            category=options.category
        )

        return template_path

    async def _optimize_layout(self, options: GenerationOptions, layout_data: Dict[str, Any]) -> tuple[Dict[str, Any], Optional[Any]]:
        """
        Optimize the generated layout using AI-driven analysis.

        Args:
            options: Generation options
            layout_data: Initial layout data

        Returns:
            Tuple of (optimized_layout_data, overlays)
        """
        try:
            logger.debug("Optimizing layout")

            # Analyze current layout
            analysis = await self.layout_analyzer.analyze_layout(layout_data)

            # Generate optimization actions
            actions = await self.layout_optimizer.optimize_layout(
                analysis,
                level=options.layout_optimization_level
            )

            # Apply optimizations to layout data
            optimized_layout = await self.layout_optimizer.apply_actions(layout_data, actions)

            # Generate overlays if requested
            overlays = None
            if options.generate_layout_overlays:
                overlays = await self.overlay_generator.generate_overlays(
                    analysis,
                    actions
                )

            logger.info(f"Layout optimized with {len(actions)} actions")
            return optimized_layout, overlays

        except Exception as e:
            logger.warning(f"Layout optimization failed: {e}")
            # Return original layout if optimization fails
            return layout_data, None

    def _generate_variants(self, options: GenerationOptions, template_path: Path) -> List[Dict[str, Any]]:
        """
        Generate template variants.

        Args:
            options: Generation options
            template_path: Path to base template

        Returns:
            List of variant results
        """
        logger.debug(f"Generating {options.variant_count} variants")

        variants = self.variant_generator.generate_variants(
            template_path=template_path,
            count=options.variant_count,
            color_variations=options.color_variations,
            typography_variations=options.typography_variations
        )

        return variants

    def generate_template_async(self, options: GenerationOptions,
                               callback: Optional[callable] = None) -> str:
        """
        Generate a template asynchronously.

        Args:
            options: Generation options
            callback: Optional callback function

        Returns:
            Task ID for tracking
        """
        def _async_generate():
            result = self.generate_template(options)
            if callback:
                callback(result)
            return result

        task_id = submit_task(
            task_func=_async_generate,
            priority=TaskPriority.NORMAL,
            description=f"Generate {options.category.value} template"
        )

        logger.info(f"Template generation task submitted: {task_id}")
        return task_id

    def get_generation_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the status of an async generation task.

        Args:
            task_id: Task ID

        Returns:
            Status dictionary
        """
        from ..async_engine import get_task_status

        status = get_task_status(task_id)
        return status

    def cancel_generation(self, task_id: str) -> bool:
        """
        Cancel an async generation task.

        Args:
            task_id: Task ID

        Returns:
            True if cancelled successfully
        """
        from ..async_engine import cancel_task

        success = cancel_task(task_id)
        if success:
            logger.info(f"Template generation cancelled: {task_id}")
        return success