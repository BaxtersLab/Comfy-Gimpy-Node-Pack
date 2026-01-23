"""
Styles API for web interface.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def get_style_categories() -> List[Dict[str, Any]]:
    """
    Get all style categories.

    Returns:
        List of category dictionaries
    """
    try:
        from gimp_comfy_bridge.gimp_plugin.plugin import list_style_categories
        return list_style_categories()
    except Exception as e:
        logger.error(f"Failed to get style categories: {e}")
        return []


def get_styles_in_category(category: str) -> List[Dict[str, Any]]:
    """
    Get styles in a specific category.

    Args:
        category (str): Category name

    Returns:
        List of style dictionaries
    """
    try:
        from gimp_comfy_bridge.gimp_plugin.plugin import list_styles_in_category
        return list_styles_in_category(category)
    except Exception as e:
        logger.error(f"Failed to get styles in category {category}: {e}")
        return []


def get_style_preview_path(category: str, name: str) -> Optional[Path]:
    """
    Get the preview image path for a style.

    Args:
        category (str): Style category
        name (str): Style name

    Returns:
        Path to preview or None if not found
    """
    try:
        from gimp_comfy_bridge.shared.config import load_config
        config = load_config()
        preview_path = config.styles_dir / category / name / "preview.png"

        if preview_path.exists():
            return preview_path
        return None

    except Exception as e:
        logger.error(f"Failed to get style preview path: {e}")
        return None