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

def build_params(mode, workflow_name, prompt=None, negative_prompt=None, width=None, height=None, strength=None, upscale_factor=None, model=None, loras=None, controlnet=None):
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
    Internal workflow execution.

    Args:
        mode (str): Mode.
        workflow_name (str): Workflow name.
        params (dict): Parameters.
        export_image (bool): Whether to export image.
        export_mask (bool): Whether to export mask.
        generate_mask (bool): Whether to generate mask.
    """
    if not history.session_id:
        history.start_session()
    
    if history.current_step > 0:  # If undo was used
        history.truncate_forward_history()
    
    step_dir = history.next_step_dir()
    
    image_path = None
    if export_image:
        image_path = export_current_layer(step_dir)
    
    mask_path = None
    if export_mask:
        mask_path = export_selection_mask(step_dir)
    elif generate_mask:
        mask_path = generate_outpaint_mask(step_dir)
    
    # Save params
    params_json = encode_params(params)
    with open(step_dir / "params.json", 'w') as f:
        f.write(params_json)
    
    # Run workflow
    try:
        image_data = None
        if image_path:
            with open(image_path, 'rb') as f:
                image_data = f.read()
        
        mask_data = None
        if mask_path:
            with open(mask_path, 'rb') as f:
                mask_data = f.read()
        
        response = run_workflow(mode, workflow_name, params, image_data, mask_data)
        
        # Decode result
        result_image = decode_base64_image(response.result['image_base64'])
        output_path = step_dir / "output.png"
        with open(output_path, 'wb') as f:
            f.write(result_image)
        
        # Save step
        history.save_step(str(image_path) if image_path else None, str(mask_path) if mask_path else None, str(output_path), params)
        
        # Insert into GIMP
        insert_image_as_new_layer(output_path)
        
        update_status("Workflow completed successfully")
    
    except Exception as e:
        show_error(str(e))

def send_current_layer_for_inpaint(prompt, negative_prompt=None):
    """
    Send current layer for inpainting.

    Args:
        prompt (str): Prompt.
        negative_prompt (str, optional): Negative prompt.
    """
    if not prompt:
        show_error("Prompt is required for inpainting")
        return
    params = build_params("inpaint", "inpaint_basic", prompt=prompt, negative_prompt=negative_prompt)
    _execute_workflow("inpaint", "inpaint_basic", params, export_image=True, export_mask=True)

def send_current_layer_for_upscale(upscale_factor=2.0):
    """
    Send current layer for upscaling.

    Args:
        upscale_factor (float): Upscale factor.
    """
    if upscale_factor <= 1:
        show_error("Upscale factor must be > 1")
        return
    params = build_params("upscale", "upscale_basic", upscale_factor=upscale_factor)
    _execute_workflow("upscale", "upscale_basic", params, export_image=True)

def generate_from_text(prompt, negative_prompt=None, width=1024, height=1024):
    """
    Generate from text.

    Args:
        prompt (str): Prompt.
        negative_prompt (str, optional): Negative prompt.
        width (int): Width.
        height (int): Height.
    """
    if not prompt:
        show_error("Prompt is required for text generation")
        return
    if width <= 0 or height <= 0:
        show_error("Width and height must be positive")
        return
    params = build_params("txt2img", "txt2img_basic", prompt=prompt, negative_prompt=negative_prompt, width=width, height=height)
    _execute_workflow("txt2img", "txt2img_basic", params, export_image=False)

def send_current_layer_for_img2img(prompt, strength=0.6):
    """
    Send current layer for img2img.

    Args:
        prompt (str): Prompt.
        strength (float): Strength.
    """
    if not prompt:
        show_error("Prompt is required for img2img")
        return
    if not (0 < strength <= 1):
        show_error("Strength must be between 0 and 1")
        return
    params = build_params("img2img", "img2img_basic", prompt=prompt, strength=strength)
    _execute_workflow("img2img", "img2img_basic", params, export_image=True)

def send_current_layer_for_controlnet(prompt, control_type="canny"):
    """
    Send current layer for ControlNet.

    Args:
        prompt (str): Prompt.
        control_type (str): Control type.
    """
    if not prompt:
        show_error("Prompt is required for ControlNet")
        return
    params = build_params("controlnet", "controlnet_basic", prompt=prompt, controlnet=[{"type": control_type}])
    _execute_workflow("controlnet", "controlnet_basic", params, export_image=True)