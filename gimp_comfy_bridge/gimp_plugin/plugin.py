"""
Main plugin logic for GIMP integration.
"""

import base64
import logging
from pathlib import Path
from shared.history import HistoryManager
from shared.protocol import encode_params, decode_base64_image
from gimp_plugin.api_client import run_workflow
from gimp_plugin.utils import export_current_layer, export_selection_mask, insert_image_as_new_layer, generate_outpaint_mask
from gimp_plugin.ui_panel import update_status, show_error

logger = logging.getLogger(__name__)
history = HistoryManager()

def undo_ai_step():
    """
    Undo the last AI step.
    """
    try:
        logger.info("Undoing AI step")
        path = history.undo()
        if path:
            insert_image_as_new_layer(Path(path))
            update_status("Undid to previous step")
        else:
            show_error("Cannot undo further")
    except Exception as e:
        logger.error(f"Undo failed: {e}")
        show_error(f"Undo failed: {e}")

def redo_ai_step():
    """
    Redo the next AI step.
    """
    try:
        logger.info("Redoing AI step")
        path = history.redo()
        if path:
            insert_image_as_new_layer(Path(path))
            update_status("Redid to next step")
        else:
            show_error("Cannot redo further")
    except Exception as e:
        logger.error(f"Redo failed: {e}")
        show_error(f"Redo failed: {e}")

def check_comfyui_available():
    """
    Check if ComfyUI backend is available.

    Returns:
        bool: True if available, False otherwise
    """
    try:
        from gimp_plugin.api_client import ping_backend
        ping_backend()
        return True
    except Exception as e:
        logger.warning(f"ComfyUI backend not available: {e}")
        return False
    """
    Build parameters for workflow.

    Args:
        mode (str): Workflow mode.
        workflow_name (str): Workflow name.
        prompt (str, optional): Prompt.
        negative_prompt (str, optional): Negative prompt.
        width (int, optional): Width.
        height (int, optional): Height.
        strength (float, optional): Strength.
        upscale_factor (float, optional): Upscale factor.
        model (str, optional): Model.
        loras (list, optional): LoRAs.
        controlnet (list, optional): ControlNet.

    Returns:
        dict: Parameters dictionary.
    """
    params = {
        "mode": mode,
        "workflow_name": workflow_name,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "width": width,
        "height": height,
        "strength": strength,
        "upscale_factor": upscale_factor,
        "model": model,
        "loras": loras or [],
        "controlnet": controlnet or []
    }
    return {k: v for k, v in params.items() if v is not None}

def _execute_workflow(mode, workflow_name, params, export_image=True, export_mask=False, generate_mask=False):
    """
    Internal workflow execution with comprehensive error handling and validation.

    Args:
        mode (str): Mode.
        workflow_name (str): Workflow name.
        params (dict): Parameters.
        export_image (bool): Whether to export image.
        export_mask (bool): Whether to export mask.
        generate_mask (bool): Whether to generate mask.

    Raises:
        ValueError: If parameters are invalid.
        RuntimeError: If workflow execution fails.
    """
    # Validate inputs
    if not isinstance(mode, str) or not mode.strip():
        raise ValueError("Mode must be a non-empty string")
    if not isinstance(workflow_name, str) or not workflow_name.strip():
        raise ValueError("Workflow name must be a non-empty string")
    if not isinstance(params, dict):
        raise ValueError("Params must be a dictionary")

    # Initialize history session if needed
    try:
        if not history.session_id:
            history.start_session()
    except Exception as e:
        logger.error(f"Failed to initialize history session: {e}")
        raise RuntimeError(f"Cannot initialize session: {e}")

    # Handle undo state
    try:
        if history.current_step > 0:  # If undo was used
            history.truncate_forward_history()
    except Exception as e:
        logger.warning(f"Failed to truncate forward history: {e}")
        # Continue - not critical

    step_dir = None
    image_path = None
    mask_path = None
    output_path = None

    try:
        # Get step directory
        step_dir = history.next_step_dir()

        # Export image if requested
        if export_image:
            try:
                image_path = export_current_layer(step_dir)
                if not image_path or not image_path.exists():
                    raise RuntimeError("Failed to export current layer")
            except Exception as e:
                raise RuntimeError(f"Image export failed: {e}")

        # Export or generate mask
        if export_mask:
            try:
                mask_path = export_selection_mask(step_dir)
                if not mask_path:
                    logger.warning("No selection mask available for export_mask=True")
            except Exception as e:
                logger.warning(f"Mask export failed: {e}")
                mask_path = None
        elif generate_mask:
            try:
                mask_path = generate_outpaint_mask(step_dir)
                if not mask_path or not mask_path.exists():
                    raise RuntimeError("Failed to generate outpaint mask")
            except Exception as e:
                raise RuntimeError(f"Mask generation failed: {e}")

        # Always write params.json (requirement from Phase 5)
        try:
            params_json = encode_params(params)
            params_file = step_dir / "params.json"
            with open(params_file, 'w', encoding='utf-8') as f:
                f.write(params_json)
        except Exception as e:
            raise RuntimeError(f"Failed to save parameters: {e}")

        # Load image and mask data
        image_data = None
        if image_path and image_path.exists():
            try:
                with open(image_path, 'rb') as f:
                    image_data = f.read()
                # Validate reasonable file size
                if len(image_data) > 50 * 1024 * 1024:  # 50MB
                    raise RuntimeError("Image file too large (>50MB)")
            except Exception as e:
                raise RuntimeError(f"Failed to read image data: {e}")

        mask_data = None
        if mask_path and mask_path.exists():
            try:
                with open(mask_path, 'rb') as f:
                    mask_data = f.read()
                # Validate reasonable file size
                if len(mask_data) > 10 * 1024 * 1024:  # 10MB
                    raise RuntimeError("Mask file too large (>10MB)")
            except Exception as e:
                logger.warning(f"Failed to read mask data: {e}")
                mask_data = None  # Continue without mask

        # Execute workflow
        try:
            response = run_workflow(mode, workflow_name, params, image_data, mask_data)
        except Exception as e:
            raise RuntimeError(f"Workflow execution failed: {e}")

        # Process response
        try:
            if 'image_base64' not in response.result:
                raise RuntimeError("Response missing image_base64")

            result_image = decode_base64_image(response.result['image_base64'])

            # Validate result size
            if len(result_image) > 100 * 1024 * 1024:  # 100MB
                raise RuntimeError("Result image too large (>100MB)")

            output_path = step_dir / "output.png"
            with open(output_path, 'wb') as f:
                f.write(result_image)

        except Exception as e:
            raise RuntimeError(f"Failed to process workflow result: {e}")

        # Save step to history
        try:
            history.save_step(
                str(image_path) if image_path else None,
                str(mask_path) if mask_path else None,
                str(output_path),
                params
            )
        except Exception as e:
            logger.error(f"Failed to save step to history: {e}")
            # Continue - history failure shouldn't stop the workflow

        # Insert into GIMP
        try:
            insert_image_as_new_layer(output_path)
        except Exception as e:
            logger.error(f"Failed to insert result into GIMP: {e}")
            # Don't raise - GIMP insertion failure shouldn't stop the workflow

        update_status("Workflow completed successfully")
        logger.info(f"Workflow {workflow_name} completed successfully")

    except ValueError as e:
        # Parameter/validation errors
        error_msg = f"Validation error: {e}"
        logger.error(error_msg)
        show_error(error_msg)
        raise
    except RuntimeError as e:
        # Execution errors
        error_msg = f"Workflow execution failed: {e}"
        logger.error(error_msg)
        show_error(error_msg)
        raise
    except Exception as e:
        # Unexpected errors
        error_msg = f"Unexpected error: {e}"
        logger.error(error_msg)
        show_error("An unexpected error occurred. Check logs for details.")
        raise
    finally:
        # Cleanup temporary files if something went wrong
        # Note: We keep the step directory for history purposes
        pass

def send_current_layer_for_inpaint(prompt, negative_prompt=None):
    """
    Send current layer for inpainting with validation.

    Args:
        prompt (str): Prompt.
        negative_prompt (str, optional): Negative prompt.

    Raises:
        ValueError: If parameters are invalid.
    """
    if not prompt or not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt is required for inpainting")
    if len(prompt) > 1000:
        raise ValueError("Prompt too long (>1000 characters)")

    if negative_prompt and (not isinstance(negative_prompt, str) or len(negative_prompt) > 1000):
        raise ValueError("Negative prompt must be a string <= 1000 characters")

    # Check ComfyUI availability
    if not check_comfyui_available():
        from gimp_plugin.ui_panel import show_error
        show_error("ComfyUI backend is not available. Please start ComfyUI and try again.")
        return

    params = build_params("inpaint", "inpaint_basic", prompt=prompt, negative_prompt=negative_prompt)
    _execute_workflow("inpaint", "inpaint_basic", params, export_image=True, export_mask=True)

def send_current_layer_for_upscale(upscale_factor=2.0):
    """
    Send current layer for upscaling with validation.

    Args:
        upscale_factor (float): Upscale factor.

    Raises:
        ValueError: If parameters are invalid.
    """
    if not isinstance(upscale_factor, (int, float)) or upscale_factor <= 1 or upscale_factor > 4:
        raise ValueError("Upscale factor must be a number between 1 and 4")

    # Check ComfyUI availability
    if not check_comfyui_available():
        from gimp_plugin.ui_panel import show_error
        show_error("ComfyUI backend is not available. Please start ComfyUI and try again.")
        return

    params = build_params("upscale", "upscale_basic", upscale_factor=upscale_factor)
    _execute_workflow("upscale", "upscale_basic", params, export_image=True)

def generate_from_text(prompt, negative_prompt=None, width=1024, height=1024):
    """
    Generate from text with validation.

    Args:
        prompt (str): Prompt.
        negative_prompt (str, optional): Negative prompt.
        width (int): Width.
        height (int): Height.

    Raises:
        ValueError: If parameters are invalid.
    """
    if not prompt or not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt is required for text generation")
    if len(prompt) > 1000:
        raise ValueError("Prompt too long (>1000 characters)")

    if negative_prompt and (not isinstance(negative_prompt, str) or len(negative_prompt) > 1000):
        raise ValueError("Negative prompt must be a string <= 1000 characters")

    if not isinstance(width, int) or not (64 <= width <= 2048):
        raise ValueError("Width must be an integer between 64 and 2048")
    if not isinstance(height, int) or not (64 <= height <= 2048):
        raise ValueError("Height must be an integer between 64 and 2048")

    # Check ComfyUI availability
    if not check_comfyui_available():
        from gimp_plugin.ui_panel import show_error
        show_error("ComfyUI backend is not available. Please start ComfyUI and try again.")
        return

    params = build_params("txt2img", "txt2img_basic", prompt=prompt, negative_prompt=negative_prompt, width=width, height=height)
    _execute_workflow("txt2img", "txt2img_basic", params, export_image=False)

def send_current_layer_for_img2img(prompt, strength=0.6):
    """
    Send current layer for img2img with validation.

    Args:
        prompt (str): Prompt.
        strength (float): Strength.

    Raises:
        ValueError: If parameters are invalid.
    """
    if not prompt or not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt is required for img2img")
    if len(prompt) > 1000:
        raise ValueError("Prompt too long (>1000 characters)")

    if not isinstance(strength, (int, float)) or not (0 < strength <= 1):
        raise ValueError("Strength must be a number between 0 and 1")

    # Check ComfyUI availability
    if not check_comfyui_available():
        from gimp_plugin.ui_panel import show_error
        show_error("ComfyUI backend is not available. Please start ComfyUI and try again.")
        return

    params = build_params("img2img", "img2img_basic", prompt=prompt, strength=strength)
    _execute_workflow("img2img", "img2img_basic", params, export_image=True)

def send_current_layer_for_controlnet(prompt, control_type="canny"):
    """
    Send current layer for ControlNet with validation.

    Args:
        prompt (str): Prompt.
        control_type (str): Control type.

    Raises:
        ValueError: If parameters are invalid.
    """
    if not prompt or not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt is required for ControlNet")
    if len(prompt) > 1000:
        raise ValueError("Prompt too long (>1000 characters)")

    valid_control_types = ["canny", "depth", "pose", "normal"]
    if control_type not in valid_control_types:
        raise ValueError(f"Invalid control type: {control_type}. Must be one of {valid_control_types}")

    # Check ComfyUI availability
    if not check_comfyui_available():
        from gimp_plugin.ui_panel import show_error
        show_error("ComfyUI backend is not available. Please start ComfyUI and try again.")
        return

    params = build_params("controlnet", "controlnet_basic", prompt=prompt, controlnet=[{"type": control_type}])
    _execute_workflow("controlnet", "controlnet_basic", params, export_image=True)

def send_current_layer_for_outpaint(prompt, negative_prompt=None):
    """
    Send current layer for outpainting with validation.

    Args:
        prompt (str): Prompt.
        negative_prompt (str, optional): Negative prompt.

    Raises:
        ValueError: If parameters are invalid.
    """
    if not prompt or not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt is required for outpainting")
    if len(prompt) > 1000:
        raise ValueError("Prompt too long (>1000 characters)")

    if negative_prompt and (not isinstance(negative_prompt, str) or len(negative_prompt) > 1000):
        raise ValueError("Negative prompt must be a string <= 1000 characters")

    # Check ComfyUI availability
    if not check_comfyui_available():
        from gimp_plugin.ui_panel import show_error
        show_error("ComfyUI backend is not available. Please start ComfyUI and try again.")
        return

    params = build_params("outpaint", "outpaint_basic", prompt=prompt, negative_prompt=negative_prompt)
    _execute_workflow("outpaint", "outpaint_basic", params, export_image=True, generate_mask=True)