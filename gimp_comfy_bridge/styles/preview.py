"""
Style preview loading for Comfy Gimpy Studio.
"""

import logging
from pathlib import Path
from typing import Optional, Union, Any

logger = logging.getLogger(__name__)

# Try to import PIL, but make it optional
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None


def load_style_preview(preview_path: Path) -> Optional[Union[Any, bytes]]:
    """
    Load style preview image.

    Args:
        preview_path (Path): Path to preview.png

    Returns:
        PIL Image or bytes if PIL not available, or None if loading fails
    """
    if not preview_path.exists():
        logger.debug(f"Preview file does not exist: {preview_path}")
        return None

    try:
        if PIL_AVAILABLE:
            # Load with PIL
            image = Image.open(preview_path)
            # Convert to RGB if necessary
            if image.mode not in ('RGB', 'RGBA'):
                image = image.convert('RGB')
            return image
        else:
            # Load as raw bytes
            with open(preview_path, 'rb') as f:
                return f.read()

    except Exception as e:
        logger.error(f"Failed to load style preview from {preview_path}: {e}")
        return None


def save_style_preview(image: Union[Any, bytes], preview_path: Path) -> bool:
    """
    Save style preview image.

    Args:
        image: PIL Image or bytes
        preview_path (Path): Path to save preview.png

    Returns:
        bool: True if successful
    """
    try:
        preview_path.parent.mkdir(parents=True, exist_ok=True)

        if PIL_AVAILABLE and hasattr(image, 'save'):
            # Save PIL image
            image.save(preview_path, 'PNG')
        elif isinstance(image, bytes):
            # Save raw bytes
            with open(preview_path, 'wb') as f:
                f.write(image)
        else:
            logger.error(f"Unsupported image type: {type(image)}")
            return False

        logger.debug(f"Saved style preview to {preview_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to save style preview to {preview_path}: {e}")
        return False