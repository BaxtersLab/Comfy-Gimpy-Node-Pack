"""
Utility functions for GIMP operations.
"""

import logging
import tempfile
from pathlib import Path
from typing import Optional

# Try to import GIMP modules
try:
    import gimp
    from gimpfu import *
    from gimpenums import *
    GIMP_AVAILABLE = True
except ImportError:
    GIMP_AVAILABLE = False

logger = logging.getLogger(__name__)

def export_current_layer(temp_path: Path) -> Path:
    """
    Export current layer to temporary path.

    Args:
        temp_path (Path): Temporary path.

    Returns:
        Path: Path to exported image.

    Raises:
        ValueError: If temp_path is invalid or no active layer.
        RuntimeError: If export fails.
    """
    if not isinstance(temp_path, Path):
        raise ValueError("temp_path must be a Path object")

    if not temp_path.exists():
        raise ValueError(f"Temporary path does not exist: {temp_path}")

    if not temp_path.is_dir():
        raise ValueError(f"Temporary path is not a directory: {temp_path}")

    if not GIMP_AVAILABLE:
        # Development mode - create dummy file
        image_path = temp_path / "layer.png"
        try:
            with open(image_path, 'wb') as f:
                f.write(b'dummy image data')
            return image_path
        except Exception as e:
            raise RuntimeError(f"Failed to create dummy file in development mode: {e}")

    try:
        # Validate GIMP state
        try:
            image = gimp.image_list()[0]  # Get active image
        except IndexError:
            raise ValueError("No active image found")

        try:
            layer = gimp.get_active_layer(image)
        except Exception:
            raise ValueError("Failed to get active layer")

        if not layer:
            raise ValueError("No active layer found")

        # Check layer dimensions
        if layer.width <= 0 or layer.height <= 0:
            raise ValueError(f"Invalid layer dimensions: {layer.width}x{layer.height}")

        # Create temporary file path
        image_path = temp_path / "layer.png"

        # Export layer as PNG
        try:
            pdb.gimp_file_save(
                image, layer, str(image_path), str(image_path),
                run_mode=RUN_NONINTERACTIVE
            )
        except Exception as e:
            raise RuntimeError(f"GIMP export failed: {e}")

        if not image_path.exists():
            raise RuntimeError("Export completed but file was not created")

        # Check file size (basic validation)
        file_size = image_path.stat().st_size
        if file_size == 0:
            image_path.unlink()  # Clean up empty file
            raise RuntimeError("Exported file is empty")

        # Reasonable size limit (100MB)
        if file_size > 100 * 1024 * 1024:
            image_path.unlink()  # Clean up oversized file
            raise RuntimeError(f"Exported file too large: {file_size} bytes")

        logger.info(f"Exported current layer to: {image_path} ({file_size} bytes)")
        return image_path

    except ValueError:
        raise  # Re-raise validation errors
    except Exception as e:
        logger.error(f"Failed to export current layer: {e}")
        raise RuntimeError(f"Layer export failed: {e}")

def export_selection_mask(temp_path: Path) -> Optional[Path]:
    """
    Export selection mask to temporary path.

    Args:
        temp_path (Path): Temporary path.

    Returns:
        Optional[Path]: Path to exported mask, or None if no selection.

    Raises:
        ValueError: If temp_path is invalid.
        RuntimeError: If mask export fails.
    """
    if not isinstance(temp_path, Path):
        raise ValueError("temp_path must be a Path object")

    if not temp_path.exists():
        raise ValueError(f"Temporary path does not exist: {temp_path}")

    if not temp_path.is_dir():
        raise ValueError(f"Temporary path is not a directory: {temp_path}")

    if not GIMP_AVAILABLE:
        # Development mode
        return None

    try:
        # Validate GIMP state
        try:
            image = gimp.image_list()[0]
        except IndexError:
            raise ValueError("No active image found")

        # Check if selection exists
        try:
            has_selection = not pdb.gimp_selection_is_empty(image)
        except Exception as e:
            logger.warning(f"Failed to check selection status: {e}")
            return None

        if not has_selection:
            return None

        mask_path = temp_path / "mask.png"

        # Create a new channel from selection
        try:
            channel = pdb.gimp_selection_save(image)
        except Exception as e:
            raise RuntimeError(f"Failed to create selection channel: {e}")

        if not channel:
            raise RuntimeError("Failed to create selection channel")

        # Export channel as mask
        try:
            pdb.gimp_file_save(
                image, channel, str(mask_path), str(mask_path),
                run_mode=RUN_NONINTERACTIVE
            )
        except Exception as e:
            # Clean up channel before re-raising
            try:
                pdb.gimp_image_remove_channel(image, channel)
            except Exception:
                pass  # Ignore cleanup errors
            raise RuntimeError(f"Failed to export mask: {e}")

        # Remove temporary channel
        try:
            pdb.gimp_image_remove_channel(image, channel)
        except Exception as e:
            logger.warning(f"Failed to remove temporary channel: {e}")

        if not mask_path.exists():
            raise RuntimeError("Mask export completed but file was not created")

        # Check file size
        file_size = mask_path.stat().st_size
        if file_size == 0:
            mask_path.unlink()
            raise RuntimeError("Exported mask file is empty")

        if file_size > 50 * 1024 * 1024:  # 50MB limit for masks
            mask_path.unlink()
            raise RuntimeError(f"Exported mask too large: {file_size} bytes")

        logger.info(f"Exported selection mask to: {mask_path} ({file_size} bytes)")
        return mask_path

    except ValueError:
        raise  # Re-raise validation errors
    except RuntimeError:
        raise  # Re-raise runtime errors
    except Exception as e:
        logger.error(f"Failed to export selection mask: {e}")
        raise RuntimeError(f"Mask export failed: {e}")

def insert_image_as_new_layer(image_path: Path):
    """
    Insert image as new layer in GIMP.

    Args:
        image_path (Path): Path to image.

    Raises:
        ValueError: If image_path is invalid.
        RuntimeError: If insertion fails.
    """
    if not isinstance(image_path, Path):
        raise ValueError("image_path must be a Path object")

    if not image_path.exists():
        raise ValueError(f"Image file not found: {image_path}")

    if not image_path.is_file():
        raise ValueError(f"Path is not a file: {image_path}")

    # Check file size
    try:
        file_size = image_path.stat().st_size
        if file_size == 0:
            raise ValueError("Image file is empty")
        if file_size > 200 * 1024 * 1024:  # 200MB limit
            raise ValueError(f"Image file too large: {file_size} bytes")
    except Exception as e:
        raise ValueError(f"Failed to check image file: {e}")

    if not GIMP_AVAILABLE:
        logger.info(f"Would insert image as layer: {image_path}")
        return

    try:
        # Validate GIMP state
        try:
            image = gimp.image_list()[0]
        except IndexError:
            raise RuntimeError("No active image found")

        # Load image as new layer
        try:
            new_layer = pdb.gimp_file_load_layer(image, str(image_path))
        except Exception as e:
            raise RuntimeError(f"Failed to load image as layer: {e}")

        if not new_layer:
            raise RuntimeError("Failed to create new layer from image")

        # Add layer to image
        try:
            pdb.gimp_image_add_layer(image, new_layer, 0)
        except Exception as e:
            # Clean up layer if adding failed
            try:
                pdb.gimp_item_delete(new_layer)
            except Exception:
                pass
            raise RuntimeError(f"Failed to add layer to image: {e}")

        # Update display
        try:
            pdb.gimp_displays_flush()
        except Exception as e:
            logger.warning(f"Failed to flush displays: {e}")
            # Don't raise here as the layer was successfully added

        logger.info(f"Inserted image as new layer: {image_path}")

    except ValueError:
        raise  # Re-raise validation errors
    except RuntimeError:
        raise  # Re-raise runtime errors
    except Exception as e:
        logger.error(f"Failed to insert image as layer: {e}")
        raise RuntimeError(f"Layer insertion failed: {e}")

def generate_outpaint_mask(temp_path: Path) -> Path:
    """
    Generate outpaint mask for extending image.

    Args:
        temp_path (Path): Temporary path.

    Returns:
        Path: Path to generated mask.

    Raises:
        ValueError: If temp_path is invalid.
        RuntimeError: If mask generation fails.
    """
    if not isinstance(temp_path, Path):
        raise ValueError("temp_path must be a Path object")

    if not temp_path.exists():
        raise ValueError(f"Temporary path does not exist: {temp_path}")

    if not temp_path.is_dir():
        raise ValueError(f"Temporary path is not a directory: {temp_path}")

    if not GIMP_AVAILABLE:
        # Development mode
        mask_path = temp_path / "outpaint_mask.png"
        try:
            with open(mask_path, 'wb') as f:
                f.write(b'dummy mask data')
            return mask_path
        except Exception as e:
            raise RuntimeError(f"Failed to create dummy mask in development mode: {e}")

    try:
        # Validate GIMP state
        try:
            image = gimp.image_list()[0]
        except IndexError:
            raise ValueError("No active image found")

        # Validate image dimensions
        if image.width <= 0 or image.height <= 0:
            raise ValueError(f"Invalid image dimensions: {image.width}x{image.height}")

        mask_path = temp_path / "outpaint_mask.png"

        # Create a new image for the mask
        try:
            mask_image = pdb.gimp_image_new(image.width, image.height, RGB)
        except Exception as e:
            raise RuntimeError(f"Failed to create mask image: {e}")

        if not mask_image:
            raise RuntimeError("Failed to create mask image")

        try:
            # Create a white background layer
            background = pdb.gimp_layer_new(mask_image, mask_image.width, mask_image.height,
                                           RGB_IMAGE, "background", 100, NORMAL_MODE)
            if not background:
                raise RuntimeError("Failed to create background layer")

            pdb.gimp_image_add_layer(mask_image, background, 0)

            # Fill with white
            pdb.gimp_drawable_fill(background, WHITE_FILL)

            # Create a black rectangle in the center (the area to keep)
            # This creates a border mask for outpainting
            border_width = min(50, image.width // 20, image.height // 20)  # Adaptive border
            if border_width < 1:
                border_width = 1

            # Ensure border doesn't exceed image bounds
            center_width = max(1, image.width - 2 * border_width)
            center_height = max(1, image.height - 2 * border_width)

            pdb.gimp_rect_select(mask_image,
                               border_width, border_width,
                               center_width, center_height,
                               REPLACE, False, 0)
            pdb.gimp_edit_fill(background, BLACK_FILL)
            pdb.gimp_selection_none(mask_image)

            # Export mask
            pdb.gimp_file_save(mask_image, background, str(mask_path), str(mask_path),
                              run_mode=RUN_NONINTERACTIVE)

        except Exception as e:
            # Clean up mask image before re-raising
            try:
                pdb.gimp_image_delete(mask_image)
            except Exception:
                pass
            raise RuntimeError(f"Failed to generate mask content: {e}")

        # Clean up
        try:
            pdb.gimp_image_delete(mask_image)
        except Exception as e:
            logger.warning(f"Failed to clean up mask image: {e}")

        if not mask_path.exists():
            raise RuntimeError("Mask generation completed but file was not created")

        # Check file size
        file_size = mask_path.stat().st_size
        if file_size == 0:
            mask_path.unlink()
            raise RuntimeError("Generated mask file is empty")

        if file_size > 10 * 1024 * 1024:  # 10MB limit for masks
            mask_path.unlink()
            raise RuntimeError(f"Generated mask too large: {file_size} bytes")

        logger.info(f"Generated outpaint mask: {mask_path} ({file_size} bytes)")
        return mask_path

    except ValueError:
        raise  # Re-raise validation errors
    except RuntimeError:
        raise  # Re-raise runtime errors
    except Exception as e:
        logger.error(f"Failed to generate outpaint mask: {e}")
        raise RuntimeError(f"Mask generation failed: {e}")

def get_image_dimensions() -> tuple:
    """
    Get dimensions of current image.

    Returns:
        tuple: (width, height) - defaults to (1024, 1024) on error
    """
    if not GIMP_AVAILABLE:
        return (1024, 1024)  # Default for development

    try:
        try:
            image = gimp.image_list()[0]
        except IndexError:
            logger.warning("No active image found, using defaults")
            return (1024, 1024)

        if not image:
            logger.warning("Active image is None, using defaults")
            return (1024, 1024)

        width = getattr(image, 'width', 1024)
        height = getattr(image, 'height', 1024)

        # Validate dimensions
        if not isinstance(width, int) or not isinstance(height, int):
            logger.warning(f"Invalid dimension types: {type(width)}, {type(height)}")
            return (1024, 1024)

        if width <= 0 or height <= 0:
            logger.warning(f"Invalid dimensions: {width}x{height}")
            return (1024, 1024)

        # Reasonable limits
        if width > 32767 or height > 32767:
            logger.warning(f"Dimensions too large: {width}x{height}")
            return (1024, 1024)

        return (width, height)

    except Exception as e:
        logger.error(f"Failed to get image dimensions: {e}")
        return (1024, 1024)

def has_active_selection() -> bool:
    """
    Check if there's an active selection.

    Returns:
        bool: True if selection exists, False otherwise
    """
    if not GIMP_AVAILABLE:
        return False

    try:
        try:
            image = gimp.image_list()[0]
        except IndexError:
            return False

        if not image:
            return False

        try:
            return not pdb.gimp_selection_is_empty(image)
        except Exception as e:
            logger.warning(f"Failed to check selection status: {e}")
            return False

    except Exception as e:
        logger.error(f"Failed to check for active selection: {e}")
        return False

def get_active_layer_name() -> str:
    """
    Get name of active layer.

    Returns:
        str: Layer name or "Unknown" on error
    """
    if not GIMP_AVAILABLE:
        return "Layer"

    try:
        try:
            image = gimp.image_list()[0]
        except IndexError:
            return "Unknown"

        if not image:
            return "Unknown"

        try:
            layer = gimp.get_active_layer(image)
        except Exception:
            return "Unknown"

        if not layer:
            return "Unknown"

        name = getattr(layer, 'name', None)
        if not name:
            return "Unknown"

        # Validate name type and length
        if not isinstance(name, str):
            logger.warning(f"Layer name is not a string: {type(name)}")
            return "Unknown"

        if len(name) > 255:  # Reasonable limit
            logger.warning(f"Layer name too long: {len(name)} characters")
            return name[:255] + "..."

        return name

    except Exception as e:
        logger.error(f"Failed to get layer name: {e}")
        return "Unknown"