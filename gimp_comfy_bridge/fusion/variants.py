"""
Variant generation with controlled randomness.
"""

import logging
from typing import Dict, Any, List, Optional, Union
import random
import hashlib
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class VariantParameters:
    """Parameters for variant generation."""
    prompt_variation_strength: float = 0.3
    style_noise_strength: float = 0.2
    composition_variation: float = 0.1
    color_temperature_shift: float = 0.05
    lighting_variation: float = 0.15


class VariantGenerator:
    """Generates variants with controlled randomness."""

    def __init__(self):
        self.random = random.Random()
        self.variant_cache = {}

    def generate_variants(self,
                         template: Dict[str, Any],
                         style: Dict[str, Any],
                         brand_kit: Optional[Any] = None,
                         count: int = 1,
                         seed: Optional[int] = None,
                         blended_loras: Optional[Dict[str, Any]] = None,
                         parameters: Optional[VariantParameters] = None) -> List[Dict[str, Any]]:
        """
        Generate multiple variants with controlled randomness.

        Args:
            template: Base template
            style: Base style
            brand_kit: Optional brand kit
            count: Number of variants to generate
            seed: Random seed for reproducibility
            blended_loras: Optional blended LoRA configuration
            parameters: Variant generation parameters

        Returns:
            List of variant configurations
        """
        if parameters is None:
            parameters = VariantParameters()

        # Set random seed for reproducibility
        if seed is not None:
            self.random.seed(seed)
        else:
            # Use template/style hash as seed for consistency
            seed_string = f"{template.get('id', '')}_{style.get('id', '')}_{datetime.now().isoformat()}"
            self.random.seed(hashlib.md5(seed_string.encode()).hexdigest())

        variants = []

        for i in range(count):
            variant = self._generate_single_variant(
                template=template,
                style=style,
                brand_kit=brand_kit,
                variant_index=i,
                parameters=parameters,
                blended_loras=blended_loras
            )
            variants.append(variant)

        logger.info(f"Generated {len(variants)} variants")
        return variants

    def _generate_single_variant(self,
                                template: Dict[str, Any],
                                style: Dict[str, Any],
                                brand_kit: Optional[Any],
                                variant_index: int,
                                parameters: VariantParameters,
                                blended_loras: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a single variant."""

        # Start with base template and style
        variant = {
            "id": f"variant_{variant_index + 1}",
            "template_id": template.get("id"),
            "style_id": style.get("id"),
            "brand_kit_id": brand_kit.id if brand_kit else None,
            "parameters": {},
            "generated_at": datetime.now().isoformat(),
            "variant_index": variant_index
        }

        # Apply template layout
        variant["layout"] = template.get("layout", {})

        # Generate varied prompt
        base_prompt = style.get("positive_prompt", "")
        negative_prompt = style.get("negative_prompt", "")

        variant["positive_prompt"] = self._vary_prompt(
            base_prompt, parameters.prompt_variation_strength
        )
        variant["negative_prompt"] = self._vary_prompt(
            negative_prompt, parameters.prompt_variation_strength
        )

        # Apply brand kit if available
        if brand_kit:
            variant["positive_prompt"] = self._apply_brand_to_prompt(
                variant["positive_prompt"], brand_kit
            )

        # Add LoRA configuration
        if blended_loras:
            variant["loras"] = blended_loras
        elif "loras" in style:
            variant["loras"] = style["loras"]

        # Add style parameters with variation
        variant["style_parameters"] = self._vary_style_parameters(
            style.get("parameters", {}), parameters
        )

        # Add composition variation
        variant["composition"] = self._vary_composition(
            template.get("composition", {}), parameters.composition_variation
        )

        # Add workflow configuration
        variant["workflow"] = self._generate_workflow_config(
            template, style, variant
        )

        return variant

    def _vary_prompt(self, base_prompt: str, variation_strength: float) -> str:
        """Add controlled variation to a prompt."""
        if not base_prompt or variation_strength <= 0:
            return base_prompt

        # Split prompt into components
        components = [comp.strip() for comp in base_prompt.split(',') if comp.strip()]

        if len(components) < 2:
            return base_prompt

        # Randomly modify component order with some probability
        if self.random.random() < variation_strength:
            # Shuffle some components
            shuffle_count = max(1, int(len(components) * variation_strength))
            shuffle_indices = self.random.sample(range(len(components)), shuffle_count)

            for i in shuffle_indices:
                if i > 0:  # Don't shuffle the first component
                    j = self.random.randint(0, len(components) - 1)
                    components[i], components[j] = components[j], components[i]

        # Add variation words with some probability
        variation_words = [
            "vibrant", "subtle", "dramatic", "minimal", "detailed",
            "soft", "sharp", "warm", "cool", "dynamic"
        ]

        if self.random.random() < variation_strength * 0.5:
            variation_word = self.random.choice(variation_words)
            # Insert variation word at random position
            insert_pos = self.random.randint(0, len(components))
            components.insert(insert_pos, variation_word)

        return ", ".join(components)

    def _apply_brand_to_prompt(self, prompt: str, brand_kit: Any) -> str:
        """Apply brand kit elements to prompt."""
        if not brand_kit or not prompt:
            return prompt

        enhanced_prompt = prompt

        # Add color information
        if hasattr(brand_kit, 'colors') and brand_kit.colors:
            color_names = list(brand_kit.colors.keys())[:3]  # Limit to 3 colors
            if color_names:
                enhanced_prompt += f", featuring {', '.join(color_names)} brand colors"

        # Add style hints from guidelines
        if hasattr(brand_kit, 'guidelines') and brand_kit.guidelines:
            style_hint = brand_kit.guidelines.get('style_hint')
            if style_hint:
                enhanced_prompt += f", {style_hint}"

        return enhanced_prompt

    def _vary_style_parameters(self,
                              base_params: Dict[str, Any],
                              parameters: VariantParameters) -> Dict[str, Any]:
        """Add variation to style parameters."""
        varied_params = base_params.copy()

        # Add noise to numeric parameters
        for key, value in varied_params.items():
            if isinstance(value, (int, float)):
                noise = (self.random.random() - 0.5) * 2 * parameters.style_noise_strength
                varied_params[key] = value * (1 + noise)

        # Add specific variations
        varied_params["color_temperature_shift"] = (
            varied_params.get("color_temperature_shift", 0) +
            (self.random.random() - 0.5) * parameters.color_temperature_shift * 2000
        )

        varied_params["lighting_variation"] = (
            self.random.random() * parameters.lighting_variation
        )

        return varied_params

    def _vary_composition(self,
                         base_composition: Dict[str, Any],
                         variation_strength: float) -> Dict[str, Any]:
        """Add variation to composition parameters."""
        varied_composition = base_composition.copy()

        # Vary positioning
        for key in ["x_offset", "y_offset", "scale", "rotation"]:
            if key in varied_composition:
                base_value = varied_composition[key]
                if isinstance(base_value, (int, float)):
                    variation = (self.random.random() - 0.5) * 2 * variation_strength
                    if key == "scale":
                        varied_composition[key] = base_value * (1 + variation * 0.5)
                    elif key == "rotation":
                        varied_composition[key] = base_value + variation * 45  # Max 45 degree variation
                    else:
                        varied_composition[key] = base_value + variation * 100  # Pixel variation

        return varied_composition

    def _generate_workflow_config(self,
                                 template: Dict[str, Any],
                                 style: Dict[str, Any],
                                 variant: Dict[str, Any]) -> Dict[str, Any]:
        """Generate workflow configuration for the variant."""
        workflow = {
            "template_id": template.get("id"),
            "style_id": style.get("id"),
            "variant_id": variant["id"],
            "nodes": []
        }

        # Add template-specific nodes
        if "workflow_nodes" in template:
            workflow["nodes"].extend(template["workflow_nodes"])

        # Add style-specific nodes
        if "workflow_nodes" in style:
            workflow["nodes"].extend(style["workflow_nodes"])

        # Add variant-specific overrides
        workflow["overrides"] = {
            "positive_prompt": variant.get("positive_prompt"),
            "negative_prompt": variant.get("negative_prompt"),
            "loras": variant.get("loras", {}),
            "style_parameters": variant.get("style_parameters", {})
        }

        return workflow

    def get_variant_stats(self, variants: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics about generated variants."""
        if not variants:
            return {}

        stats = {
            "total_variants": len(variants),
            "unique_prompts": len(set(v.get("positive_prompt", "") for v in variants)),
            "template_distribution": {},
            "style_distribution": {}
        }

        for variant in variants:
            template_id = variant.get("template_id", "unknown")
            style_id = variant.get("style_id", "unknown")

            stats["template_distribution"][template_id] = (
                stats["template_distribution"].get(template_id, 0) + 1
            )
            stats["style_distribution"][style_id] = (
                stats["style_distribution"].get(style_id, 0) + 1
            )

        return stats