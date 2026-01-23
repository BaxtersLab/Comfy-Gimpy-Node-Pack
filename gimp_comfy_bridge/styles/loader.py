"""
Style loader for Comfy Gimpy Studio.
Handles loading and validation of style packs.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

from ..shared.types import StyleInfo

logger = logging.getLogger(__name__)


class StyleLoader:
    """
    Loader for style packs and their components.
    """

    def __init__(self, registry):
        """
        Initialize the style loader.

        Args:
            registry: StyleRegistry instance
        """
        self.registry = registry

    def load_style(self, category: str, name: str) -> Optional[Dict[str, Any]]:
        """
        Load a complete style pack.

        Args:
            category (str): Style category
            name (str): Style name

        Returns:
            Dict with 'info', 'model_path', 'metadata', 'preview' or None if loading fails
        """
        try:
            # Get style info from registry
            style_info = self.registry.get_style_info(category, name)
            if not style_info:
                logger.error(f"Style not found: {category}/{name}")
                return None

            # Get file paths
            paths = self.registry.get_style_paths(category, name)
            if not paths:
                logger.error(f"Could not get paths for style: {category}/{name}")
                return None

            # Load preview if available
            from .preview import load_style_preview
            preview = None
            if style_info.has_preview:
                preview = load_style_preview(paths['preview'])

            return {
                'info': style_info,
                'model_path': paths['model'],
                'metadata': style_info.metadata,
                'preview': preview
            }

        except Exception as e:
            logger.error(f"Failed to load style {category}/{name}: {e}")
            return None

    def validate_style_pack(self, style_dir: Path) -> bool:
        """
        Validate that a style directory contains all required files.

        Args:
            style_dir (Path): Style directory to validate

        Returns:
            bool: True if valid
        """
        required_files = [
            "style_metadata.json",
            "model.safetensors"
        ]

        for filename in required_files:
            file_path = style_dir / filename
            if not file_path.exists():
                logger.error(f"Missing required file: {file_path}")
                return False

        # Validate metadata
        from .metadata import load_style_metadata
        metadata_path = style_dir / "style_metadata.json"
        metadata = load_style_metadata(metadata_path)
        if not metadata:
            logger.error(f"Invalid metadata in: {metadata_path}")
            return False

        return True

    def get_style_model_path(self, category: str, name: str) -> Optional[Path]:
        """
        Get the model file path for a style.

        Args:
            category (str): Style category
            name (str): Style name

        Returns:
            Path to model.safetensors or None if not found
        """
        paths = self.registry.get_style_paths(category, name)
        return paths.get('model') if paths else None

    def get_style_weight(self, category: str, name: str) -> float:
        """
        Get the default weight for a style.

        Args:
            category (str): Style category
            name (str): Style name

        Returns:
            Default weight (1.0 if not found)
        """
        style_info = self.registry.get_style_info(category, name)
        if style_info and style_info.metadata:
            return style_info.metadata.default_weight
        return 1.0