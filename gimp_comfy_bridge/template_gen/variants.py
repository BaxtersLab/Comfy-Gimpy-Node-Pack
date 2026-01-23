"""
Variants Generator for Comfy Gimpy Studio (Phase 12)

Generates layout, color, style, and typography variations of templates
with controlled randomness and brand kit integration.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
from copy import deepcopy
import random
import json

logger = logging.getLogger(__name__)


@dataclass
class VariationOptions:
    """Options for generating variations."""

    color_variations: bool = True
    typography_variations: bool = True
    layout_variations: bool = True
    style_variations: bool = True
    brand_kit_preserve: bool = True
    randomness_factor: float = 0.3  # 0.0 to 1.0
    max_layout_shift: int = 50  # pixels
    color_hue_shift: int = 30  # degrees


class VariantGenerator:
    """Generates template variations."""

    def __init__(self):
        """Initialize the variant generator."""
        self.random_seed = 42
        random.seed(self.random_seed)

        # Color palettes for variations
        self._load_color_palettes()

        # Typography variations
        self._load_typography_variations()

        logger.info("Variant generator initialized")

    def _load_color_palettes(self):
        """Load predefined color palettes."""
        self.color_palettes = {
            "warm": ["#ff6b35", "#f7931e", "#ffd23f", "#f7f3e9"],
            "cool": ["#0066cc", "#00aaff", "#66ccff", "#e6f3ff"],
            "earth": ["#8b4513", "#daa520", "#228b22", "#f5f5dc"],
            "modern": ["#2c3e50", "#3498db", "#ecf0f1", "#95a5a6"],
            "vibrant": ["#ff0080", "#00ff00", "#ffff00", "#ff6600"],
            "muted": ["#666666", "#999999", "#cccccc", "#f0f0f0"],
            "pastel": ["#ffb3ba", "#bae1ff", "#baffc9", "#ffffba"],
            "dark": ["#1a1a1a", "#333333", "#666666", "#cccccc"]
        }

    def _load_typography_variations(self):
        """Load typography variation options."""
        self.font_variations = {
            "sans_serif": ["Arial", "Helvetica", "Verdana", "Tahoma"],
            "serif": ["Times New Roman", "Georgia", "Garamond", "Bookman"],
            "monospace": ["Courier New", "Consolas", "Monaco", "Menlo"],
            "display": ["Impact", "Arial Black", "Copperplate", "Engravers"]
        }

        self.size_variations = {
            "small": [10, 12, 14],
            "medium": [16, 18, 20, 24],
            "large": [28, 32, 36, 48],
            "xlarge": [56, 64, 72, 84]
        }

    def generate_variants(self, template_path: Path,
                         count: int = 3,
                         color_variations: bool = True,
                         typography_variations: bool = True,
                         layout_variations: bool = True) -> List[Dict[str, Any]]:
        """
        Generate variants of a template.

        Args:
            template_path: Path to base template
            count: Number of variants to generate
            color_variations: Whether to generate color variations
            typography_variations: Whether to generate typography variations
            layout_variations: Whether to generate layout variations

        Returns:
            List of variant data dictionaries
        """
        try:
            logger.info(f"Generating {count} variants for template: {template_path.name}")

            # Load base template data
            base_data = self._load_template_data(template_path)
            if not base_data:
                logger.error(f"Could not load template data from {template_path}")
                return []

            variants = []

            for i in range(count):
                variant_data = self._generate_single_variant(
                    base_data, i + 1,
                    color_variations, typography_variations, layout_variations
                )

                if variant_data:
                    # Save variant
                    variant_path = self._save_variant(template_path, variant_data, i + 1)
                    if variant_path:
                        variant_data["path"] = str(variant_path)
                        variants.append(variant_data)

            logger.info(f"Generated {len(variants)} variants")
            return variants

        except Exception as e:
            logger.error(f"Variant generation failed: {e}")
            return []

    def _load_template_data(self, template_path: Path) -> Optional[Dict[str, Any]]:
        """
        Load template data from path.

        Args:
            template_path: Template directory path

        Returns:
            Template data dictionary or None
        """
        try:
            # Load layout data
            layout_file = template_path / "layout.xcf"
            if not layout_file.exists():
                # Try JSON version for development
                layout_file = template_path / "layout.json"

            if layout_file.exists():
                with open(layout_file, 'r') as f:
                    if layout_file.suffix == '.json':
                        layout_data = json.load(f)
                    else:
                        # Would parse XCF file here
                        layout_data = {"elements": [], "dimensions": [1920, 1080]}

                # Load metadata
                metadata_file = template_path / "metadata.json"
                metadata = {}
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)

                return {
                    "layout": layout_data,
                    "metadata": metadata,
                    "path": template_path
                }

        except Exception as e:
            logger.error(f"Failed to load template data: {e}")

        return None

    def _generate_single_variant(self, base_data: Dict[str, Any],
                               variant_num: int,
                               color_variations: bool,
                               typography_variations: bool,
                               layout_variations: bool) -> Optional[Dict[str, Any]]:
        """
        Generate a single variant.

        Args:
            base_data: Base template data
            variant_num: Variant number
            color_variations: Enable color variations
            typography_variations: Enable typography variations
            layout_variations: Enable layout variations

        Returns:
            Variant data dictionary or None
        """
        try:
            # Deep copy base data
            variant_data = deepcopy(base_data)
            variant_data["variant_number"] = variant_num
            variant_data["variations_applied"] = []

            layout_data = variant_data["layout"]

            # Apply variations
            if color_variations:
                self._apply_color_variation(layout_data)
                variant_data["variations_applied"].append("color")

            if typography_variations:
                self._apply_typography_variation(layout_data)
                variant_data["variations_applied"].append("typography")

            if layout_variations:
                self._apply_layout_variation(layout_data)
                variant_data["variations_applied"].append("layout")

            # Update metadata
            self._update_variant_metadata(variant_data)

            return variant_data

        except Exception as e:
            logger.error(f"Single variant generation failed: {e}")
            return None

    def _apply_color_variation(self, layout_data: Dict[str, Any]):
        """
        Apply color variations to layout.

        Args:
            layout_data: Layout data to modify
        """
        # Choose random color palette
        palette_name = random.choice(list(self.color_palettes.keys()))
        palette = self.color_palettes[palette_name]

        # Apply colors to elements
        for element in layout_data.get("elements", []):
            if element.get("type") == "text":
                element["properties"]["color"] = random.choice(palette)
            elif element.get("type") == "shape":
                element["properties"]["fill_color"] = random.choice(palette)
                element["properties"]["stroke_color"] = random.choice(palette)

        # Store palette info
        layout_data["color_palette"] = {
            "name": palette_name,
            "colors": palette
        }

    def _apply_typography_variation(self, layout_data: Dict[str, Any]):
        """
        Apply typography variations to layout.

        Args:
            layout_data: Layout data to modify
        """
        # Choose random font family
        font_family = random.choice(list(self.font_variations.keys()))
        fonts = self.font_variations[font_family]

        # Apply to text elements
        for element in layout_data.get("elements", []):
            if element.get("type") == "text":
                # Random font from family
                element["properties"]["font_family"] = random.choice(fonts)

                # Random size variation
                current_size = element["properties"].get("font_size", 16)
                size_variation = random.choice([-2, -1, 0, 1, 2]) * 2
                element["properties"]["font_size"] = max(8, current_size + size_variation)

                # Random weight
                element["properties"]["font_weight"] = random.choice(["normal", "bold"])

    def _apply_layout_variation(self, layout_data: Dict[str, Any]):
        """
        Apply layout variations to elements.

        Args:
            layout_data: Layout data to modify
        """
        dimensions = layout_data.get("dimensions", [1920, 1080])
        width, height = dimensions

        for element in layout_data.get("elements", []):
            # Small random position shifts
            x_shift = random.randint(-30, 30)
            y_shift = random.randint(-30, 30)

            element["x"] = max(0, min(width - element.get("width", 100),
                                    element["x"] + x_shift))
            element["y"] = max(0, min(height - element.get("height", 50),
                                    element["y"] + y_shift))

            # Small size variations
            if random.random() < 0.3:  # 30% chance
                w_factor = random.uniform(0.9, 1.1)
                h_factor = random.uniform(0.9, 1.1)

                element["width"] = max(50, int(element["width"] * w_factor))
                element["height"] = max(20, int(element["height"] * h_factor))

    def _update_variant_metadata(self, variant_data: Dict[str, Any]):
        """
        Update metadata for variant.

        Args:
            variant_data: Variant data to update
        """
        metadata = variant_data.get("metadata", {})
        variant_num = variant_data.get("variant_number", 1)

        # Update name
        base_name = metadata.get("name", "Template")
        metadata["name"] = f"{base_name} - Variant {variant_num}"

        # Update description
        variations = variant_data.get("variations_applied", [])
        if variations:
            metadata["description"] = f"Variant with {', '.join(variations)} modifications"

        # Add variant-specific tags
        tags = metadata.get("tags", [])
        tags.append("variant")
        for variation in variations:
            tags.append(f"variant-{variation}")
        metadata["tags"] = list(set(tags))  # Remove duplicates

        # Update version
        metadata["version"] = f"1.{variant_num}"

    def _save_variant(self, template_path: Path,
                     variant_data: Dict[str, Any],
                     variant_num: int) -> Optional[Path]:
        """
        Save variant to disk.

        Args:
            template_path: Base template path
            variant_data: Variant data
            variant_num: Variant number

        Returns:
            Path to saved variant or None
        """
        try:
            # Create variant directory
            variant_dir = template_path.parent / f"{template_path.name}_variant_{variant_num}"
            variant_dir.mkdir(parents=True, exist_ok=True)

            # Save layout data
            layout_file = variant_dir / "layout.json"
            with open(layout_file, 'w') as f:
                json.dump(variant_data["layout"], f, indent=2)

            # Save metadata
            metadata_file = variant_dir / "metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(variant_data["metadata"], f, indent=2)

            # Copy workflow if it exists
            workflow_src = template_path / "workflow.json"
            if workflow_src.exists():
                import shutil
                shutil.copy2(workflow_src, variant_dir / "workflow.json")

            # Copy preview if it exists
            preview_src = template_path / "preview.png"
            if preview_src.exists():
                import shutil
                shutil.copy2(preview_src, variant_dir / "preview.png")

            logger.debug(f"Saved variant to: {variant_dir}")
            return variant_dir

        except Exception as e:
            logger.error(f"Failed to save variant: {e}")
            return None

    def generate_color_variations(self, base_colors: List[str], count: int = 5) -> List[List[str]]:
        """
        Generate color variations from base colors.

        Args:
            base_colors: Base color palette
            count: Number of variations to generate

        Returns:
            List of color palettes
        """
        variations = []

        for _ in range(count):
            variation = []
            for base_color in base_colors:
                # Apply hue shift
                hue_shift = random.randint(-30, 30)
                # Simple color manipulation (would use proper color library)
                variation.append(base_color)  # Placeholder

            variations.append(variation)

        return variations

    def generate_layout_variations(self, base_layout: Dict[str, Any], count: int = 3) -> List[Dict[str, Any]]:
        """
        Generate layout variations.

        Args:
            base_layout: Base layout data
            count: Number of variations

        Returns:
            List of layout variations
        """
        variations = []

        for _ in range(count):
            variation = deepcopy(base_layout)
            self._apply_layout_variation(variation)
            variations.append(variation)

        return variations

    def generate_typography_variations(self, base_elements: List[Dict[str, Any]], count: int = 3) -> List[List[Dict[str, Any]]]:
        """
        Generate typography variations.

        Args:
            base_elements: Base text elements
            count: Number of variations

        Returns:
            List of element variations
        """
        variations = []

        for _ in range(count):
            variation = deepcopy(base_elements)
            for element in variation:
                if element.get("type") == "text":
                    # Apply typography variation
                    self._apply_single_typography_variation(element)
            variations.append(variation)

        return variations

    def _apply_single_typography_variation(self, element: Dict[str, Any]):
        """
        Apply typography variation to a single element.

        Args:
            element: Text element to modify
        """
        properties = element.get("properties", {})

        # Random font size adjustment
        current_size = properties.get("font_size", 16)
        size_change = random.choice([-4, -2, 0, 2, 4])
        properties["font_size"] = max(8, current_size + size_change)

        # Random font weight
        properties["font_weight"] = random.choice(["normal", "bold", "light"])

        # Random alignment
        properties["alignment"] = random.choice(["left", "center", "right"])

    def blend_with_brand_kit(self, layout_data: Dict[str, Any],
                           brand_kit: Dict[str, Any]) -> Dict[str, Any]:
        """
        Blend layout with brand kit elements.

        Args:
            layout_data: Layout data to modify
            brand_kit: Brand kit data

        Returns:
            Modified layout data
        """
        # Apply brand colors
        if "colors" in brand_kit:
            brand_colors = brand_kit["colors"]
            # Replace some colors with brand colors
            for element in layout_data.get("elements", []):
                if random.random() < 0.5:  # 50% chance
                    if element.get("type") in ["text", "shape"]:
                        element["properties"]["color"] = random.choice(brand_colors)

        # Apply brand fonts
        if "fonts" in brand_kit:
            brand_fonts = brand_kit["fonts"]
            for element in layout_data.get("elements", []):
                if element.get("type") == "text" and random.random() < 0.7:  # 70% chance
                    element["properties"]["font_family"] = random.choice(brand_fonts)

        return layout_data