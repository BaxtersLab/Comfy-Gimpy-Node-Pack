"""
Brand Kit Application Module.

Provides functionality to apply brand kits to templates, styles, workflows,
and AI generations for consistent brand identity.
"""

import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

from .kit import BrandKit, StylePreset, WorkflowPreset
from ..shared.config import ConfigManager
from ..layout_opt import LayoutAnalyzer, LayoutOptimizer

logger = logging.getLogger(__name__)


class BrandKitApplier:
    """Main class for applying brand kits to various components."""

    def __init__(self, brandkit: BrandKit, config_manager: Optional[ConfigManager] = None):
        """
        Initialize the brand kit applier.

        Args:
            brandkit: BrandKit instance to apply
            config_manager: Optional config manager
        """
        self.brandkit = brandkit
        self.config_manager = config_manager

    def apply_to_template(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply brand kit to a template.

        Args:
            template_data: Template data dictionary

        Returns:
            Modified template data with brand kit applied
        """
        try:
            modified_template = template_data.copy()

            # Apply color palette
            if self.brandkit.primary_palette:
                palette = self.brandkit.primary_palette
                if 'colors' not in modified_template:
                    modified_template['colors'] = {}

                # Apply primary colors
                for color in palette.primary_colors[:3]:  # Limit to 3 primary colors
                    color_key = f"brand_{color.name.lower().replace(' ', '_')}"
                    modified_template['colors'][color_key] = color.hex_value

            # Apply fonts
            if self.brandkit.primary_font:
                font = self.brandkit.primary_font
                if 'typography' not in modified_template:
                    modified_template['typography'] = {}

                modified_template['typography']['primary_font'] = {
                    'family': font.family,
                    'weight': font.weight,
                    'size': font.size or 16,
                    'fallbacks': font.fallback_fonts
                }

            # Apply style presets
            if self.brandkit.style_presets:
                if 'style_presets' not in modified_template:
                    modified_template['style_presets'] = []

                for preset in self.brandkit.style_presets[:2]:  # Limit to 2 presets
                    modified_template['style_presets'].append({
                        'name': preset.name,
                        'loras': preset.loras.copy(),
                        'description': preset.description
                    })

            # Add brand metadata
            modified_template['brand_applied'] = {
                'kit_name': self.brandkit.metadata.name,
                'kit_version': self.brandkit.metadata.version,
                'applied_at': 'template'
            }

            logger.info(f"Applied brand kit '{self.brandkit.metadata.name}' to template")
            return modified_template

        except Exception as e:
            logger.error(f"Failed to apply brand kit to template: {e}")
            return template_data

    async def optimize_layout_with_brand(self, layout_data: Dict[str, Any],
                                       optimization_level: str = "standard") -> Dict[str, Any]:
        """
        Optimize layout with brand kit awareness.

        Args:
            layout_data: Layout data to optimize
            optimization_level: Level of optimization ("basic", "standard", "advanced")

        Returns:
            Optimized layout data with brand considerations
        """
        try:
            # Initialize layout optimization components
            analyzer = LayoutAnalyzer()
            optimizer = LayoutOptimizer()

            # Analyze current layout
            analysis = await analyzer.analyze_layout(layout_data)

            # Get brand-specific optimization rules
            brand_rules = self._get_brand_optimization_rules()

            # Generate brand-aware optimization actions
            actions = await optimizer.optimize_layout_with_rules(
                analysis,
                brand_rules,
                level=optimization_level
            )

            # Apply optimizations
            optimized_layout = await optimizer.apply_actions(layout_data, actions)

            logger.info(f"Applied brand-aware layout optimization with {len(actions)} actions")
            return optimized_layout

        except Exception as e:
            logger.warning(f"Brand-aware layout optimization failed: {e}")
            return layout_data

    def _get_brand_optimization_rules(self) -> Dict[str, Any]:
        """
        Get brand-specific optimization rules from the brand kit.

        Returns:
            Dictionary of brand optimization rules
        """
        rules = {}

        # Color harmony rules based on brand palette
        if self.brandkit.primary_palette:
            palette = self.brandkit.primary_palette
            rules['color_harmony'] = {
                'primary_colors': palette.primary_colors,
                'secondary_colors': palette.secondary_colors,
                'accent_colors': palette.accent_colors,
                'neutral_colors': palette.neutral_colors
            }

        # Typography rules based on brand fonts
        if self.brandkit.typography:
            typography = self.brandkit.typography
            rules['typography'] = {
                'heading_font': typography.heading_font,
                'body_font': typography.body_font,
                'font_scale': typography.font_scale,
                'line_height_ratio': typography.line_height_ratio
            }

        # Spacing rules based on brand guidelines
        if self.brandkit.spacing:
            spacing = self.brandkit.spacing
            rules['spacing'] = {
                'base_unit': spacing.base_unit,
                'scale_factor': spacing.scale_factor,
                'preferred_ratios': spacing.preferred_ratios
            }

        # Layout preferences
        if self.brandkit.layout_preferences:
            rules['layout'] = self.brandkit.layout_preferences

        return rules

    def apply_to_style(self, style_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply brand kit to a style definition.

        Args:
            style_data: Style data dictionary

        Returns:
            Modified style data with brand kit applied
        """
        try:
            modified_style = style_data.copy()

            # Apply style presets
            if self.brandkit.style_presets:
                primary_preset = self.brandkit.style_presets[0]

                # Merge LoRAs
                if 'loras' not in modified_style:
                    modified_style['loras'] = {}

                for lora_name, weight in primary_preset.loras.items():
                    if lora_name not in modified_style['loras']:
                        modified_style['loras'][lora_name] = weight
                    else:
                        # Blend existing weight with brand weight
                        existing = modified_style['loras'][lora_name]
                        modified_style['loras'][lora_name] = (existing + weight) / 2

            # Apply color influences
            if self.brandkit.primary_palette:
                palette = self.brandkit.primary_palette
                if 'color_influences' not in modified_style:
                    modified_style['color_influences'] = []

                for color in palette.primary_colors[:2]:
                    modified_style['color_influences'].append({
                        'color': color.hex_value,
                        'influence': 0.3  # 30% influence
                    })

            # Add brand metadata
            modified_style['brand_applied'] = {
                'kit_name': self.brandkit.metadata.name,
                'kit_version': self.brandkit.metadata.version,
                'applied_at': 'style'
            }

            logger.info(f"Applied brand kit '{self.brandkit.metadata.name}' to style")
            return modified_style

        except Exception as e:
            logger.error(f"Failed to apply brand kit to style: {e}")
            return style_data

    def apply_to_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply brand kit to a workflow definition.

        Args:
            workflow_data: Workflow data dictionary

        Returns:
            Modified workflow data with brand kit applied
        """
        try:
            modified_workflow = workflow_data.copy()

            # Apply workflow presets
            if self.brandkit.workflow_presets:
                primary_preset = self.brandkit.workflow_presets[0]

                # Apply preset parameters
                if 'parameters' not in modified_workflow:
                    modified_workflow['parameters'] = {}

                for param_key, param_value in primary_preset.parameters.items():
                    if param_key not in modified_workflow['parameters']:
                        modified_workflow['parameters'][param_key] = param_value

            # Apply layout preferences
            if 'layout' not in modified_workflow:
                modified_workflow['layout'] = {}

            layout_prefs = self.brandkit.layout_preferences
            modified_workflow['layout']['preferred_aspect_ratios'] = layout_prefs.aspect_ratios
            modified_workflow['layout']['preferred_sizes'] = layout_prefs.preferred_sizes

            # Add brand metadata
            modified_workflow['brand_applied'] = {
                'kit_name': self.brandkit.metadata.name,
                'kit_version': self.brandkit.metadata.version,
                'applied_at': 'workflow'
            }

            logger.info(f"Applied brand kit '{self.brandkit.metadata.name}' to workflow")
            return modified_workflow

        except Exception as e:
            logger.error(f"Failed to apply brand kit to workflow: {e}")
            return workflow_data

    def apply_to_generation(self, generation_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply brand kit to AI generation parameters.

        Args:
            generation_params: Generation parameters dictionary

        Returns:
            Modified generation parameters with brand kit applied
        """
        try:
            modified_params = generation_params.copy()

            # Apply style presets to positive prompt
            if self.brandkit.style_presets and 'positive_prompt' in modified_params:
                primary_preset = self.brandkit.style_presets[0]
                style_tags = [tag for tag in primary_preset.tags if len(tag) > 2]
                if style_tags:
                    current_prompt = modified_params['positive_prompt']
                    style_addition = ", " + ", ".join(style_tags[:3])  # Limit to 3 tags
                    modified_params['positive_prompt'] = current_prompt + style_addition

            # Apply color influences to negative prompt (avoid certain colors)
            if self.brandkit.primary_palette and 'negative_prompt' in modified_params:
                palette = self.brandkit.primary_palette
                # Add color constraints based on brand palette
                color_descriptors = []
                for color in palette.primary_colors[:2]:
                    # Simple color name extraction (this could be more sophisticated)
                    if 'blue' in color.name.lower():
                        color_descriptors.append('purple')  # Avoid competing colors
                    elif 'green' in color.name.lower():
                        color_descriptors.append('purple')

                if color_descriptors:
                    current_negative = modified_params['negative_prompt']
                    color_avoidance = ", " + ", ".join(color_descriptors)
                    modified_params['negative_prompt'] = current_negative + color_avoidance

            # Apply layout preferences
            layout_prefs = self.brandkit.layout_preferences
            if layout_prefs.preferred_sizes:
                preferred_size = layout_prefs.preferred_sizes[0]
                width, height = map(int, preferred_size.split('x'))
                modified_params['width'] = width
                modified_params['height'] = height

            # Add brand metadata
            modified_params['brand_applied'] = {
                'kit_name': self.brandkit.metadata.name,
                'kit_version': self.brandkit.metadata.version,
                'applied_at': 'generation'
            }

            logger.info(f"Applied brand kit '{self.brandkit.metadata.name}' to generation")
            return modified_params

        except Exception as e:
            logger.error(f"Failed to apply brand kit to generation: {e}")
            return generation_params


# Convenience functions

def apply_brandkit_to_template(brandkit: BrandKit, template_data: Dict[str, Any],
                              config_manager: Optional[ConfigManager] = None) -> Dict[str, Any]:
    """
    Convenience function to apply brand kit to template.

    Args:
        brandkit: BrandKit instance
        template_data: Template data
        config_manager: Optional config manager

    Returns:
        Modified template data
    """
    applier = BrandKitApplier(brandkit, config_manager)
    return applier.apply_to_template(template_data)


def apply_brandkit_to_style(brandkit: BrandKit, style_data: Dict[str, Any],
                           config_manager: Optional[ConfigManager] = None) -> Dict[str, Any]:
    """
    Convenience function to apply brand kit to style.

    Args:
        brandkit: BrandKit instance
        style_data: Style data
        config_manager: Optional config manager

    Returns:
        Modified style data
    """
    applier = BrandKitApplier(brandkit, config_manager)
    return applier.apply_to_style(style_data)


def apply_brandkit_to_workflow(brandkit: BrandKit, workflow_data: Dict[str, Any],
                              config_manager: Optional[ConfigManager] = None) -> Dict[str, Any]:
    """
    Convenience function to apply brand kit to workflow.

    Args:
        brandkit: BrandKit instance
        workflow_data: Workflow data
        config_manager: Optional config manager

    Returns:
        Modified workflow data
    """
    applier = BrandKitApplier(brandkit, config_manager)
    return applier.apply_to_workflow(workflow_data)


def apply_brandkit_to_generation(brandkit: BrandKit, generation_params: Dict[str, Any],
                                config_manager: Optional[ConfigManager] = None) -> Dict[str, Any]:
    """
    Convenience function to apply brand kit to AI generation.

    Args:
        brandkit: BrandKit instance
        generation_params: Generation parameters
        config_manager: Optional config manager

    Returns:
        Modified generation parameters
    """
    applier = BrandKitApplier(brandkit, config_manager)
    return applier.apply_to_generation(generation_params)


def generate_brand_variants(base_params: Dict[str, Any], brandkit: BrandKit,
                           num_variants: int = 3) -> List[Dict[str, Any]]:
    """
    Generate brand-consistent variants of parameters.

    Args:
        base_params: Base parameters to vary
        brandkit: BrandKit for consistency
        num_variants: Number of variants to generate

    Returns:
        List of variant parameter sets
    """
    variants = []

    try:
        # Apply base brand kit
        applier = BrandKitApplier(brandkit)
        base_branded = applier.apply_to_generation(base_params)

        for i in range(num_variants):
            variant = base_branded.copy()

            # Apply slight variations based on brand style presets
            if brandkit.style_presets and len(brandkit.style_presets) > 1:
                # Use different style preset for each variant
                preset_index = i % len(brandkit.style_presets)
                preset = brandkit.style_presets[preset_index]

                if 'positive_prompt' in variant:
                    current_prompt = variant['positive_prompt']
                    # Add style-specific tags
                    style_tags = [tag for tag in preset.tags if len(tag) > 2][:2]
                    if style_tags:
                        style_addition = f", {preset.name.lower()}"
                        variant['positive_prompt'] = current_prompt + style_addition

            # Vary parameters slightly for diversity
            if 'guidance_scale' in variant:
                base_guidance = variant['guidance_scale']
                variant['guidance_scale'] = base_guidance + (i - 1) * 0.5  # -0.5, 0, +0.5

            if 'num_inference_steps' in variant:
                base_steps = variant['num_inference_steps']
                variant['num_inference_steps'] = max(10, base_steps + (i - 1) * 5)  # -5, 0, +5 steps

            variants.append(variant)

        logger.info(f"Generated {num_variants} brand variants for '{brandkit.metadata.name}'")
        return variants

    except Exception as e:
        logger.error(f"Failed to generate brand variants: {e}")
        return [base_params] * num_variants</content>
<parameter name="filePath">c:\Users\Baxter\Documents\ComfyUI_env\ComfyUI\custom_nodes\Comfy Gimpy Node Pack\gimp_comfy_bridge\brandkit\applier.py