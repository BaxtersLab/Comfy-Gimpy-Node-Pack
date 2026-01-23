"""
Style metadata handling for Comfy Gimpy Studio.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from ..shared.types import StyleMetadata

logger = logging.getLogger(__name__)


def load_style_metadata(metadata_path: Path) -> Optional[StyleMetadata]:
    """
    Load style metadata from JSON file.

    Args:
        metadata_path (Path): Path to style_metadata.json

    Returns:
        StyleMetadata or None if loading fails
    """
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Validate required fields
        if not validate_style_metadata(data):
            logger.error(f"Invalid style metadata in {metadata_path}")
            return None

        return StyleMetadata(
            name=data['name'],
            category=data['category'],
            description=data.get('description', ''),
            tags=data.get('tags', []),
            default_weight=data.get('default_weight', 1.0)
        )

    except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
        logger.error(f"Failed to load style metadata from {metadata_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error loading style metadata from {metadata_path}: {e}")
        return None


def validate_style_metadata(data: Dict[str, Any]) -> bool:
    """
    Validate style metadata structure.

    Args:
        data (dict): Metadata dictionary

    Returns:
        bool: True if valid
    """
    required_fields = ['name', 'category']

    # Check required fields
    for field in required_fields:
        if field not in data:
            logger.error(f"Missing required field: {field}")
            return False

        if not isinstance(data[field], str) or not data[field].strip():
            logger.error(f"Field {field} must be a non-empty string")
            return False

    # Validate optional fields
    if 'description' in data and not isinstance(data['description'], str):
        logger.error("Description must be a string")
        return False

    if 'tags' in data:
        if not isinstance(data['tags'], list):
            logger.error("Tags must be a list")
            return False
        if not all(isinstance(tag, str) for tag in data['tags']):
            logger.error("All tags must be strings")
            return False

    if 'default_weight' in data:
        if not isinstance(data['default_weight'], (int, float)):
            logger.error("Default weight must be a number")
            return False
        if not (0.0 <= data['default_weight'] <= 2.0):
            logger.error("Default weight must be between 0.0 and 2.0")
            return False

    return True