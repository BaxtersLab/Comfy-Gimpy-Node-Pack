"""
Main plugin logic for GIMP integration.
"""

import base64
import logging
from pathlib import Path
from gimp_comfy_bridge.shared.history import HistoryManager
from gimp_comfy_bridge.shared.protocol import encode_params, decode_base64_image
from gimp_plugin.api_client import run_workflow
from gimp_plugin.utils import export_current_layer, export_selection_mask, insert_image_as_new_layer, generate_outpaint_mask
from gimp_plugin.ui_panel import update_status, show_error

# Import template system
from gimp_comfy_bridge.templates import TemplateRegistry, TemplateLoader

# Import style system
from gimp_comfy_bridge.styles import StyleRegistry, StyleLoader

# Import async task engine
from gimp_comfy_bridge.async_engine import (
    initialize as init_task_engine,
    submit_task,
    get_task_status,
    cancel_task,
    shutdown as shutdown_task_engine
)
from gimp_comfy_bridge.async_engine.task import TaskPriority

# Import fusion engine
from gimp_comfy_bridge.fusion import (
    initialize_fusion_engine,
    fuse
)
from gimp_comfy_bridge.fusion.brandkits import BrandKitManager

# Import workflow auto-generation
from gimp_comfy_bridge.workflow_auto import WorkflowBuilder
from gimp_comfy_bridge.workflow_auto.rules import RuleEngine

# Import execution system
from gimp_comfy_bridge.execution import (
    initialize_execution_engine,
    execute_workflow,
    execute_fusion_result,
    process_execution_result,
    get_execution_monitor,
    initialize_monitoring
)

# Import optimization system (Phase 10)
from gimp_comfy_bridge.optimization import (
    initialize_phase10_system,
    shutdown_phase10_system,
    get_system_status,
    get_optimization_report,
    optimize_workflow_execution,
    get_workflow_optimization_suggestions,
    add_execution_node,
    get_performance_metrics
)

logger = logging.getLogger(__name__)
history = HistoryManager()

# Initialize template system
_template_registry = None
_template_loader = None

# Initialize style system
_style_registry = None
_style_loader = None

# Initialize workflow auto-generation
_workflow_builder = None
_rule_engine = None

# Initialize execution system
_execution_engine = None
_execution_monitor = None

# Initialize optimization system (Phase 10)
_optimization_system = None

# Initialize fusion engine
_fusion_engine = None
_brand_kit_manager = None

# Initialize fusion system
_fusion_engine = None
_brand_kit_manager = None

# Initialize workflow auto-generation
_workflow_builder = None
_rule_engine = None

# Task engine initialization flag
_task_engine_initialized = False

def _ensure_task_engine():
    """Ensure the task engine is initialized."""
    global _task_engine_initialized
    if not _task_engine_initialized:
        # Initialize with default settings
        init_task_engine(
            queue_max_size=100,
            max_workers=4,
            task_timeout_seconds=300
        )
        _task_engine_initialized = True


def _ensure_fusion_engine():
    """Ensure the fusion engine is initialized."""
    global _fusion_engine, _brand_kit_manager
    if _fusion_engine is None:
        _fusion_engine = initialize_fusion_engine()
        _brand_kit_manager = BrandKitManager()
        logger.info("Fusion engine initialized in GIMP plugin")


def _ensure_execution_engine():
    """Ensure the execution engine is initialized."""
    global _execution_engine, _execution_monitor
    if _execution_engine is None:
        _execution_engine = initialize_execution_engine()
        _execution_monitor = initialize_monitoring()
        logger.info("Execution engine initialized in GIMP plugin")


def _ensure_optimization_system():
    """Ensure the optimization system is initialized."""
    global _optimization_system
    if _optimization_system is None:
        # Note: This needs to be called in an async context
        # For now, we'll initialize synchronously where possible
        logger.info("Optimization system initialization requested in GIMP plugin")
        # The actual async initialization should be handled by calling code


def send_current_layer_for_upscale(scale_factor=2.0, method="4x-UltraSharp"):
    """
    Send current layer for upscaling using the async task engine.

    Args:
        scale_factor (float): Scale factor for upscaling
        method (str): Upscaling method

    Returns:
        str: Task ID if successful, None otherwise
    """
    try:
        logger.info(f"Starting upscale operation: scale={scale_factor}, method={method}")

        # Ensure task engine is initialized
        _ensure_task_engine()

        # Export current layer
        image_data = export_current_layer_to_base64()
        if not image_data:
            show_error("Failed to export current layer")
            return None

        # Submit task
        task_id = submit_task(
            operation="upscale",
            parameters={
                "input_image": image_data,
                "scale_factor": scale_factor,
                "method": method
            },
            priority=TaskPriority.NORMAL
        )

        update_status(f"Upscale task submitted: {task_id}")
        logger.info(f"Upscale task submitted: {task_id}")
        return task_id

    except Exception as e:
        logger.error(f"Upscale operation failed: {e}")
        show_error(f"Upscale failed: {e}")
        return None


def send_current_layer_for_inpaint(prompt="", negative_prompt="", inpaint_mode="original"):
    """
    Send current layer for inpainting using the async task engine.

    Args:
        prompt (str): Inpainting prompt
        negative_prompt (str): Negative prompt
        inpaint_mode (str): Inpainting mode

    Returns:
        str: Task ID if successful, None otherwise
    """
    try:
        logger.info(f"Starting inpaint operation: prompt='{prompt[:50]}...'")

        # Ensure task engine is initialized
        _ensure_task_engine()

        # Export current layer and selection mask
        image_data = export_current_layer_to_base64()
        mask_data = export_selection_mask_to_base64()

        if not image_data:
            show_error("Failed to export current layer")
            return None

        # Submit task
        task_id = submit_task(
            operation="inpaint",
            parameters={
                "input_image": image_data,
                "mask_image": mask_data,
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "inpaint_mode": inpaint_mode
            },
            priority=TaskPriority.NORMAL
        )

        update_status(f"Inpaint task submitted: {task_id}")
        logger.info(f"Inpaint task submitted: {task_id}")
        return task_id

    except Exception as e:
        logger.error(f"Inpaint operation failed: {e}")
        show_error(f"Inpaint failed: {e}")
        return None


def generate_from_text(prompt="", negative_prompt="", width=1024, height=1024):
    """
    Generate image from text using the async task engine.

    Args:
        prompt (str): Text prompt
        negative_prompt (str): Negative prompt
        width (int): Image width
        height (int): Image height

    Returns:
        str: Task ID if successful, None otherwise
    """
    try:
        logger.info(f"Starting text-to-image generation: prompt='{prompt[:50]}...', size={width}x{height}")

        # Ensure task engine is initialized
        _ensure_task_engine()

        # Submit task
        task_id = submit_task(
            operation="generate",
            parameters={
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height
            },
            priority=TaskPriority.NORMAL
        )

        update_status(f"Generation task submitted: {task_id}")
        logger.info(f"Generation task submitted: {task_id}")
        return task_id

    except Exception as e:
        logger.error(f"Generation operation failed: {e}")
        show_error(f"Generation failed: {e}")
        return None
        )

        update_status(f"Generation task submitted: {task_id}")
        return True

    except Exception as e:
        logger.error(f"Text-to-image generation failed: {e}")
        show_error(f"Generation failed: {e}")
        return False


def send_current_layer_for_img2img(prompt="", negative_prompt="", strength=0.8):
    """
    Send current layer for img2img using the async task engine.

    Args:
        prompt (str): Transformation prompt
        negative_prompt (str): Negative prompt
        strength (float): Transformation strength

    Returns:
        str: Task ID if successful, None otherwise
    """
    try:
        logger.info(f"Starting img2img operation: strength={strength}")

        # Ensure task engine is initialized
        _ensure_task_engine()

        # Export current layer
        image_data = export_current_layer_to_base64()
        if not image_data:
            show_error("Failed to export current layer")
            return None

        # Submit task
        task_id = submit_task(
            operation="img2img",
            parameters={
                "input_image": image_data,
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "strength": strength
            },
            priority=TaskPriority.NORMAL
        )

        update_status(f"Img2Img task submitted: {task_id}")
        logger.info(f"Img2Img task submitted: {task_id}")
        return task_id

    except Exception as e:
        logger.error(f"Img2Img operation failed: {e}")
        show_error(f"Img2Img failed: {e}")
        return None


def send_current_layer_for_controlnet(prompt="", negative_prompt="", controlnet_model="control_v11p_sd15_canny"):
    """
    Send current layer for ControlNet processing using the async task engine.

    Args:
        prompt (str): Generation prompt
        negative_prompt (str): Negative prompt
        controlnet_model (str): ControlNet model to use

    Returns:
        str: Task ID if successful, None otherwise
    """
    try:
        logger.info(f"Starting ControlNet operation: model={controlnet_model}")

        # Ensure task engine is initialized
        _ensure_task_engine()

        # Export current layer and control image
        image_data = export_current_layer_to_base64()
        control_data = export_current_layer_to_base64()  # Could be different layer

        if not image_data:
            show_error("Failed to export current layer")
            return None

        # Submit task
        task_id = submit_task(
            operation="controlnet",
            parameters={
                "input_image": image_data,
                "control_image": control_data,
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "controlnet_model": controlnet_model
            },
            priority=TaskPriority.NORMAL
        )

        update_status(f"ControlNet task submitted: {task_id}")
        logger.info(f"ControlNet task submitted: {task_id}")
        return task_id

    except Exception as e:
        logger.error(f"ControlNet operation failed: {e}")
        show_error(f"ControlNet failed: {e}")
        return None


def export_current_layer_to_base64():
    """
    Export current layer to base64 string.

    Returns:
        str: Base64 encoded image data, or None if failed
    """
    try:
        # Use existing export function
        temp_path = export_current_layer(Path("./temp"))
        if temp_path and temp_path.exists():
            with open(temp_path, 'rb') as f:
                image_data = f.read()
            return base64.b64encode(image_data).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to export layer to base64: {e}")
    return None


def export_selection_mask_to_base64():
    """
    Export selection mask to base64 string.

    Returns:
        str: Base64 encoded mask data, or None if failed
    """
    try:
        # Use existing export function
        temp_path = export_selection_mask(Path("./temp"))
        if temp_path and temp_path.exists():
            with open(temp_path, 'rb') as f:
                mask_data = f.read()
            return base64.b64encode(mask_data).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to export mask to base64: {e}")
    return None

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


def _initialize_template_system():
    """
    Initialize the template system if not already done.
    """
    global _template_registry, _template_loader

    if _template_registry is None:
        from gimp_comfy_bridge.shared.config import load_config
        config = load_config()
        _template_registry = TemplateRegistry(config.templates_dir)
        _template_loader = TemplateLoader(_template_registry)
        logger.info("Template system initialized")


def list_template_categories():
    """
    Get list of available template categories.

    Returns:
        List of category dictionaries with name, display_name, description, and count
    """
    try:
        _initialize_template_system()
        categories = _template_registry.list_categories()
        return [
            {
                'name': cat.name,
                'display_name': cat.display_name,
                'description': cat.description,
                'template_count': cat.template_count
            }
            for cat in categories
        ]
    except Exception as e:
        logger.error(f"Failed to list template categories: {e}")
        return []


def list_templates_in_category(category):
    """
    Get list of templates in a specific category.

    Args:
        category (str): Category name

    Returns:
        List of template dictionaries with name, description, and metadata
    """
    try:
        _initialize_template_system()
        templates = _template_registry.list_templates(category)
        return [
            {
                'name': template.name,
                'category': template.category,
                'description': template.metadata.description if template.metadata else '',
                'tags': template.metadata.tags if template.metadata else [],
                'has_preview': (template.path / "preview.png").exists()
            }
            for template in templates
        ]
    except Exception as e:
        logger.error(f"Failed to list templates in category {category}: {e}")
        return []


def load_template_into_gimp(category, name):
    """
    Load a template into GIMP.

    This is currently a stub implementation. Real XCF loading will be
    implemented when GIMP integration is complete.

    Args:
        category (str): Template category
        name (str): Template name

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        _initialize_template_system()

        # Load template data
        template_data = _template_loader.load_template(category, name)
        if not template_data:
            show_error(f"Failed to load template: {category}/{name}")
            return False

        # For now, just insert a placeholder message
        # Real implementation will load the XCF file
        placeholder_text = f"Template Loaded: {template_data['metadata'].name}\n\n"
        placeholder_text += f"Category: {template_data['metadata'].category}\n"
        placeholder_text += f"Description: {template_data['metadata'].description}\n"
        placeholder_text += f"Required Workflow: {template_data['metadata'].required_workflow}\n"
        placeholder_text += f"Recommended Styles: {', '.join(template_data['metadata'].recommended_styles)}\n"
        placeholder_text += f"Tags: {', '.join(template_data['metadata'].tags)}\n\n"
        placeholder_text += "Note: Full XCF loading will be implemented in a future update."

        # Create a text layer with the placeholder (stub implementation)
        logger.info(f"Template {category}/{name} loaded (stub implementation)")
        update_status(f"Loaded template: {template_data['metadata'].name}")

        return True

    except Exception as e:
        logger.error(f"Failed to load template {category}/{name} into GIMP: {e}")
        show_error(f"Failed to load template: {e}")
        return False


def _initialize_style_system():
    """
    Initialize the style system if not already done.
    """
    global _style_registry, _style_loader

    if _style_registry is None:
        from gimp_comfy_bridge.shared.config import load_config
        config = load_config()
        _style_registry = StyleRegistry(config.styles_dir)
        _style_loader = StyleLoader(_style_registry)
        logger.info("Style system initialized")


def _initialize_workflow_auto_system():
    """
    Initialize the workflow auto-generation system if not already done.
    """
    global _workflow_builder, _rule_engine

    if _workflow_builder is None:
        from gimp_comfy_bridge.shared.config import load_config
        config = load_config()
        _workflow_builder = WorkflowBuilder(config)
        _rule_engine = RuleEngine(config)
        logger.info("Workflow auto-generation system initialized")


def list_style_categories():
    """
    Get list of available style categories.

    Returns:
        List of category dictionaries with name, display_name, description, and count
    """
    try:
        _initialize_style_system()
        categories = _style_registry.list_categories()
        return [
            {
                'name': cat.name,
                'display_name': cat.display_name,
                'description': cat.description,
                'style_count': cat.style_count
            }
            for cat in categories
        ]
    except Exception as e:
        logger.error(f"Failed to list style categories: {e}")
        return []


def list_styles_in_category(category):
    """
    Get list of styles in a specific category.

    Args:
        category (str): Category name

    Returns:
        List of style dictionaries with name, description, and metadata
    """
    try:
        _initialize_style_system()
        styles = _style_registry.list_styles(category)
        return [
            {
                'name': style.name,
                'category': style.category,
                'description': style.metadata.description if style.metadata else '',
                'tags': style.metadata.tags if style.metadata else [],
                'default_weight': style.metadata.default_weight if style.metadata else 1.0,
                'has_preview': style.has_preview
            }
            for style in styles
        ]
    except Exception as e:
        logger.error(f"Failed to list styles in category {category}: {e}")
        return []


def apply_style_to_workflow(category, name, weight=None):
    """
    Apply a style to the current workflow.

    Args:
        category (str): Style category
        name (str): Style name
        weight (float, optional): Style weight override

    Returns:
        dict: Style information for workflow integration or None if failed
    """
    try:
        _initialize_style_system()

        # Load style data
        style_data = _style_loader.load_style(category, name)
        if not style_data:
            show_error(f"Failed to load style: {category}/{name}")
            return None

        # Use provided weight or default
        style_weight = weight if weight is not None else style_data['metadata'].default_weight

        return {
            'model_path': str(style_data['model_path']),
            'weight': style_weight,
            'metadata': {
                'name': style_data['metadata'].name,
                'category': style_data['metadata'].category,
                'description': style_data['metadata'].description,
                'tags': style_data['metadata'].tags
            }
        }

    except Exception as e:
        logger.error(f"Failed to apply style {category}/{name} to workflow: {e}")
        show_error(f"Failed to apply style: {e}")
        return None


def fuse_template_and_style(template_id: str,
                           style_id: str,
                           brand_kit_id: Optional[str] = None,
                           variant_count: int = 1,
                           lora_weights: Optional[Dict[str, float]] = None,
                           style_mix_ratios: Optional[Dict[str, float]] = None,
                           randomness_seed: Optional[int] = None):
    """
    Fuse a template with a style to generate variants.

    Args:
        template_id: ID of the template to use
        style_id: ID of the style to use
        brand_kit_id: Optional brand kit ID
        variant_count: Number of variants to generate
        lora_weights: Optional LoRA weights for blending
        style_mix_ratios: Optional style mixing ratios
        randomness_seed: Optional seed for reproducible results

    Returns:
        FusionResult with generated variants
    """
    try:
        _ensure_fusion_engine()
        _initialize_template_system()
        _initialize_style_system()

        # Load template and style
        template = _template_loader.load_template(template_id)
        style = _style_loader.load_style_by_id(style_id)

        if not template:
            show_error(f"Template not found: {template_id}")
            return None

        if not style:
            show_error(f"Style not found: {style_id}")
            return None

        # Create fusion options
        from gimp_comfy_bridge.fusion.engine import FusionOptions
        options = FusionOptions(
            lora_weights=lora_weights,
            style_mix_ratios=style_mix_ratios,
            brand_kit_id=brand_kit_id,
            variant_count=variant_count,
            randomness_seed=randomness_seed,
            generate_previews=True
        )

        # Perform fusion
        result = fuse(template, style, options)

        update_status(f"Fusion completed: {len(result.variants)} variants generated")
        return result

    except Exception as e:
        logger.error(f"Failed to fuse template and style: {e}")
        show_error(f"Fusion failed: {e}")
        return None


def get_available_brand_kits():
    """
    Get list of available brand kits.

    Returns:
        List of brand kit information
    """
    try:
        _ensure_fusion_engine()
        return _brand_kit_manager.list_brand_kits()
    except Exception as e:
        logger.error(f"Failed to get brand kits: {e}")
        return []


def create_brand_kit_template(kit_id: str, name: str, description: str = ""):
    """
    Create a new brand kit template.

    Args:
        kit_id: Unique identifier for the kit
        name: Display name
        description: Optional description

    Returns:
        Created BrandKit instance
    """
    try:
        _ensure_fusion_engine()
        kit = _brand_kit_manager.create_brand_kit_template(kit_id, name, description)
        _brand_kit_manager.save_brand_kit(kit)
        update_status(f"Brand kit template created: {name}")
        return kit
    except Exception as e:
        logger.error(f"Failed to create brand kit template: {e}")
        show_error(f"Failed to create brand kit: {e}")
        return None


# Workflow Auto-Generation Functions

def _ensure_workflow_auto_system():
    """
    Ensure workflow auto-generation system is initialized.
    """
    if _workflow_builder is None:
        _initialize_workflow_auto_system()


def build_workflow_from_template(template_id: str, style_id: str = None, options: dict = None):
    """
    Build a ComfyUI workflow from template and optional style.

    Args:
        template_id: Template identifier
        style_id: Optional style identifier
        options: Build options

    Returns:
        WorkflowBuildResult
    """
    try:
        _ensure_workflow_auto_system()

        # Get template
        template = None
        if _template_registry:
            template = _template_registry.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        # Get style if specified
        style = None
        if style_id and _style_registry:
            style = _style_registry.get_style(style_id)

        # Build workflow
        from gimp_comfy_bridge.workflow_auto import WorkflowBuildOptions
        build_options = WorkflowBuildOptions(**(options or {}))

        result = _workflow_builder.build_workflow(template, style, build_options)

        if result.success:
            update_status(f"Workflow built successfully: {len(result.workflow.nodes)} nodes")
        else:
            show_error(f"Workflow build failed: {', '.join(result.errors)}")

        return result

    except Exception as e:
        logger.error(f"Failed to build workflow: {e}")
        show_error(f"Failed to build workflow: {e}")
        return None


def get_available_workflow_templates():
    """
    Get list of available workflow templates.

    Returns:
        List of template information
    """
    try:
        _ensure_workflow_auto_system()
        return _workflow_builder.get_available_templates()
    except Exception as e:
        logger.error(f"Failed to get workflow templates: {e}")
        return []


def get_workflow_template_info(template_id: str):
    """
    Get detailed information about a workflow template.

    Args:
        template_id: Template identifier

    Returns:
        Template information dict
    """
    try:
        _ensure_workflow_auto_system()
        return _workflow_builder.get_template_info(template_id)
    except Exception as e:
        logger.error(f"Failed to get template info: {e}")
        return None


def validate_workflow_template(template_id: str):
    """
    Validate a workflow template.

    Args:
        template_id: Template identifier

    Returns:
        ValidationResult
    """
    try:
        _ensure_workflow_auto_system()

        # Get template
        template = None
        if _template_registry:
            template = _template_registry.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        return _workflow_builder.validate_template(template)

    except Exception as e:
        logger.error(f"Failed to validate template: {e}")
        return None


def get_workflow_build_rules():
    """
    Get available workflow build rules.

    Returns:
        List of rule information
    """
    try:
        _ensure_workflow_auto_system()
        rules = _rule_engine.rules.list_rules()
        return [
            {
                "id": rule.id,
                "name": rule.name,
                "description": rule.description,
                "priority": rule.priority,
                "enabled": rule.enabled
            }
            for rule in rules
        ]
    except Exception as e:
        logger.error(f"Failed to get workflow rules: {e}")
        return []


def apply_workflow_rule(template_id: str, rule_id: str, style_id: str = None):
    """
    Apply a specific rule to build a workflow.

    Args:
        template_id: Template identifier
        rule_id: Rule identifier
        style_id: Optional style identifier

    Returns:
        Workflow build result
    """
    try:
        _ensure_workflow_auto_system()

        # Get template
        template = None
        if _template_registry:
            template = _template_registry.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        # Get style if specified
        style = None
        if style_id and _style_registry:
            style = _style_registry.get_style(style_id)

        # Create rule context
        context = _rule_engine.create_context(template, style)

        # Evaluate specific rule
        rule = _rule_engine.rules.get_rule(rule_id)
        if not rule:
            raise ValueError(f"Rule not found: {rule_id}")

        result = _rule_engine._evaluate_rule(rule, context)

        if result.matched:
            update_status(f"Rule applied successfully: {rule.name}")
            return {
                "success": True,
                "rule_id": rule_id,
                "actions": result.actions,
                "confidence": result.confidence
            }
        else:
            return {
                "success": False,
                "rule_id": rule_id,
                "message": "Rule conditions not met"
            }

    except Exception as e:
        logger.error(f"Failed to apply workflow rule: {e}")
        show_error(f"Failed to apply rule: {e}")
        return {"success": False, "error": str(e)}


# Phase 9 - Real ComfyUI Integration Functions

def execute_comfyui_workflow(workflow_data, options=None):
    """
    Execute a ComfyUI workflow directly.

    Args:
        workflow_data: Workflow data (dict or WorkflowData object)
        options: Execution options

    Returns:
        Execution job result
    """
    try:
        _ensure_execution_engine()

        # Convert dict to WorkflowData if needed
        if isinstance(workflow_data, dict):
            from shared.types import WorkflowData
            workflow_data = WorkflowData(**workflow_data)

        job = execute_workflow(workflow_data, options)
        update_status(f"Workflow execution started: {job.job_id}")
        return {
            "success": True,
            "job_id": job.job_id,
            "status": job.status.value
        }

    except Exception as e:
        logger.error(f"Failed to execute workflow: {e}")
        show_error(f"Workflow execution failed: {e}")
        return {"success": False, "error": str(e)}


def execute_fusion_variants(fusion_result, template_id, style_id, options=None):
    """
    Execute all variants from a fusion result.

    Args:
        fusion_result: FusionResult object
        template_id: Template identifier
        style_id: Style identifier
        options: Execution options

    Returns:
        List of execution jobs
    """
    try:
        _ensure_execution_engine()

        jobs = execute_fusion_result(fusion_result, template_id, style_id, options)
        update_status(f"Started execution of {len(jobs)} fusion variants")
        return {
            "success": True,
            "job_count": len(jobs),
            "job_ids": [job.job_id for job in jobs]
        }

    except Exception as e:
        logger.error(f"Failed to execute fusion variants: {e}")
        show_error(f"Fusion execution failed: {e}")
        return {"success": False, "error": str(e)}


def get_execution_status(job_id):
    """
    Get the status of an execution job.

    Args:
        job_id: Job identifier

    Returns:
        Job status information
    """
    try:
        _ensure_execution_engine()

        job = _execution_engine.active_jobs.get(job_id)
        if not job:
            return {"success": False, "error": "Job not found"}

        return {
            "success": True,
            "job_id": job.job_id,
            "status": job.status.value,
            "progress": job.progress,
            "start_time": job.start_time,
            "end_time": job.end_time,
            "execution_time": (job.end_time - job.start_time) if job.end_time and job.start_time else None,
            "error_message": job.error_message
        }

    except Exception as e:
        logger.error(f"Failed to get execution status: {e}")
        return {"success": False, "error": str(e)}


def cancel_execution_job(job_id):
    """
    Cancel an execution job.

    Args:
        job_id: Job identifier

    Returns:
        Cancellation result
    """
    try:
        _ensure_execution_engine()

        success = _execution_engine.cancel_job(job_id)
        if success:
            update_status(f"Cancelled execution job: {job_id}")
            return {"success": True, "job_id": job_id}
        else:
            return {"success": False, "error": "Failed to cancel job"}

    except Exception as e:
        logger.error(f"Failed to cancel execution job: {e}")
        return {"success": False, "error": str(e)}


def get_execution_system_status():
    """
    Get the status of the execution system.

    Returns:
        System status information
    """
    try:
        _ensure_execution_engine()

        status = _execution_engine.get_system_status()
        return {
            "success": True,
            "system_status": status
        }

    except Exception as e:
        logger.error(f"Failed to get execution system status: {e}")
        return {"success": False, "error": str(e)}


def get_execution_performance_report():
    """
    Get execution performance report.

    Returns:
        Performance metrics and analytics
    """
    try:
        _ensure_execution_engine()

        report = _execution_monitor.get_performance_report()
        return {
            "success": True,
            "performance_report": report
        }

    except Exception as e:
        logger.error(f"Failed to get performance report: {e}")
        return {"success": False, "error": str(e)}


def process_execution_output(job_id, options=None):
    """
    Process the output of a completed execution job.

    Args:
        job_id: Job identifier
        options: Processing options

    Returns:
        Processed result
    """
    try:
        _ensure_execution_engine()

        job = _execution_engine.active_jobs.get(job_id)
        if not job or not job.result:
            return {"success": False, "error": "Job not found or has no result"}

        processed_result = process_execution_result(job, options)
        update_status(f"Processed execution output for job: {job_id}")

        return {
            "success": True,
            "job_id": job_id,
            "processed_result": {
                "success": processed_result.success,
                "output_count": len(processed_result.outputs),
                "processing_time": processed_result.processing_time,
                "file_paths": [str(p) for p in processed_result.file_paths],
                "error_message": processed_result.error_message
            }
        }

    except Exception as e:
        logger.error(f"Failed to process execution output: {e}")
        return {"success": False, "error": str(e)}


# Phase 10 - Advanced Workflow Optimization Functions

def initialize_optimization_system():
    """
    Initialize the Phase 10 optimization system.

    Returns:
        Initialization result
    """
    try:
        # Note: Full async initialization should be handled externally
        # This is a synchronous placeholder
        update_status("Optimization system initialization requested")
        return {
            "success": True,
            "message": "Optimization system initialization requested. Use async initialization for full functionality."
        }
    except Exception as e:
        logger.error(f"Failed to initialize optimization system: {e}")
        return {"success": False, "error": str(e)}


def get_optimization_system_status():
    """
    Get the status of the optimization system.

    Returns:
        System status information
    """
    try:
        _ensure_execution_engine()

        # Get basic execution system status
        exec_status = get_execution_system_status()

        return {
            "success": True,
            "phase10_available": True,
            "execution_system": exec_status.get("system_status", {}),
            "optimization_features": [
                "workflow_optimization",
                "distributed_execution",
                "performance_monitoring",
                "intelligent_caching"
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get optimization system status: {e}")
        return {"success": False, "error": str(e)}


def get_workflow_optimization_advice(workflow_hash=None):
    """
    Get optimization advice for workflows.

    Args:
        workflow_hash: Specific workflow hash to analyze

    Returns:
        Optimization advice and recommendations
    """
    try:
        _ensure_execution_engine()

        advice = {
            "general_recommendations": [
                "Enable caching for frequently used workflows",
                "Monitor system resources during execution",
                "Consider distributed execution for high-throughput needs",
                "Use batch processing for similar workflows"
            ],
            "performance_tips": [
                "Lower concurrency reduces memory usage",
                "Higher batch sizes improve GPU utilization",
                "Workflow caching reduces execution time",
                "Distributed nodes improve fault tolerance"
            ]
        }

        if workflow_hash:
            # Add specific workflow advice
            advice["workflow_specific"] = {
                "hash": workflow_hash,
                "recommendations": [
                    "Consider caching this workflow",
                    "Monitor execution patterns",
                    "Optimize based on usage frequency"
                ]
            }

        update_status("Optimization advice generated")
        return {
            "success": True,
            "advice": advice
        }

    except Exception as e:
        logger.error(f"Failed to get optimization advice: {e}")
        return {"success": False, "error": str(e)}


def add_distributed_execution_node(host, port, priority=1, max_concurrent=4):
    """
    Add a distributed execution node.

    Args:
        host: Node host address
        port: Node port
        priority: Node priority (higher = preferred)
        max_concurrent: Maximum concurrent jobs

    Returns:
        Node addition result
    """
    try:
        add_execution_node(host, port, priority, max_concurrent)
        update_status(f"Added distributed execution node: {host}:{port}")
        return {
            "success": True,
            "node_id": f"{host}:{port}",
            "priority": priority,
            "max_concurrent": max_concurrent
        }
    except Exception as e:
        logger.error(f"Failed to add distributed execution node: {e}")
        return {"success": False, "error": str(e)}


def get_performance_optimization_report():
    """
    Get comprehensive performance optimization report.

    Returns:
        Performance and optimization metrics
    """
    try:
        _ensure_execution_engine()

        # Get execution performance report
        exec_report = get_execution_performance_report()

        # Get current performance metrics
        perf_metrics = get_performance_metrics()

        report = {
            "execution_performance": exec_report.get("performance_report", {}),
            "system_performance": perf_metrics,
            "optimization_opportunities": [
                "Consider workflow caching for repeated executions",
                "Monitor memory usage patterns",
                "Optimize batch sizes based on GPU memory",
                "Use distributed execution for scalability"
            ],
            "recommendations": [
                "Enable performance monitoring for detailed insights",
                "Configure appropriate concurrency limits",
                "Set up health checks for distributed nodes",
                "Implement caching strategies for common workflows"
            ]
        }

        update_status("Performance optimization report generated")
        return {
            "success": True,
            "report": report
        }

    except Exception as e:
        logger.error(f"Failed to generate performance report: {e}")
        return {"success": False, "error": str(e)}


def optimize_execution_parameters(workflow_data, target_performance="balanced"):
    """
    Optimize execution parameters for a workflow.

    Args:
        workflow_data: Workflow data to optimize for
        target_performance: "speed", "efficiency", "balanced"

    Returns:
        Optimized execution parameters
    """
    try:
        _ensure_execution_engine()

        # Base parameters
        params = {
            "concurrency": 2,
            "batch_size": 1,
            "enable_caching": True,
            "timeout": 300
        }

        # Adjust based on target performance
        if target_performance == "speed":
            params.update({
                "concurrency": 4,
                "batch_size": 2,
                "enable_caching": True
            })
        elif target_performance == "efficiency":
            params.update({
                "concurrency": 1,
                "batch_size": 1,
                "enable_caching": True
            })
        # balanced is default

        update_status(f"Optimized parameters for {target_performance} performance")
        return {
            "success": True,
            "target_performance": target_performance,
            "optimized_parameters": params,
            "explanation": f"Parameters optimized for {target_performance} execution"
        }

    except Exception as e:
        logger.error(f"Failed to optimize execution parameters: {e}")
        return {"success": False, "error": str(e)}