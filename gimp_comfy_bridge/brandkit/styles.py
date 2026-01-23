"""
Style Management Module.

Provides style preset blending, inheritance, and brand-specific LoRA management.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from copy import deepcopy

from .kit import StylePreset

logger = logging.getLogger(__name__)


class StyleManager:
    """Manager class for style operations."""

    def __init__(self):
        """Initialize the style manager."""
        self.style_cache: Dict[str, StylePreset] = {}

    def blend_style_presets(self, presets: List[StylePreset], weights: Optional[List[float]] = None) -> StylePreset:
        """
        Blend multiple style presets together.

        Args:
            presets: List of StylePreset objects to blend
            weights: Optional weights for each preset (defaults to equal weighting)

        Returns:
            Blended StylePreset
        """
        if not presets:
            raise ValueError("At least one preset required for blending")

        if len(presets) == 1:
            return deepcopy(presets[0])

        # Set default weights if not provided
        if weights is None:
            weights = [1.0 / len(presets)] * len(presets)
        elif len(weights) != len(presets):
            raise ValueError("Weights list must match presets list length")

        # Normalize weights
        total_weight = sum(weights)
        if total_weight == 0:
            raise ValueError("Total weight cannot be zero")
        weights = [w / total_weight for w in weights]

        # Blend LoRAs
        blended_loras: Dict[str, float] = {}
        all_lora_names = set()

        for preset in presets:
            all_lora_names.update(preset.loras.keys())

        for lora_name in all_lora_names:
            blended_weight = 0.0
            total_contributing_weight = 0.0

            for preset, weight in zip(presets, weights):
                if lora_name in preset.loras:
                    blended_weight += preset.loras[lora_name] * weight
                    total_contributing_weight += weight

            if total_contributing_weight > 0:
                # Normalize by contributing weight
                blended_weight /= total_contributing_weight
                blended_loras[lora_name] = round(blended_weight, 3)

        # Combine descriptions
        descriptions = [p.description for p in presets if p.description]
        blended_description = " + ".join(descriptions) if descriptions else "Blended style"

        # Combine tags
        all_tags = set()
        for preset in presets:
            all_tags.update(preset.tags)

        # Create blended preset name
        names = [p.name for p in presets]
        blended_name = " + ".join(names) if len(names) <= 3 else f"Blend of {len(names)} styles"

        return StylePreset(
            name=blended_name,
            loras=blended_loras,
            description=blended_description,
            tags=list(all_tags)
        )

    def create_brand_style_variant(self, base_preset: StylePreset, brand_name: str,
                                 variation_type: str = "subtle") -> StylePreset:
        """
        Create a brand-specific variant of a style preset.

        Args:
            base_preset: Base StylePreset to vary
            brand_name: Brand name for the variant
            variation_type: Type of variation ('subtle', 'bold', 'minimal')

        Returns:
            Brand-specific StylePreset variant
        """
        variant = deepcopy(base_preset)

        # Modify LoRA weights based on variation type
        if variation_type == "subtle":
            # Reduce all weights slightly
            for lora_name in variant.loras:
                variant.loras[lora_name] *= 0.8
        elif variation_type == "bold":
            # Increase all weights
            for lora_name in variant.loras:
                variant.loras[lora_name] = min(2.0, variant.loras[lora_name] * 1.2)
        elif variation_type == "minimal":
            # Keep only the strongest LoRA, reduce others
            if variant.loras:
                strongest_lora = max(variant.loras.items(), key=lambda x: x[1])
                for lora_name in variant.loras:
                    if lora_name != strongest_lora[0]:
                        variant.loras[lora_name] *= 0.3

        # Update name and description
        variant.name = f"{brand_name} {variant.name}"
        variant.description = f"Brand variant: {variant.description}"

        # Add brand tag
        if "brand" not in variant.tags:
            variant.tags.append("brand")

        return variant

    def optimize_style_for_brand(self, preset: StylePreset, brand_context: Dict[str, Any]) -> StylePreset:
        """
        Optimize a style preset for a specific brand context.

        Args:
            preset: StylePreset to optimize
            brand_context: Brand context information

        Returns:
            Optimized StylePreset
        """
        optimized = deepcopy(preset)

        # Adjust based on brand personality (if available)
        brand_personality = brand_context.get('personality', '').lower()

        if 'professional' in brand_personality:
            # Reduce dramatic LoRAs
            for lora_name, weight in optimized.loras.items():
                if any(word in lora_name.lower() for word in ['dramatic', 'intense', 'bold']):
                    optimized.loras[lora_name] = min(weight, 0.8)

        elif 'creative' in brand_personality or 'artistic' in brand_personality:
            # Boost artistic LoRAs
            for lora_name, weight in optimized.loras.items():
                if any(word in lora_name.lower() for word in ['artistic', 'creative', 'stylized']):
                    optimized.loras[lora_name] = min(1.5, weight * 1.2)

        elif 'minimal' in brand_personality or 'clean' in brand_personality:
            # Reduce complex LoRAs
            for lora_name, weight in optimized.loras.items():
                if weight > 1.0:
                    optimized.loras[lora_name] = min(weight, 1.0)

        # Adjust for brand colors (if available)
        brand_colors = brand_context.get('primary_colors', [])
        if brand_colors:
            # This could adjust LoRAs based on color themes
            # For now, just add a note
            optimized.description += f" (optimized for {len(brand_colors)} brand colors)"

        return optimized

    def validate_style_preset(self, preset: StylePreset) -> List[str]:
        """
        Validate a style preset.

        Args:
            preset: StylePreset to validate

        Returns:
            List of validation errors
        """
        errors = []

        if not preset.name or not preset.name.strip():
            errors.append("Style preset name is required")

        if len(preset.name) > 50:
            errors.append("Style preset name too long (max 50 characters)")

        if not preset.loras:
            errors.append("Style preset must contain at least one LoRA")

        for lora_name, weight in preset.loras.items():
            if not isinstance(weight, (int, float)):
                errors.append(f"LoRA weight for '{lora_name}' must be numeric")
            elif not (-2.0 <= weight <= 2.0):
                errors.append(f"LoRA weight {weight} for '{lora_name}' out of range (-2.0 to 2.0)")

        if len(preset.description) > 200:
            errors.append("Style preset description too long (max 200 characters)")

        if len(preset.tags) > 10:
            errors.append("Too many tags (max 10)")

        return errors

    def get_style_recommendations(self, brand_context: Dict[str, Any],
                                available_styles: List[StylePreset]) -> List[Tuple[StylePreset, float]]:
        """
        Get style recommendations based on brand context.

        Args:
            brand_context: Brand context information
            available_styles: List of available StylePreset objects

        Returns:
            List of (StylePreset, confidence_score) tuples
        """
        recommendations = []

        brand_personality = brand_context.get('personality', '').lower()
        brand_colors = brand_context.get('primary_colors', [])

        for style in available_styles:
            score = 0.0

            # Personality matching
            style_tags = [tag.lower() for tag in style.tags]
            if brand_personality:
                if any(personality_word in ' '.join(style_tags) for personality_word in brand_personality.split()):
                    score += 0.4

            # Color theme matching (simplified)
            if brand_colors:
                # Check if style name suggests color compatibility
                style_name_lower = style.name.lower()
                color_keywords = ['colorful', 'vibrant', 'muted', 'monochrome', 'pastel']
                if any(keyword in style_name_lower for keyword in color_keywords):
                    score += 0.2

            # Default minimum score for all styles
            score = max(score, 0.1)

            recommendations.append((style, score))

        # Sort by score descending
        recommendations.sort(key=lambda x: x[1], reverse=True)

        return recommendations[:5]  # Return top 5 recommendations

    def create_style_from_loras(self, lora_dict: Dict[str, float], name: str = "Custom Style",
                              description: str = "", tags: Optional[List[str]] = None) -> StylePreset:
        """
        Create a StylePreset from a LoRA dictionary.

        Args:
            lora_dict: Dictionary of LoRA names to weights
            name: Name for the style preset
            description: Description for the style preset
            tags: Optional tags for the style preset

        Returns:
            Created StylePreset
        """
        # Validate LoRA weights
        validated_loras = {}
        for lora_name, weight in lora_dict.items():
            if isinstance(weight, (int, float)) and -2.0 <= weight <= 2.0:
                validated_loras[lora_name] = float(weight)
            else:
                logger.warning(f"Invalid LoRA weight {weight} for '{lora_name}', skipping")

        if not validated_loras:
            raise ValueError("No valid LoRAs provided")

        return StylePreset(
            name=name,
            loras=validated_loras,
            description=description or f"Custom style with {len(validated_loras)} LoRAs",
            tags=tags or []
        )

    def merge_style_with_overrides(self, base_style: StylePreset,
                                 overrides: Dict[str, Any]) -> StylePreset:
        """
        Merge a base style with override parameters.

        Args:
            base_style: Base StylePreset
            overrides: Dictionary of override parameters

        Returns:
            Merged StylePreset
        """
        merged = deepcopy(base_style)

        # Override LoRA weights
        if 'loras' in overrides:
            for lora_name, weight in overrides['loras'].items():
                merged.loras[lora_name] = weight

        # Override other properties
        if 'name' in overrides:
            merged.name = overrides['name']
        if 'description' in overrides:
            merged.description = overrides['description']
        if 'tags' in overrides:
            merged.tags = overrides['tags']

        return merged

    def cache_style(self, preset: StylePreset) -> None:
        """
        Cache a style preset for faster access.

        Args:
            preset: StylePreset to cache
        """
        self.style_cache[preset.name] = deepcopy(preset)

    def get_cached_style(self, name: str) -> Optional[StylePreset]:
        """
        Get a cached style preset.

        Args:
            name: Name of the cached style

        Returns:
            Cached StylePreset or None
        """
        return deepcopy(self.style_cache.get(name))

    def clear_cache(self) -> None:
        """Clear the style cache."""
        self.style_cache.clear()


# Convenience functions

def blend_style_presets(presets: List[StylePreset], weights: Optional[List[float]] = None) -> StylePreset:
    """
    Convenience function to blend style presets.

    Args:
        presets: List of StylePreset objects
        weights: Optional weights for blending

    Returns:
        Blended StylePreset
    """
    manager = StyleManager()
    return manager.blend_style_presets(presets, weights)


def create_brand_style_variant(base_preset: StylePreset, brand_name: str,
                             variation_type: str = "subtle") -> StylePreset:
    """
    Convenience function to create brand style variant.

    Args:
        base_preset: Base StylePreset
        brand_name: Brand name
        variation_type: Variation type

    Returns:
        Brand-specific StylePreset variant
    """
    manager = StyleManager()
    return manager.create_brand_style_variant(base_preset, brand_name, variation_type)</content>
<parameter name="filePath">c:\Users\Baxter\Documents\ComfyUI_env\ComfyUI\custom_nodes\Comfy Gimpy Node Pack\gimp_comfy_bridge\brandkit\styles.py