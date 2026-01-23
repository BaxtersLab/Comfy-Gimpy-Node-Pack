"""
Template preview loading for Comfy Gimpy Studio.
"""

import logging
from pathlib import Path
from typing import Optional, Union, Any

# Try to import PIL, but make it optional
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    Image = None

logger = logging.getLogger(__name__)


def load_preview(preview_path: Path) -> Optional[Union[Any, bytes]]:
    """
    Load template preview image.

    Args:
        preview_path: Path to preview.png file

    Returns:
        PIL Image object if PIL is available, otherwise raw bytes
        None if preview doesn't exist or can't be loaded
    """
    if not preview_path.exists():
        logger.debug(f"Preview file not found: {preview_path}")
        return None

    try:
        if PIL_AVAILABLE:
            # Load as PIL Image
            image = Image.open(preview_path)
            # Convert to RGB if necessary
            if image.mode not in ('RGB', 'RGBA'):
                image = image.convert('RGB')
            logger.debug(f"Loaded preview image: {preview_path} ({image.size})")
            return image
        else:
            # Load as raw bytes
            with open(preview_path, 'rb') as f:
                data = f.read()
            logger.debug(f"Loaded preview data: {preview_path} ({len(data)} bytes)")
            return data

    except Exception as e:
        logger.error(f"Failed to load preview from {preview_path}: {e}")
        return None


def save_preview(image: Union[Any, bytes], preview_path: Path) -> bool:
    """
    Save template preview image.

    Args:
        image: PIL Image object or raw bytes
        preview_path: Path where to save the preview

    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure parent directory exists
        preview_path.parent.mkdir(parents=True, exist_ok=True)

        if PIL_AVAILABLE and isinstance(image, Image.Image):
            # Save PIL Image
            image.save(preview_path, 'PNG')
            logger.debug(f"Saved preview image: {preview_path}")
        elif isinstance(image, bytes):
            # Save raw bytes
            with open(preview_path, 'wb') as f:
                f.write(image)
            logger.debug(f"Saved preview data: {preview_path}")
        else:
            logger.error(f"Unsupported image type: {type(image)}")
            return False

        return True

    except Exception as e:
        logger.error(f"Failed to save preview to {preview_path}: {e}")
        return False


def get_preview_dimensions(preview_path: Path) -> Optional[tuple[int, int]]:
    """
    Get dimensions of preview image without loading the full image.

    Args:
        preview_path: Path to preview.png file

    Returns:
        Tuple of (width, height) or None if can't determine
    """
    if not preview_path.exists():
        return None

    if not PIL_AVAILABLE:
        logger.warning("PIL not available, cannot get preview dimensions")
        return None

    try:
        with Image.open(preview_path) as img:
            return img.size
    except Exception as e:
        logger.error(f"Failed to get dimensions for {preview_path}: {e}")
        return None