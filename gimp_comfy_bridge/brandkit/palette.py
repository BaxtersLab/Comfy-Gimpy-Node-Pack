"""
Color Palette Management Module.

Provides tools for color palette creation, harmonization, and image-based
color extraction for brand kit development.
"""

import colorsys
import logging
import math
from typing import List, Tuple, Optional, Dict, Any
from PIL import Image
import numpy as np

from .kit import Color, ColorPalette

logger = logging.getLogger(__name__)


class ColorPaletteManager:
    """Manager class for color palette operations."""

    def __init__(self):
        """Initialize the color palette manager."""
        pass

    def create_complementary_palette(self, base_color: Color) -> ColorPalette:
        """
        Create a complementary color palette from a base color.

        Args:
            base_color: Base color to build palette around

        Returns:
            Complementary ColorPalette
        """
        try:
            # Convert hex to HSL
            r, g, b = self._hex_to_rgb(base_color.hex_value)
            h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)

            # Create complementary colors
            comp_h = (h + 0.5) % 1.0  # 180 degrees opposite

            # Generate palette
            primary_colors = [
                Color(f"{base_color.name} Primary", base_color.hex_value, (r, g, b)),
                Color(f"{base_color.name} Light", self._hsl_to_hex(h, min(1.0, l + 0.2), s)),
                Color(f"{base_color.name} Dark", self._hsl_to_hex(h, max(0.0, l - 0.2), s)),
            ]

            secondary_colors = [
                Color(f"{base_color.name} Complement", self._hsl_to_hex(comp_h, l, s)),
                Color(f"{base_color.name} Complement Light", self._hsl_to_hex(comp_h, min(1.0, l + 0.2), s)),
            ]

            neutral_colors = [
                Color("Light Gray", "#E0E0E0", (224, 224, 224)),
                Color("Medium Gray", "#A0A0A0", (160, 160, 160)),
                Color("Dark Gray", "#404040", (64, 64, 64)),
            ]

            return ColorPalette(
                name=f"{base_color.name} Complementary",
                primary_colors=primary_colors,
                secondary_colors=secondary_colors,
                neutral_colors=neutral_colors
            )

        except Exception as e:
            logger.error(f"Failed to create complementary palette: {e}")
            return self._create_fallback_palette(base_color.name)

    def create_triadic_palette(self, base_color: Color) -> ColorPalette:
        """
        Create a triadic color palette from a base color.

        Args:
            base_color: Base color to build palette around

        Returns:
            Triadic ColorPalette
        """
        try:
            # Convert hex to HSL
            r, g, b = self._hex_to_rgb(base_color.hex_value)
            h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)

            # Create triadic colors (120 degrees apart)
            triad1_h = (h + 1/3) % 1.0
            triad2_h = (h + 2/3) % 1.0

            # Generate palette
            primary_colors = [
                Color(f"{base_color.name} Primary", base_color.hex_value, (r, g, b)),
            ]

            secondary_colors = [
                Color(f"{base_color.name} Triad 1", self._hsl_to_hex(triad1_h, l, s)),
                Color(f"{base_color.name} Triad 2", self._hsl_to_hex(triad2_h, l, s)),
                Color(f"{base_color.name} Triad 1 Light", self._hsl_to_hex(triad1_h, min(1.0, l + 0.15), s)),
                Color(f"{base_color.name} Triad 2 Light", self._hsl_to_hex(triad2_h, min(1.0, l + 0.15), s)),
            ]

            return ColorPalette(
                name=f"{base_color.name} Triadic",
                primary_colors=primary_colors,
                secondary_colors=secondary_colors
            )

        except Exception as e:
            logger.error(f"Failed to create triadic palette: {e}")
            return self._create_fallback_palette(base_color.name)

    def create_analogous_palette(self, base_color: Color) -> ColorPalette:
        """
        Create an analogous color palette from a base color.

        Args:
            base_color: Base color to build palette around

        Returns:
            Analogous ColorPalette
        """
        try:
            # Convert hex to HSL
            r, g, b = self._hex_to_rgb(base_color.hex_value)
            h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)

            # Create analogous colors (±30 degrees)
            analog1_h = (h + 1/12) % 1.0  # +30 degrees
            analog2_h = (h - 1/12) % 1.0  # -30 degrees

            # Generate palette
            primary_colors = [
                Color(f"{base_color.name} Primary", base_color.hex_value, (r, g, b)),
            ]

            secondary_colors = [
                Color(f"{base_color.name} Analog 1", self._hsl_to_hex(analog1_h, l, s)),
                Color(f"{base_color.name} Analog 2", self._hsl_to_hex(analog2_h, l, s)),
            ]

            accent_colors = [
                Color(f"{base_color.name} Warm", self._hsl_to_hex(h, l, min(1.0, s + 0.2))),
                Color(f"{base_color.name} Cool", self._hsl_to_hex(h, l, max(0.0, s - 0.2))),
            ]

            return ColorPalette(
                name=f"{base_color.name} Analogous",
                primary_colors=primary_colors,
                secondary_colors=secondary_colors,
                accent_colors=accent_colors
            )

        except Exception as e:
            logger.error(f"Failed to create analogous palette: {e}")
            return self._create_fallback_palette(base_color.name)

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _rgb_to_hex(self, r: int, g: int, b: int) -> str:
        """Convert RGB tuple to hex color."""
        return f"#{r:02x}{g:02x}{b:02x}"

    def _hsl_to_hex(self, h: float, l: float, s: float) -> str:
        """Convert HSL to hex color."""
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return self._rgb_to_hex(int(r * 255), int(g * 255), int(b * 255))

    def _create_fallback_palette(self, base_name: str) -> ColorPalette:
        """Create a fallback palette when generation fails."""
        return ColorPalette(
            name=f"{base_name} Fallback",
            primary_colors=[
                Color("Fallback Blue", "#0066CC", (0, 102, 204)),
                Color("Fallback Green", "#00CC66", (0, 204, 102)),
            ],
            secondary_colors=[
                Color("Fallback Gray", "#666666", (102, 102, 102)),
            ]
        )


def harmonize_palette(palette: ColorPalette) -> ColorPalette:
    """
    Harmonize a color palette for better visual consistency.

    Args:
        palette: ColorPalette to harmonize

    Returns:
        Harmonized ColorPalette
    """
    try:
        harmonized = ColorPalette(
            name=f"{palette.name} (Harmonized)",
            primary_colors=palette.primary_colors.copy(),
            secondary_colors=palette.secondary_colors.copy(),
            accent_colors=palette.accent_colors.copy(),
            neutral_colors=palette.neutral_colors.copy()
        )

        # Ensure minimum contrast ratios
        _ensure_contrast_ratios(harmonized)

        # Balance color distribution
        _balance_color_distribution(harmonized)

        logger.info(f"Harmonized palette '{palette.name}'")
        return harmonized

    except Exception as e:
        logger.error(f"Failed to harmonize palette: {e}")
        return palette


def _ensure_contrast_ratios(palette: ColorPalette) -> None:
    """Ensure adequate contrast ratios between colors."""
    # This is a simplified implementation
    # In a real implementation, you'd calculate proper contrast ratios
    # according to WCAG guidelines

    all_colors = (palette.primary_colors + palette.secondary_colors +
                  palette.accent_colors + palette.neutral_colors)

    if len(all_colors) < 2:
        return

    # Simple check: ensure no two colors are too similar
    for i, color1 in enumerate(all_colors):
        for color2 in all_colors[i+1:]:
            if _colors_too_similar(color1, color2):
                # Adjust color2 to increase contrast
                _adjust_color_for_contrast(color2, color1)


def _colors_too_similar(color1: Color, color2: Color, threshold: float = 50.0) -> bool:
    """Check if two colors are too similar."""
    if not (color1.rgb and color2.rgb):
        return False

    # Calculate Euclidean distance in RGB space
    distance = math.sqrt(
        (color1.rgb[0] - color2.rgb[0]) ** 2 +
        (color1.rgb[1] - color2.rgb[1]) ** 2 +
        (color1.rgb[2] - color2.rgb[2]) ** 2
    )

    return distance < threshold


def _adjust_color_for_contrast(color: Color, reference: Color) -> None:
    """Adjust a color to increase contrast with reference color."""
    if not (color.rgb and reference.rgb):
        return

    # Simple adjustment: shift hue
    r, g, b = color.rgb
    h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)

    # Shift hue by 30 degrees
    new_h = (h + 1/12) % 1.0

    new_r, new_g, new_b = colorsys.hls_to_rgb(new_h, l, s)
    new_hex = f"#{int(new_r*255):02x}{int(new_g*255):02x}{int(new_b*255):02x}"

    color.hex_value = new_hex
    color.rgb = (int(new_r*255), int(new_g*255), int(new_b*255))


def _balance_color_distribution(palette: ColorPalette) -> None:
    """Balance the distribution of colors in the palette."""
    # Ensure we have a good mix of warm and cool colors
    # This is a simplified implementation
    pass


def extract_palette_from_image(image_path: str, num_colors: int = 6,
                              palette_name: str = "Extracted") -> Optional[ColorPalette]:
    """
    Extract a color palette from an image.

    Args:
        image_path: Path to the image file
        num_colors: Number of colors to extract
        palette_name: Name for the extracted palette

    Returns:
        Extracted ColorPalette or None if extraction fails
    """
    try:
        # Open and process image
        image = Image.open(image_path)
        image = image.convert('RGB')

        # Resize for faster processing
        image.thumbnail((200, 200))

        # Convert to numpy array
        pixels = np.array(image)
        pixels = pixels.reshape(-1, 3)

        # Use k-means clustering to find dominant colors
        from sklearn.cluster import KMeans
        kmeans = KMeans(n_clusters=num_colors, random_state=42, n_init=10)
        kmeans.fit(pixels)

        # Get cluster centers (dominant colors)
        colors = []
        for i, center in enumerate(kmeans.cluster_centers_):
            r, g, b = center.astype(int)
            hex_color = f"#{r:02x}{g:02x}{b:02x}"
            color_name = f"Color {i+1}"
            colors.append(Color(color_name, hex_color, (r, g, b)))

        # Categorize colors
        primary_colors = colors[:2] if len(colors) >= 2 else colors
        secondary_colors = colors[2:4] if len(colors) >= 4 else []
        accent_colors = colors[4:] if len(colors) >= 5 else []

        return ColorPalette(
            name=palette_name,
            primary_colors=primary_colors,
            secondary_colors=secondary_colors,
            accent_colors=accent_colors
        )

    except ImportError:
        logger.warning("sklearn not available for color extraction")
        return None
    except Exception as e:
        logger.error(f"Failed to extract palette from image '{image_path}': {e}")
        return None


def blend_palettes(palette1: ColorPalette, palette2: ColorPalette,
                  blend_ratio: float = 0.5) -> ColorPalette:
    """
    Blend two color palettes together.

    Args:
        palette1: First palette
        palette2: Second palette
        blend_ratio: Blend ratio (0.0 = all palette1, 1.0 = all palette2)

    Returns:
        Blended ColorPalette
    """
    try:
        blended_name = f"{palette1.name} + {palette2.name}"

        def blend_colors(colors1: List[Color], colors2: List[Color]) -> List[Color]:
            blended = []
            max_len = max(len(colors1), len(colors2))

            for i in range(max_len):
                color1 = colors1[i] if i < len(colors1) else None
                color2 = colors2[i] if i < len(colors2) else None

                if color1 and color2 and color1.rgb and color2.rgb:
                    # Blend RGB values
                    r = int(color1.rgb[0] * (1 - blend_ratio) + color2.rgb[0] * blend_ratio)
                    g = int(color1.rgb[1] * (1 - blend_ratio) + color2.rgb[1] * blend_ratio)
                    b = int(color1.rgb[2] * (1 - blend_ratio) + color2.rgb[2] * blend_ratio)

                    hex_color = f"#{r:02x}{g:02x}{b:02x}"
                    name = f"Blended {i+1}"
                    blended.append(Color(name, hex_color, (r, g, b)))
                elif color1:
                    blended.append(color1)
                elif color2:
                    blended.append(color2)

            return blended

        return ColorPalette(
            name=blended_name,
            primary_colors=blend_colors(palette1.primary_colors, palette2.primary_colors),
            secondary_colors=blend_colors(palette1.secondary_colors, palette2.secondary_colors),
            accent_colors=blend_colors(palette1.accent_colors, palette2.accent_colors),
            neutral_colors=blend_colors(palette1.neutral_colors, palette2.neutral_colors)
        )

    except Exception as e:
        logger.error(f"Failed to blend palettes: {e}")
        return palette1</content>
<parameter name="filePath">c:\Users\Baxter\Documents\ComfyUI_env\ComfyUI\custom_nodes\Comfy Gimpy Node Pack\gimp_comfy_bridge\brandkit\palette.py