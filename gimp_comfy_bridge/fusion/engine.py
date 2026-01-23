"""
Main fusion engine for style-template fusion.
"""

import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from .blender import LoRABlender, StyleMixer
from .brandkits import BrandKitManager
from .variants import VariantGenerator
from .preview import PreviewGenerator

# Import brand kit components
from ..brandkit import BrandKitApplier, load_brandkit

# Import template generation components
from ..template_gen.generator import TemplateGenerator
from ..template_gen.layout_builder import LayoutBuilder
from ..template_gen.metadata_builder import MetadataBuilder
from ..template_gen.preview_builder import PreviewBuilder
from ..template_gen.variants import VariantGenerator as TemplateVariantGenerator
from ..template_gen.save import TemplateSaver

logger = logging.getLogger(__name__)


@dataclass
class FusionOptions:
    """Options for fusion operations."""
    lora_weights: Optional[Dict[str, float]] = None
    style_mix_ratios: Optional[Dict[str, float]] = None
    brand_kit_id: Optional[str] = None
    variant_count: int = 1
    randomness_seed: Optional[int] = None
    generate_previews: bool = True
    output_format: str = "png"
    quality: int = 95
    # Remote execution options
    prefer_remote: bool = False
    force_remote: bool = False
    remote_node_id: Optional[str] = None
    remote_fallback: bool = True  # Fall back to local if remote fails


@dataclass
class FusionResult:
    """Result of a fusion operation."""
    task_id: str
    variants: List[Dict[str, Any]]
    preview_urls: Optional[List[str]] = None
    brand_kit_applied: Optional[str] = None
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class FusionEngine:
    """Main engine for style-template fusion operations."""

    def __init__(self):
        self.lora_blender = LoRABlender()
        self.style_mixer = StyleMixer()
        self.brand_kit_manager = BrandKitManager()
        self.brand_kit_applier = BrandKitApplier()
        self.variant_generator = VariantGenerator()
        self.preview_generator = PreviewGenerator()

        # Template generation components
        self.template_generator = TemplateGenerator()
        self.layout_builder = LayoutBuilder()
        self.metadata_builder = MetadataBuilder()
        self.template_preview_builder = PreviewBuilder()
        self.template_variant_generator = TemplateVariantGenerator()
        self.template_saver = TemplateSaver()

    def fuse(self,
             template: Dict[str, Any],
             style: Dict[str, Any],
             options: FusionOptions) -> FusionResult:
        """
        Fuse a template with a style and generate variants.

        Args:
            template: Template definition
            style: Style definition
            options: Fusion options

        Returns:
            FusionResult with generated variants
        """
        logger.info(f"Starting fusion with template '{template.get('id', 'unknown')}' "
                   f"and style '{style.get('id', 'unknown')}'")

        # Check if remote execution is requested
        if options.force_remote or options.prefer_remote:
            remote_result = self._try_remote_fusion(template, style, options)
            if remote_result:
                return remote_result
            elif options.force_remote:
                # Create error result for forced remote that failed
                return FusionResult(
                    task_id=f"fusion_failed_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    variants=[],
                    preview_urls=None,
                    brand_kit_applied=None
                )
            # Fall back to local execution if prefer_remote and fallback enabled

        # Apply brand kit if specified
        brand_kit = None
        if options.brand_kit_id:
            try:
                brand_kit = load_brandkit(options.brand_kit_id)
                logger.info(f"Loaded brand kit '{options.brand_kit_id}'")
            except Exception as e:
                logger.warning(f"Failed to load brand kit '{options.brand_kit_id}': {e}")

        # Blend LoRAs if specified
        blended_loras = None
        if options.lora_weights:
            blended_loras = self.lora_blender.blend_loras(options.lora_weights)
            logger.info(f"Blended {len(options.lora_weights)} LoRAs")

        # Mix styles if specified
        mixed_style = style
        if options.style_mix_ratios:
            mixed_style = self.style_mixer.mix_styles(
                [style] + list(options.style_mix_ratios.keys()),
                list(options.style_mix_ratios.values())
            )
            logger.info(f"Mixed {len(options.style_mix_ratios)} styles")

        # Generate variants
        variants = self.variant_generator.generate_variants(
            template=template,
            style=mixed_style,
            brand_kit=brand_kit,
            count=options.variant_count,
            seed=options.randomness_seed,
            blended_loras=blended_loras
        )

        logger.info(f"Generated {len(variants)} variants")

        # Generate previews if requested
        preview_urls = None
        if options.generate_previews:
            preview_urls = []
            for i, variant in enumerate(variants):
                preview_url = self.preview_generator.generate_preview(
                    variant,
                    f"variant_{i+1}",
                    options.output_format,
                    options.quality
                )
                if preview_url:
                    preview_urls.append(preview_url)

            logger.info(f"Generated {len(preview_urls)} preview thumbnails")

        # Create result
        result = FusionResult(
            task_id=f"fusion_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            variants=variants,
            preview_urls=preview_urls,
            brand_kit_applied=options.brand_kit_id
        )

        logger.info(f"Fusion completed successfully: {result.task_id}")
        return result

    def _try_remote_fusion(self,
                          template: Dict[str, Any],
                          style: Dict[str, Any],
                          options: FusionOptions) -> Optional[FusionResult]:
        """
        Attempt to perform fusion remotely.

        Args:
            template: Template definition
            style: Style definition
            options: Fusion options

        Returns:
            FusionResult if successful, None if remote execution not available
        """
        try:
            # Import remote execution components
            from ..async_engine.api import submit_remote_task, is_remote_available, get_task_status
            import time

            if not is_remote_available():
                logger.debug("Remote execution not available for fusion")
                return None

            # Prepare fusion parameters
            fusion_params = {
                'template': template,
                'style': style,
                'options': {
                    'lora_weights': options.lora_weights,
                    'style_mix_ratios': options.style_mix_ratios,
                    'brand_kit_id': options.brand_kit_id,
                    'variant_count': options.variant_count,
                    'randomness_seed': options.randomness_seed,
                    'generate_previews': options.generate_previews,
                    'output_format': options.output_format,
                    'quality': options.quality,
                }
            }

            # Submit remote fusion task
            task_id = submit_remote_task(
                operation='fuse_template_style',
                parameters=fusion_params,
                node_id=options.remote_node_id,
                timeout_seconds=300,  # 5 minutes for fusion
                metadata={'fusion_type': 'remote', 'template_id': template.get('id'), 'style_id': style.get('id')}
            )

            # Wait for completion (with timeout)
            start_wait = time.time()
            timeout = 300  # 5 minutes
            while time.time() - start_wait < timeout:
                status = get_task_status(task_id)
                if status and status['state'] in ['completed', 'failed']:
                    break
                time.sleep(1)  # Check every second

            # Get final result
            final_status = get_task_status(task_id)

            if final_status and final_status['state'] == 'completed' and final_status['result']:
                result_data = final_status['result']
                variants = result_data.get('variants', [])
                if variants:
                    return FusionResult(
                        task_id=task_id,
                        variants=variants,
                        preview_urls=result_data.get('preview_urls'),
                        brand_kit_applied=result_data.get('brand_kit_applied')
                    )
            elif final_status and final_status['state'] == 'failed':
                logger.warning(f"Remote fusion failed: {final_status.get('result', {}).get('error', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Remote fusion attempt failed: {e}")

        return None

    async def generate_template_from_prompt(self,
                                          prompt: str,
                                          category: str = "general",
                                          style_references: Optional[List[str]] = None,
                                          brand_kit_id: Optional[str] = None,
                                          generate_variants: bool = True,
                                          variant_count: int = 3) -> Dict[str, Any]:
        """
        Generate a new template from a text prompt using AI assistance.

        Args:
            prompt: Text description of the desired template
            category: Template category (poster, brochure, website, etc.)
            style_references: Optional list of style IDs to reference
            brand_kit_id: Optional brand kit to apply
            generate_variants: Whether to generate template variants
            variant_count: Number of variants to generate

        Returns:
            Generated template definition with metadata and variants
        """
        logger.info(f"Generating template from prompt: '{prompt[:50]}...'")

        try:
            # Generate template using AI
            template_data = await self.template_generator.generate_from_prompt(
                prompt=prompt,
                category=category,
                style_references=style_references,
                brand_kit_id=brand_kit_id
            )

            # Build layout
            layout = await self.layout_builder.build_layout(
                template_data=template_data,
                category=category
            )

            # Generate metadata
            metadata = await self.metadata_builder.build_metadata(
                template_data=template_data,
                prompt=prompt,
                category=category
            )

            # Generate previews
            previews = await self.template_preview_builder.build_previews(
                layout=layout,
                template_data=template_data,
                metadata=metadata
            )

            # Generate variants if requested
            variants = []
            if generate_variants:
                variants = await self.template_variant_generator.generate_variants(
                    base_template={
                        "layout": layout,
                        "metadata": metadata,
                        "previews": previews
                    },
                    count=variant_count
                )

            # Combine into complete template
            template = {
                "id": metadata.get("id", f"template_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
                "name": metadata.get("name", "Generated Template"),
                "description": metadata.get("description", ""),
                "category": category,
                "layout": layout,
                "metadata": metadata,
                "previews": previews,
                "variants": variants,
                "generated_from": "prompt",
                "prompt": prompt,
                "created_at": datetime.now().isoformat(),
                "version": "1.0"
            }

            logger.info(f"Template generated successfully: {template['id']}")
            return template

        except Exception as e:
            logger.error(f"Template generation failed: {e}")
            raise

    async def generate_template_from_image(self,
                                         image_path: Union[str, Path],
                                         category: str = "general",
                                         analysis_prompt: Optional[str] = None,
                                         generate_variants: bool = True,
                                         variant_count: int = 3) -> Dict[str, Any]:
        """
        Generate a template by analyzing an existing image.

        Args:
            image_path: Path to the reference image
            category: Template category
            analysis_prompt: Optional prompt to guide the analysis
            generate_variants: Whether to generate variants
            variant_count: Number of variants to generate

        Returns:
            Generated template based on image analysis
        """
        logger.info(f"Generating template from image: {image_path}")

        try:
            # Generate template from image analysis
            template_data = await self.template_generator.generate_from_image(
                image_path=str(image_path),
                category=category,
                analysis_prompt=analysis_prompt
            )

            # Build layout based on image structure
            layout = await self.layout_builder.build_layout_from_image(
                image_path=str(image_path),
                template_data=template_data,
                category=category
            )

            # Generate metadata
            metadata = await self.metadata_builder.build_metadata_from_image(
                image_path=str(image_path),
                template_data=template_data,
                category=category,
                analysis_prompt=analysis_prompt
            )

            # Generate previews
            previews = await self.template_preview_builder.build_previews(
                layout=layout,
                template_data=template_data,
                metadata=metadata
            )

            # Generate variants
            variants = []
            if generate_variants:
                variants = await self.template_variant_generator.generate_variants(
                    base_template={
                        "layout": layout,
                        "metadata": metadata,
                        "previews": previews
                    },
                    count=variant_count
                )

            # Combine into complete template
            template = {
                "id": metadata.get("id", f"template_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
                "name": metadata.get("name", "Template from Image"),
                "description": metadata.get("description", ""),
                "category": category,
                "layout": layout,
                "metadata": metadata,
                "previews": previews,
                "variants": variants,
                "generated_from": "image",
                "source_image": str(image_path),
                "created_at": datetime.now().isoformat(),
                "version": "1.0"
            }

            logger.info(f"Template generated from image successfully: {template['id']}")
            return template

        except Exception as e:
            logger.error(f"Template generation from image failed: {e}")
            raise

    async def generate_template_from_workflow(self,
                                            workflow_data: Dict[str, Any],
                                            category: str = "general",
                                            generate_variants: bool = True,
                                            variant_count: int = 3) -> Dict[str, Any]:
        """
        Generate a template based on a ComfyUI workflow structure.

        Args:
            workflow_data: ComfyUI workflow definition
            category: Template category
            generate_variants: Whether to generate variants
            variant_count: Number of variants to generate

        Returns:
            Generated template based on workflow analysis
        """
        logger.info("Generating template from workflow")

        try:
            # Generate template from workflow analysis
            template_data = await self.template_generator.generate_from_workflow(
                workflow_data=workflow_data,
                category=category
            )

            # Build layout based on workflow outputs
            layout = await self.layout_builder.build_layout_from_workflow(
                workflow_data=workflow_data,
                template_data=template_data,
                category=category
            )

            # Generate metadata
            metadata = await self.metadata_builder.build_metadata_from_workflow(
                workflow_data=workflow_data,
                template_data=template_data,
                category=category
            )

            # Generate previews
            previews = await self.template_preview_builder.build_previews(
                layout=layout,
                template_data=template_data,
                metadata=metadata
            )

            # Generate variants
            variants = []
            if generate_variants:
                variants = await self.template_variant_generator.generate_variants(
                    base_template={
                        "layout": layout,
                        "metadata": metadata,
                        "previews": previews
                    },
                    count=variant_count
                )

            # Combine into complete template
            template = {
                "id": metadata.get("id", f"template_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
                "name": metadata.get("name", "Template from Workflow"),
                "description": metadata.get("description", ""),
                "category": category,
                "layout": layout,
                "metadata": metadata,
                "previews": previews,
                "variants": variants,
                "generated_from": "workflow",
                "source_workflow": workflow_data.get("id", "unknown"),
                "created_at": datetime.now().isoformat(),
                "version": "1.0"
            }

            logger.info(f"Template generated from workflow successfully: {template['id']}")
            return template

        except Exception as e:
            logger.error(f"Template generation from workflow failed: {e}")
            raise

    async def enhance_template_with_ai(self,
                                     template: Dict[str, Any],
                                     enhancement_prompt: str,
                                     generate_variants: bool = True,
                                     variant_count: int = 3) -> Dict[str, Any]:
        """
        Enhance an existing template using AI assistance.

        Args:
            template: Existing template to enhance
            enhancement_prompt: Description of desired enhancements
            generate_variants: Whether to generate enhanced variants
            variant_count: Number of enhanced variants to generate

        Returns:
            Enhanced template with AI improvements
        """
        logger.info(f"Enhancing template '{template.get('id', 'unknown')}' with AI")

        try:
            # Enhance template using AI
            enhanced_data = await self.template_generator.enhance_template(
                template=template,
                enhancement_prompt=enhancement_prompt
            )

            # Update layout with enhancements
            enhanced_layout = await self.layout_builder.enhance_layout(
                layout=template.get("layout", {}),
                enhancements=enhanced_data.get("layout_enhancements", {})
            )

            # Update metadata
            enhanced_metadata = await self.metadata_builder.enhance_metadata(
                metadata=template.get("metadata", {}),
                enhancements=enhanced_data.get("metadata_enhancements", {}),
                enhancement_prompt=enhancement_prompt
            )

            # Generate new previews
            enhanced_previews = await self.template_preview_builder.build_previews(
                layout=enhanced_layout,
                template_data=enhanced_data,
                metadata=enhanced_metadata
            )

            # Generate enhanced variants
            variants = []
            if generate_variants:
                variants = await self.template_variant_generator.generate_variants(
                    base_template={
                        "layout": enhanced_layout,
                        "metadata": enhanced_metadata,
                        "previews": enhanced_previews
                    },
                    count=variant_count,
                    enhancement_mode=True
                )

            # Combine into enhanced template
            enhanced_template = template.copy()
            enhanced_template.update({
                "layout": enhanced_layout,
                "metadata": enhanced_metadata,
                "previews": enhanced_previews,
                "variants": variants,
                "enhanced": True,
                "enhancement_prompt": enhancement_prompt,
                "enhanced_at": datetime.now().isoformat(),
                "version": "1.1"  # Increment version for enhanced templates
            })

            logger.info(f"Template enhanced successfully: {enhanced_template['id']}")
            return enhanced_template

        except Exception as e:
            logger.error(f"Template enhancement failed: {e}")
            raise

    async def save_generated_template(self,
                                    template: Dict[str, Any],
                                    output_dir: Optional[Union[str, Path]] = None,
                                    include_variants: bool = True) -> str:
        """
        Save a generated template to disk.

        Args:
            template: Template to save
            output_dir: Optional output directory
            include_variants: Whether to save variants

        Returns:
            Path to saved template directory
        """
        logger.info(f"Saving generated template: {template.get('id', 'unknown')}")

        try:
            saved_path = await self.template_saver.save_template(
                template=template,
                output_dir=str(output_dir) if output_dir else None,
                include_variants=include_variants
            )

            logger.info(f"Template saved successfully: {saved_path}")
            return saved_path

        except Exception as e:
            logger.error(f"Template saving failed: {e}")
            raise

    def get_supported_template_categories(self) -> List[str]:
        """Get supported template categories for generation."""
        return [
            "poster", "brochure", "website", "business_card", "flyer",
            "banner", "social_media", "presentation", "newsletter",
            "menu", "certificate", "invitation", "logo", "packaging",
            "infographic", "resume", "letterhead", "envelope", "general"
        ]

    def get_template_generation_capabilities(self) -> Dict[str, Any]:
        """Get information about template generation capabilities."""
        return {
            "supported_categories": self.get_supported_template_categories(),
            "generation_methods": [
                "from_prompt",
                "from_image",
                "from_workflow",
                "enhancement"
            ],
            "max_variants": 10,
            "supported_image_formats": ["png", "jpg", "jpeg", "webp"],
            "ai_enhanced": True,
            "layout_building": True,
            "metadata_generation": True,
            "preview_generation": True,
            "variant_generation": True
        }

    def get_supported_formats(self) -> List[str]:
        """Get supported output formats."""
        return ["png", "jpg", "webp", "tiff"]

    def validate_template(self, template: Dict[str, Any]) -> bool:
        """Validate template structure."""
        required_keys = ["id", "name", "layout"]
        return all(key in template for key in required_keys)

    def validate_style(self, style: Dict[str, Any]) -> bool:
        """Validate style structure."""
        required_keys = ["id", "name"]
        return all(key in style for key in required_keys)


# Global fusion engine instance
_fusion_engine: Optional[FusionEngine] = None


def initialize_fusion_engine() -> FusionEngine:
    """Initialize the global fusion engine."""
    global _fusion_engine
    if _fusion_engine is None:
        _fusion_engine = FusionEngine()
        logger.info("Fusion engine initialized")
    return _fusion_engine


def fuse(template: Dict[str, Any],
         style: Dict[str, Any],
         options: Optional[FusionOptions] = None) -> FusionResult:
    """
    Convenience function to fuse template and style.

    Args:
        template: Template definition
        style: Style definition
        options: Fusion options (optional)

    Returns:
        FusionResult with generated variants
    """
    if options is None:
        options = FusionOptions()

    engine = initialize_fusion_engine()
    return engine.fuse(template, style, options)