"""
Brand Kit Preview Generation Module.

Provides functionality to generate preview images and thumbnails for brand kits.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from PIL import Image, ImageDraw, ImageFont
import math

from .kit import BrandKit, ColorPalette, Color

logger = logging.getLogger(__name__)


class BrandKitPreviewGenerator:
    """Generator class for brand kit preview images."""

    def __init__(self, width: int = 800, height: int = 600):
        """
        Initialize the preview generator.

        Args:
            width: Default preview width
            height: Default preview height
        """
        self.default_width = width
        self.default_height = height
        self.font_cache: Dict[str, ImageFont.FreeTypeFont] = {}

    def generate_brandkit_preview(self, brandkit: BrandKit, output_path: Optional[str] = None,
                                width: Optional[int] = None, height: Optional[int] = None) -> Optional[Image.Image]:
        """
        Generate a preview image for a brand kit.

        Args:
            brandkit: BrandKit to generate preview for
            output_path: Optional path to save the preview
            width: Preview width (uses default if not specified)
            height: Preview height (uses default if not specified)

        Returns:
            Generated preview image or None if generation fails
        """
        try:
            width = width or self.default_width
            height = height or self.default_height

            # Create base image
            img = Image.new('RGB', (width, height), 'white')
            draw = ImageDraw.Draw(img)

            # Draw header with brand name
            self._draw_header(draw, brandkit.metadata.name, width, height)

            # Draw color palette section
            if brandkit.color_palettes:
                self._draw_color_palette(draw, brandkit.color_palettes[0], width, height)

            # Draw typography section
            if brandkit.fonts:
                self._draw_typography_preview(draw, brandkit, width, height)

            # Draw logo placeholder
            if brandkit.logo_paths:
                self._draw_logo_placeholder(draw, len(brandkit.logo_paths), width, height)

            # Draw brand metadata
            self._draw_metadata(draw, brandkit, width, height)

            # Save if path provided
            if output_path:
                img.save(output_path)
                logger.info(f"Brand kit preview saved to '{output_path}'")

            return img

        except Exception as e:
            logger.error(f"Failed to generate brand kit preview: {e}")
            return None

    def generate_variant_previews(self, brandkit: BrandKit, base_params: Dict[str, Any],
                                num_variants: int = 3) -> List[Dict[str, Any]]:
        """
        Generate preview data for brand kit variants.

        Args:
            brandkit: BrandKit to generate variants for
            base_params: Base generation parameters
            num_variants: Number of variants to generate

        Returns:
            List of variant preview data
        """
        variants = []

        try:
            from .applier import generate_brand_variants
            variant_params = generate_brand_variants(base_params, brandkit, num_variants)

            for i, params in enumerate(variant_params):
                variant_data = {
                    'variant_number': i + 1,
                    'parameters': params,
                    'preview_description': self._generate_variant_description(params, brandkit),
                    'expected_style': self._predict_variant_style(params, brandkit)
                }
                variants.append(variant_data)

            logger.info(f"Generated {num_variants} variant previews for '{brandkit.metadata.name}'")
            return variants

        except Exception as e:
            logger.error(f"Failed to generate variant previews: {e}")
            return []

    def _draw_header(self, draw: ImageDraw.ImageDraw, brand_name: str, width: int, height: int) -> None:
        """Draw the header section with brand name."""
        # Header background
        header_height = height // 8
        draw.rectangle([0, 0, width, header_height], fill='#f0f0f0')

        # Brand name
        try:
            font = self._get_font('Arial', 24)
            bbox = draw.textbbox((0, 0), brand_name, font=font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            y = (header_height - (bbox[3] - bbox[1])) // 2
            draw.text((x, y), brand_name, fill='black', font=font)
        except Exception:
            # Fallback if font loading fails
            draw.text((width//2 - 100, header_height//2 - 10), brand_name, fill='black')

    def _draw_color_palette(self, draw: ImageDraw.ImageDraw, palette: ColorPalette,
                          width: int, height: int) -> None:
        """Draw the color palette section."""
        palette_y = height // 8 + 20
        palette_height = height // 4

        # Palette title
        try:
            font = self._get_font('Arial', 16)
            draw.text((20, palette_y), f"Color Palette: {palette.name}", fill='black', font=font)
        except Exception:
            draw.text((20, palette_y), f"Color Palette: {palette.name}", fill='black')

        # Draw color swatches
        all_colors = (palette.primary_colors + palette.secondary_colors +
                     palette.accent_colors + palette.neutral_colors)

        if all_colors:
            swatch_width = width // len(all_colors)
            swatch_height = 40

            for i, color in enumerate(all_colors[:8]):  # Limit to 8 colors
                x = i * swatch_width
                y = palette_y + 30

                # Color swatch
                draw.rectangle([x, y, x + swatch_width - 5, y + swatch_height],
                             fill=color.hex_value)

                # Color name
                try:
                    font = self._get_font('Arial', 10)
                    draw.text((x + 5, y + swatch_height + 5), color.name, fill='black', font=font)
                except Exception:
                    draw.text((x + 5, y + swatch_height + 5), color.name[:10], fill='black')

    def _draw_typography_preview(self, draw: ImageDraw.ImageDraw, brandkit: BrandKit,
                               width: int, height: int) -> None:
        """Draw the typography preview section."""
        typo_y = height // 8 + height // 4 + 60

        # Typography title
        try:
            font = self._get_font('Arial', 16)
            draw.text((20, typo_y), "Typography", fill='black', font=font)
        except Exception:
            draw.text((20, typo_y), "Typography", fill='black')

        # Sample text with different fonts
        sample_texts = ["Heading", "Subheading", "Body text"]
        y_offset = typo_y + 30

        for i, sample in enumerate(sample_texts):
            font_spec = None
            if i == 0 and 'heading' in brandkit.fonts:
                font_spec = brandkit.fonts['heading']
            elif i == 1 and 'subheading' in brandkit.fonts:
                font_spec = brandkit.fonts['subheading']
            elif 'body' in brandkit.fonts:
                font_spec = brandkit.fonts['body']

            try:
                if font_spec:
                    font = self._get_font(font_spec.family, 14 + (2-i) * 4)
                    draw.text((20, y_offset), f"{sample}: {font_spec.family}", fill='black', font=font)
                else:
                    draw.text((20, y_offset), f"{sample}: Default font", fill='black')
            except Exception:
                draw.text((20, y_offset), f"{sample}: Font preview", fill='black')

            y_offset += 25

    def _draw_logo_placeholder(self, draw: ImageDraw.ImageDraw, logo_count: int,
                             width: int, height: int) -> None:
        """Draw logo placeholder section."""
        logo_y = height - 100

        # Logo section
        try:
            font = self._get_font('Arial', 14)
            draw.text((20, logo_y), f"Logos: {logo_count} available", fill='black', font=font)
        except Exception:
            draw.text((20, logo_y), f"Logos: {logo_count} available", fill='black')

    def _draw_metadata(self, draw: ImageDraw.ImageDraw, brandkit: BrandKit,
                      width: int, height: int) -> None:
        """Draw brand metadata section."""
        meta_y = height - 60

        metadata_text = f"v{brandkit.metadata.version} | {len(brandkit.color_palettes)} palettes | {len(brandkit.style_presets)} styles"

        try:
            font = self._get_font('Arial', 12)
            draw.text((20, meta_y), metadata_text, fill='#666666', font=font)
        except Exception:
            draw.text((20, meta_y), metadata_text, fill='#666666')

    def _get_font(self, family: str, size: int) -> ImageFont.FreeTypeFont:
        """Get a font for drawing, with caching."""
        cache_key = f"{family}_{size}"

        if cache_key in self.font_cache:
            return self.font_cache[cache_key]

        try:
            # Try to load the specified font
            font = ImageFont.truetype(family, size)
        except Exception:
            try:
                # Fallback to default font
                font = ImageFont.load_default()
            except Exception:
                # Ultimate fallback
                font = None

        if font:
            self.font_cache[cache_key] = font

        return font

    def _generate_variant_description(self, params: Dict[str, Any], brandkit: BrandKit) -> str:
        """Generate a description for a variant."""
        description_parts = []

        # Style information
        if 'positive_prompt' in params:
            prompt = params['positive_prompt']
            if any(style.name.lower() in prompt.lower() for style in brandkit.style_presets):
                description_parts.append("brand-styled")

        # Color information
        if brandkit.primary_palette and brandkit.primary_palette.primary_colors:
            primary_color = brandkit.primary_palette.primary_colors[0]
            description_parts.append(f"{primary_color.name.lower()}-accented")

        # Size information
        if 'width' in params and 'height' in params:
            description_parts.append(f"{params['width']}x{params['height']}")

        return " ".join(description_parts) if description_parts else "brand variant"

    def _predict_variant_style(self, params: Dict[str, Any], brandkit: BrandKit) -> str:
        """Predict the style characteristics of a variant."""
        styles = []

        # Analyze prompt for style indicators
        if 'positive_prompt' in params:
            prompt = params['positive_prompt'].lower()

            if any(word in prompt for word in ['bold', 'dramatic', 'intense']):
                styles.append("bold")
            if any(word in prompt for word in ['subtle', 'soft', 'gentle']):
                styles.append("subtle")
            if any(word in prompt for word in ['minimal', 'clean', 'simple']):
                styles.append("minimal")
            if any(word in prompt for word in ['vibrant', 'colorful', 'bright']):
                styles.append("vibrant")

        # Check LoRA influences
        if 'loras' in params:
            lora_names = [name.lower() for name in params['loras'].keys()]
            if any('artistic' in name for name in lora_names):
                styles.append("artistic")
            if any('professional' in name for name in lora_names):
                styles.append("professional")

        return ", ".join(styles) if styles else "balanced"


def generate_brandkit_preview(brandkit: BrandKit, output_path: Optional[str] = None,
                            width: Optional[int] = None, height: Optional[int] = None) -> Optional[Image.Image]:
    """
    Convenience function to generate brand kit preview.

    Args:
        brandkit: BrandKit to generate preview for
        output_path: Optional output path
        width: Preview width
        height: Preview height

    Returns:
        Generated preview image
    """
    generator = BrandKitPreviewGenerator()
    return generator.generate_brandkit_preview(brandkit, output_path, width, height)


def generate_variant_previews(brandkit: BrandKit, base_params: Dict[str, Any],
                            num_variants: int = 3) -> List[Dict[str, Any]]:
    """
    Convenience function to generate variant previews.

    Args:
        brandkit: BrandKit to generate variants for
        base_params: Base generation parameters
        num_variants: Number of variants

    Returns:
        List of variant preview data
    """
    generator = BrandKitPreviewGenerator()
    return generator.generate_variant_previews(brandkit, base_params, num_variants)</content>
<parameter name="filePath">c:\Users\Baxter\Documents\ComfyUI_env\ComfyUI\custom_nodes\Comfy Gimpy Node Pack\gimp_comfy_bridge\brandkit\preview.py