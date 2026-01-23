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
    Validate workflow request.

    Args:
        request (WorkflowRequest): Request to validate.

    Raises:
        ValueError: If invalid.
    """
    if not request.mode or not request.workflow_name:
        raise ValueError("Mode and workflow_name are required")
    if not isinstance(request.params, dict):
        raise ValueError("Params must be a dict")

def validate_workflow_response(response: WorkflowResponse):
    """
    Validate workflow response.

    Args:
        response (WorkflowResponse): Response to validate.

    Raises:
        ValueError: If invalid.
    """
    if response.status not in ["completed", "failed"]:
        raise ValueError("Invalid status")
    if not response.task_id:
        raise ValueError("Task ID is required")
    if not isinstance(response.result, dict):
        raise ValueError("Result must be a dict")