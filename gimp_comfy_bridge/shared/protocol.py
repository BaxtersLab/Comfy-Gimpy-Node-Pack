"""
Protocol definitions for communication between GIMP and ComfyUI.
"""

import json
import base64
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PingResponse:
    """
    Response for ping endpoint.
    """
    status: str
    comfyui_version: str
    models_available: list

@dataclass
class WorkflowRequest:
    """
    Request for workflow execution.
    """
    mode: str
    workflow_name: str
    params: dict
    image: bytes = None
    mask: bytes = None

@dataclass
class WorkflowResponse:
    """
    Response for workflow execution.
    """
    status: str
    task_id: str
    result: dict

def encode_params(params: dict) -> str:
    """
    Encode parameters to JSON string.

    Args:
        params (dict): Parameters to encode.

    Returns:
        str: JSON string.
    """
    try:
        return json.dumps(params)
    except (TypeError, ValueError) as e:
        logger.error(f"Failed to encode params: {e}")
        raise

def decode_base64_image(base64_str: str) -> bytes:
    """
    Decode base64 image string to bytes.

    Args:
        base64_str (str): Base64 encoded image.

    Returns:
        bytes: Decoded image bytes.
    """
    try:
        return base64.b64decode(base64_str)
    except Exception as e:
        logger.error(f"Failed to decode base64 image: {e}")
        raise

def validate_workflow_request(request: WorkflowRequest):
    """
    Validate workflow request with comprehensive checks.

    Args:
        request (WorkflowRequest): Request to validate.

    Raises:
        ValueError: If invalid.
    """
    # Required fields validation
    if not request.mode or not isinstance(request.mode, str):
        raise ValueError("Mode is required and must be a string")
    if not request.workflow_name or not isinstance(request.workflow_name, str):
        raise ValueError("Workflow_name is required and must be a string")
    if not isinstance(request.params, dict):
        raise ValueError("Params must be a dict")

    # Mode-specific validation
    valid_modes = ["txt2img", "img2img", "inpaint", "outpaint", "upscale", "controlnet"]
    if request.mode not in valid_modes:
        raise ValueError(f"Invalid mode: {request.mode}. Must be one of {valid_modes}")

    # Parameter validation based on mode
    _validate_workflow_params(request.mode, request.params)

    # File validation
    if request.image is not None and not isinstance(request.image, bytes):
        raise ValueError("Image must be bytes or None")
    if request.mask is not None and not isinstance(request.mask, bytes):
        raise ValueError("Mask must be bytes or None")

    # Size limits (prevent memory exhaustion)
    if request.image and len(request.image) > 50 * 1024 * 1024:  # 50MB limit
        raise ValueError("Image file too large (>50MB)")
    if request.mask and len(request.mask) > 10 * 1024 * 1024:  # 10MB limit
        raise ValueError("Mask file too large (>10MB)")

def _validate_workflow_params(mode: str, params: dict):
    """
    Validate workflow parameters based on mode.

    Args:
        mode (str): Workflow mode.
        params (dict): Parameters to validate.

    Raises:
        ValueError: If invalid.
    """
    # Common parameter validations
    if "prompt" in params:
        if not isinstance(params["prompt"], str) or len(params["prompt"]) > 1000:
            raise ValueError("Prompt must be a string <= 1000 characters")

    if "negative_prompt" in params:
        if not isinstance(params["negative_prompt"], str) or len(params["negative_prompt"]) > 1000:
            raise ValueError("Negative prompt must be a string <= 1000 characters")

    if "width" in params:
        if not isinstance(params["width"], int) or not (64 <= params["width"] <= 2048):
            raise ValueError("Width must be an integer between 64 and 2048")

    if "height" in params:
        if not isinstance(params["height"], int) or not (64 <= params["height"] <= 2048):
            raise ValueError("Height must be an integer between 64 and 2048")

    if "strength" in params:
        if not isinstance(params["strength"], (int, float)) or not (0 <= params["strength"] <= 1):
            raise ValueError("Strength must be a number between 0 and 1")

    if "upscale_factor" in params:
        if not isinstance(params["upscale_factor"], (int, float)) or not (1 <= params["upscale_factor"] <= 4):
            raise ValueError("Upscale factor must be between 1 and 4")

    # Mode-specific validations
    if mode == "txt2img":
        if "prompt" not in params or not params["prompt"].strip():
            raise ValueError("Prompt is required for txt2img mode")

    elif mode in ["img2img", "inpaint", "outpaint", "upscale", "controlnet"]:
        # These modes require an image (validated at higher level)
        pass

    if mode == "controlnet":
        if "control_type" not in params:
            raise ValueError("Control type is required for controlnet mode")
        valid_control_types = ["canny", "depth", "pose", "normal"]
        if params["control_type"] not in valid_control_types:
            raise ValueError(f"Invalid control type: {params['control_type']}. Must be one of {valid_control_types}")

def validate_workflow_response(response: WorkflowResponse):
    """
    Validate workflow response with comprehensive checks.

    Args:
        response (WorkflowResponse): Response to validate.

    Raises:
        ValueError: If invalid.
    """
    # Status validation
    if not response.status or not isinstance(response.status, str):
        raise ValueError("Status is required and must be a string")
    if response.status not in ["completed", "failed", "cancelled"]:
        raise ValueError(f"Invalid status: {response.status}")

    # Task ID validation
    if not response.task_id or not isinstance(response.task_id, str):
        raise ValueError("Task ID is required and must be a string")
    if len(response.task_id) > 100:  # Reasonable limit
        raise ValueError("Task ID too long (>100 characters)")

    # Result validation
    if not isinstance(response.result, dict):
        raise ValueError("Result must be a dict")

    # Result content validation for completed responses
    if response.status == "completed":
        if "image_base64" not in response.result:
            raise ValueError("Completed response must include image_base64")
        if "mime_type" not in response.result:
            raise ValueError("Completed response must include mime_type")

        # Validate base64 image
        try:
            image_data = decode_base64_image(response.result["image_base64"])
            if len(image_data) > 100 * 1024 * 1024:  # 100MB limit
                raise ValueError("Decoded image too large (>100MB)")
        except Exception as e:
            raise ValueError(f"Invalid image_base64 in response: {e}")

        # Validate mime type
        valid_mime_types = ["image/png", "image/jpeg", "image/webp"]
        if response.result["mime_type"] not in valid_mime_types:
            raise ValueError(f"Invalid mime_type: {response.result['mime_type']}")

def validate_ping_response(response: PingResponse):
    """
    Validate ping response.

    Args:
        response (PingResponse): Response to validate.

    Raises:
        ValueError: If invalid.
    """
    if not response.status or response.status != "ok":
        raise ValueError("Ping response status must be 'ok'")
    if not response.comfyui_version or not isinstance(response.comfyui_version, str):
        raise ValueError("ComfyUI version is required and must be a string")
    if not isinstance(response.models_available, list):
        raise ValueError("Models available must be a list")
    # Validate each model name
    for model in response.models_available:
        if not isinstance(model, str) or len(model) > 200:
            raise ValueError("Model names must be strings <= 200 characters")