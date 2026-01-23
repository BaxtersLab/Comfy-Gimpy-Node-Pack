"""
Templates API for web interface.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def get_template_categories() -> List[Dict[str, Any]]:
    """
    Get all template categories.

    Returns:
        List of category dictionaries
    """
    try:
        from gimp_comfy_bridge.gimp_plugin.plugin import list_template_categories
        return list_template_categories()
    except Exception as e:
        logger.error(f"Failed to get template categories: {e}")
        return []


def get_templates_in_category(category: str) -> List[Dict[str, Any]]:
    """
    Get templates in a specific category.

    Args:
        category (str): Category name

    Returns:
        List of template dictionaries
    """
    try:
        from gimp_comfy_bridge.gimp_plugin.plugin import list_templates_in_category
        return list_templates_in_category(category)
    except Exception as e:
        logger.error(f"Failed to get templates in category {category}: {e}")
        return []


def get_template_preview_path(category: str, name: str) -> Optional[Path]:
    """
    Get the preview image path for a template.

    Args:
        category (str): Template category
        name (str): Template name

    Returns:
        Path to preview or None if not found
    """
    try:
        from gimp_comfy_bridge.shared.config import load_config
        config = load_config()
        preview_path = config.templates_dir / category / name / "preview.png"

        if preview_path.exists():
            return preview_path
        return None

    except Exception as e:
        logger.error(f"Failed to get template preview path: {e}")
        return None