"""
I/O handlers for ComfyUI extension.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

def save_uploaded_image(image_data: bytes, temp_dir) -> str:
    """
    Save uploaded image.

    Args:
        image_data (bytes): Image data.
        temp_dir: Temporary directory path.

    Returns:
        str: Path to saved image.
    """
    try:
        temp_dir = Path(temp_dir)
        temp_dir.mkdir(exist_ok=True)
        image_path = temp_dir / "input.png"
        with open(image_path, 'wb') as f:
            f.write(image_data)
        logger.info(f"Saved uploaded image: {image_path}")
        return str(image_path)
    except Exception as e:
        logger.error(f"Failed to save uploaded image: {e}")
        raise

def save_uploaded_mask(mask_data: bytes, temp_dir) -> str:
    """
    Save uploaded mask.

    Args:
        mask_data (bytes): Mask data.
        temp_dir: Temporary directory path.

    Returns:
        str: Path to saved mask.
    """
    try:
        temp_dir = Path(temp_dir)
        temp_dir.mkdir(exist_ok=True)
        mask_path = temp_dir / "mask.png"
        with open(mask_path, 'wb') as f:
            f.write(mask_data)
        logger.info(f"Saved uploaded mask: {mask_path}")
        return str(mask_path)
    except Exception as e:
        logger.error(f"Failed to save uploaded mask: {e}")
        raise

def load_result_image(image_path: str) -> bytes:
    """
    Load result image.

    Args:
        image_path (str): Path to image.

    Returns:
        bytes: Image data.
    """
    try:
        with open(image_path, 'rb') as f:
            data = f.read()
        logger.info(f"Loaded result image: {image_path}")
        return data
    except Exception as e:
        logger.error(f"Failed to load result image: {e}")
        raise