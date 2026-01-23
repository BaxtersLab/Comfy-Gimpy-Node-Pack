"""
Font Management Module.

Provides font loading, validation, and fallback logic for brand kits.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
import os

from .kit import FontSpec

logger = logging.getLogger(__name__)


class FontManager:
    """Manager class for font operations."""

    def __init__(self):
        """Initialize the font manager."""
        self.system_fonts = self._discover_system_fonts()
        self.loaded_fonts: Dict[str, FontSpec] = {}

    def _discover_system_fonts(self) -> Dict[str, str]:
        """
        Discover available system fonts.

        Returns:
            Dictionary mapping font names to file paths
        """
        system_fonts = {}

        # Common system font directories
        font_dirs = []

        if os.name == 'nt':  # Windows
            font_dirs = [
                "C:\\Windows\\Fonts",
                str(Path.home() / "AppData\\Local\\Microsoft\\Windows\\Fonts")
            ]
        elif os.name == 'posix':  # macOS/Linux
            font_dirs = [
                "/System/Library/Fonts",
                "/Library/Fonts",
                "/usr/share/fonts",
                str(Path.home() / ".fonts")
            ]

        # Scan font directories
        for font_dir in font_dirs:
            if Path(font_dir).exists():
                self._scan_font_directory(font_dir, system_fonts)

        return system_fonts

    def _scan_font_directory(self, directory: str, fonts_dict: Dict[str, str]) -> None:
        """
        Scan a font directory and add fonts to the dictionary.

        Args:
            directory: Directory to scan
            fonts_dict: Dictionary to update with found fonts
        """
        try:
            path = Path(directory)
            for font_file in path.rglob("*"):
                if font_file.is_file() and font_file.suffix.lower() in ['.ttf', '.otf', '.woff', '.woff2']:
                    # Extract font name from filename (simplified)
                    font_name = font_file.stem.replace('-', ' ').replace('_', ' ').title()
                    fonts_dict[font_name] = str(font_file)
        except Exception as e:
            logger.warning(f"Failed to scan font directory '{directory}': {e}")

    def is_font_available(self, font_spec: FontSpec) -> bool:
        """
        Check if a font specification is available.

        Args:
            font_spec: FontSpec to check

        Returns:
            True if font is available
        """
        # Check primary font
        if font_spec.family in self.system_fonts:
            return True

        # Check fallbacks
        for fallback in font_spec.fallback_fonts:
            if fallback in self.system_fonts:
                return True

        # Check generic fallbacks
        generic_fallbacks = ['serif', 'sans-serif', 'monospace', 'cursive', 'fantasy']
        if any(fallback in generic_fallbacks for fallback in [font_spec.family] + font_spec.fallback_fonts):
            return True

        return False

    def validate_font_spec(self, font_spec: FontSpec) -> List[str]:
        """
        Validate a font specification.

        Args:
            font_spec: FontSpec to validate

        Returns:
            List of validation errors
        """
        errors = []

        if not font_spec.family or not font_spec.family.strip():
            errors.append("Font family is required")

        # Check availability
        if not self.is_font_available(font_spec):
            errors.append(f"Font '{font_spec.family}' is not available on this system")

        # Validate weight
        valid_weights = ['normal', 'bold', 'lighter', 'bolder', '100', '200', '300', '400', '500', '600', '700', '800', '900']
        if font_spec.weight not in valid_weights:
            errors.append(f"Invalid font weight '{font_spec.weight}'")

        # Validate style
        valid_styles = ['normal', 'italic', 'oblique']
        if font_spec.style not in valid_styles:
            errors.append(f"Invalid font style '{font_spec.style}'")

        # Validate size
        if font_spec.size is not None and (font_spec.size < 8 or font_spec.size > 200):
            errors.append(f"Font size {font_spec.size} out of range (8-200px)")

        return errors

    def get_font_fallbacks(self, font_spec: FontSpec) -> List[str]:
        """
        Get complete fallback chain for a font specification.

        Args:
            font_spec: FontSpec to get fallbacks for

        Returns:
            Ordered list of font families to try
        """
        fallbacks = [font_spec.family]

        # Add user-specified fallbacks
        fallbacks.extend(font_spec.fallback_fonts)

        # Add generic fallbacks based on style
        if font_spec.style == 'monospace' or 'mono' in font_spec.family.lower():
            fallbacks.extend(['monospace', 'Courier New', 'Courier'])
        elif any(word in font_spec.family.lower() for word in ['script', 'cursive', 'handwriting']):
            fallbacks.extend(['cursive', 'Comic Sans MS'])
        elif any(word in font_spec.family.lower() for word in ['serif', 'times', 'georgia']):
            fallbacks.extend(['serif', 'Times New Roman', 'Times'])
        else:
            # Default to sans-serif
            fallbacks.extend(['sans-serif', 'Arial', 'Helvetica'])

        # Remove duplicates while preserving order
        seen = set()
        unique_fallbacks = []
        for font in fallbacks:
            if font not in seen:
                seen.add(font)
                unique_fallbacks.append(font)

        return unique_fallbacks

    def get_similar_fonts(self, font_spec: FontSpec, limit: int = 5) -> List[str]:
        """
        Find similar fonts to a given font specification.

        Args:
            font_spec: FontSpec to find similar fonts for
            limit: Maximum number of similar fonts to return

        Returns:
            List of similar font names
        """
        similar = []
        target_family = font_spec.family.lower()

        # Simple similarity based on substring matching
        for font_name in self.system_fonts.keys():
            if target_family in font_name.lower() and font_name != font_spec.family:
                similar.append(font_name)
                if len(similar) >= limit:
                    break

        return similar

    def load_font(self, font_spec: FontSpec) -> Optional[str]:
        """
        Load a font and return its file path.

        Args:
            font_spec: FontSpec to load

        Returns:
            Font file path or None if not found
        """
        # Check primary font
        if font_spec.family in self.system_fonts:
            return self.system_fonts[font_spec.family]

        # Check fallbacks
        for fallback in font_spec.fallback_fonts:
            if fallback in self.system_fonts:
                logger.info(f"Using fallback font '{fallback}' for '{font_spec.family}'")
                return self.system_fonts[fallback]

        logger.warning(f"Font '{font_spec.family}' and fallbacks not found")
        return None

    def get_available_fonts(self, category: Optional[str] = None) -> List[str]:
        """
        Get list of available fonts, optionally filtered by category.

        Args:
            category: Font category to filter by ('serif', 'sans-serif', 'monospace', etc.)

        Returns:
            List of available font names
        """
        fonts = list(self.system_fonts.keys())

        if category:
            category = category.lower()
            filtered = []

            if category == 'serif':
                keywords = ['serif', 'times', 'georgia', 'garamond']
            elif category == 'sans-serif':
                keywords = ['sans', 'arial', 'helvetica', 'verdana']
            elif category == 'monospace':
                keywords = ['mono', 'courier', 'consolas', 'menlo']
            elif category == 'script':
                keywords = ['script', 'cursive', 'handwriting']
            else:
                keywords = [category]

            for font in fonts:
                if any(keyword in font.lower() for keyword in keywords):
                    filtered.append(font)

            return filtered

        return sorted(fonts)

    def create_font_stack_css(self, font_spec: FontSpec) -> str:
        """
        Create CSS font-family stack for a font specification.

        Args:
            font_spec: FontSpec to create CSS for

        Returns:
            CSS font-family declaration
        """
        fallbacks = self.get_font_fallbacks(font_spec)
        font_stack = ", ".join(f"'{font}'" for font in fallbacks)
        return f"font-family: {font_stack};"

    def get_font_metrics(self, font_spec: FontSpec) -> Optional[Dict[str, Any]]:
        """
        Get font metrics for a font specification.

        Args:
            font_spec: FontSpec to get metrics for

        Returns:
            Dictionary with font metrics or None if unavailable
        """
        # This would require a font parsing library like fonttools
        # For now, return basic info
        font_path = self.load_font(font_spec)
        if font_path:
            try:
                path_obj = Path(font_path)
                return {
                    'file_path': font_path,
                    'file_size': path_obj.stat().st_size,
                    'file_modified': path_obj.stat().st_mtime,
                    'available': True
                }
            except Exception as e:
                logger.error(f"Failed to get font metrics for '{font_path}': {e}")

        return {
            'available': False,
            'error': 'Font not found'
        }


# Global font manager instance
_font_manager: Optional[FontManager] = None


def get_font_manager() -> FontManager:
    """Get the global font manager instance."""
    global _font_manager
    if _font_manager is None:
        _font_manager = FontManager()
    return _font_manager


def load_font(font_spec: FontSpec) -> Optional[str]:
    """
    Convenience function to load a font.

    Args:
        font_spec: FontSpec to load

    Returns:
        Font file path or None
    """
    return get_font_manager().load_font(font_spec)


def get_font_fallbacks(font_spec: FontSpec) -> List[str]:
    """
    Convenience function to get font fallbacks.

    Args:
        font_spec: FontSpec to get fallbacks for

    Returns:
        List of fallback fonts
    """
    return get_font_manager().get_font_fallbacks(font_spec)


def validate_font_spec(font_spec: FontSpec) -> List[str]:
    """
    Convenience function to validate a font spec.

    Args:
        font_spec: FontSpec to validate

    Returns:
        List of validation errors
    """
    return get_font_manager().validate_font_spec(font_spec)</content>
<parameter name="filePath">c:\Users\Baxter\Documents\ComfyUI_env\ComfyUI\custom_nodes\Comfy Gimpy Node Pack\gimp_comfy_bridge\brandkit\fonts.py