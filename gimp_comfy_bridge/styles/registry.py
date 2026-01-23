"""
Style registry for Comfy Gimpy Studio.
Manages style discovery, caching, and organization.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from ..shared.types import StyleInfo, StyleCategory

logger = logging.getLogger(__name__)


class StyleRegistry:
    """
    Registry for managing style discovery and caching.
    """

    def __init__(self, styles_dir: Path):
        """
        Initialize the style registry.

        Args:
            styles_dir (Path): Directory containing style packs
        """
        self.styles_dir = styles_dir
        self._styles: Dict[str, Dict[str, StyleInfo]] = {}
        self._categories: Dict[str, StyleCategory] = {}
        self._scanned = False

    def scan_styles(self) -> None:
        """
        Scan the styles directory for available styles.
        """
        if self._scanned:
            return

        logger.info(f"Scanning styles directory: {self.styles_dir}")
        self._styles.clear()
        self._categories.clear()

        if not self.styles_dir.exists():
            logger.warning(f"Styles directory does not exist: {self.styles_dir}")
            self._scanned = True
            return

        # Scan each category directory
        for category_dir in self.styles_dir.iterdir():
            if not category_dir.is_dir():
                continue

            category_name = category_dir.name
            category_styles = {}

            # Scan each style in the category
            for style_dir in category_dir.iterdir():
                if not style_dir.is_dir():
                    continue

                style_name = style_dir.name
                style_info = self._load_style_info(category_name, style_name, style_dir)

                if style_info:
                    category_styles[style_name] = style_info

            if category_styles:
                self._styles[category_name] = category_styles

                # Create category info
                display_name = category_name.replace('_', ' ').title()
                description = f"Styles in the {display_name} category"
                style_count = len(category_styles)

                self._categories[category_name] = StyleCategory(
                    name=category_name,
                    display_name=display_name,
                    description=description,
                    style_count=style_count
                )

        self._scanned = True
        logger.info(f"Found {len(self._categories)} style categories with {sum(len(styles) for styles in self._styles.values())} total styles")

    def _load_style_info(self, category: str, name: str, style_dir: Path) -> Optional[StyleInfo]:
        """
        Load style information from a style directory.

        Args:
            category (str): Style category
            name (str): Style name
            style_dir (Path): Style directory path

        Returns:
            StyleInfo or None if loading fails
        """
        try:
            from .metadata import load_style_metadata

            # Check for required files
            metadata_file = style_dir / "style_metadata.json"
            model_file = style_dir / "model.safetensors"

            if not metadata_file.exists():
                logger.debug(f"No metadata file for style {category}/{name}")
                return None

            if not model_file.exists():
                logger.debug(f"No model file for style {category}/{name}")
                return None

            # Load metadata
            metadata = load_style_metadata(metadata_file)
            if not metadata:
                logger.debug(f"Failed to load metadata for style {category}/{name}")
                return None

            # Check for preview
            preview_path = style_dir / "preview.png"
            has_preview = preview_path.exists()

            return StyleInfo(
                name=name,
                category=category,
                path=style_dir,
                metadata=metadata,
                has_preview=has_preview
            )

        except Exception as e:
            logger.error(f"Error loading style info for {category}/{name}: {e}")
            return None

    def list_categories(self) -> List[StyleCategory]:
        """
        Get list of available style categories.

        Returns:
            List of StyleCategory objects
        """
        self.scan_styles()
        return list(self._categories.values())

    def list_styles(self, category: str) -> List[StyleInfo]:
        """
        Get list of styles in a specific category.

        Args:
            category (str): Category name

        Returns:
            List of StyleInfo objects
        """
        self.scan_styles()
        return list(self._styles.get(category, {}).values())

    def get_style_info(self, category: str, name: str) -> Optional[StyleInfo]:
        """
        Get information for a specific style.

        Args:
            category (str): Style category
            name (str): Style name

        Returns:
            StyleInfo or None if not found
        """
        self.scan_styles()
        category_styles = self._styles.get(category, {})
        return category_styles.get(name)

    def get_style_paths(self, category: str, name: str) -> Optional[Dict[str, Path]]:
        """
        Get file paths for a specific style.

        Args:
            category (str): Style category
            name (str): Style name

        Returns:
            Dict with 'model', 'metadata', 'preview' paths or None if not found
        """
        style_info = self.get_style_info(category, name)
        if not style_info:
            return None

        style_dir = style_info.path
        return {
            'model': style_dir / "model.safetensors",
            'metadata': style_dir / "style_metadata.json",
            'preview': style_dir / "preview.png"
        }