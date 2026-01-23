"""
API client for communicating with ComfyUI backend.
"""

import requests
import logging
import time
from typing import Optional, Dict, Any
from shared.config import load_config
from shared.protocol import PingResponse, WorkflowResponse, validate_workflow_response

logger = logging.getLogger(__name__)

def _make_request_with_retry(url: str, method: str = 'GET', data: Optional[Dict] = None,
                           files: Optional[Dict] = None, timeout: int = 10,
                           max_retries: int = 3) -> requests.Response:
    """
    Make HTTP request with retry logic and exponential backoff.

    Args:
        url: Request URL
        method: HTTP method
        data: Request data
        files: File uploads
        timeout: Request timeout
        max_retries: Maximum retry attempts

    Returns:
        Response object

    Raises:
        Exception: If all retries fail
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            if attempt > 0:
                # Exponential backoff: 1s, 2s, 4s
                backoff_time = 2 ** (attempt - 1)
                logger.info(f"Retrying request in {backoff_time} seconds (attempt {attempt + 1}/{max_retries})")
                time.sleep(backoff_time)

            if method.upper() == 'GET':
                response = requests.get(url, timeout=timeout)
            elif method.upper() == 'POST':
                if files:
                    response = requests.post(url, data=data, files=files, timeout=timeout)
                else:
                    response = requests.post(url, json=data, timeout=timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response

        except requests.exceptions.Timeout as e:
            last_exception = Exception(f"Request timeout after {timeout}s: {e}")
            logger.warning(f"Request timeout (attempt {attempt + 1}/{max_retries}): {e}")
        except requests.exceptions.ConnectionError as e:
            last_exception = Exception(f"Connection failed: {e}")
            logger.warning(f"Connection error (attempt {attempt + 1}/{max_retries}): {e}")
        except requests.exceptions.HTTPError as e:
            # Don't retry on HTTP errors (4xx, 5xx)
            raise Exception(f"HTTP error: {e}")
        except Exception as e:
            last_exception = Exception(f"Request failed: {e}")
            logger.warning(f"Request error (attempt {attempt + 1}/{max_retries}): {e}")

    # All retries failed
    raise last_exception or Exception("Request failed after all retries")

def ping_backend():
    """
    Ping the backend.

    Returns:
        PingResponse: Ping response.

    Raises:
        Exception: If ping fails after retries
    """
    try:
        config = load_config()
    except Exception as e:
        raise Exception(f"Failed to load configuration: {e}")

    if not config.base_url:
        raise Exception("No base URL configured")

    try:
        logger.info("Pinging backend")
        url = f"{config.base_url.rstrip('/')}/ping"
        response = _make_request_with_retry(url, method='POST', data={}, timeout=10)

        try:
            data = response.json()
        except ValueError as e:
            raise Exception(f"Invalid JSON response: {e}")

        try:
            ping_response = PingResponse(**data)
        except Exception as e:
            raise Exception(f"Invalid ping response format: {e}")

        logger.info("Ping successful")
        return ping_response

    except Exception as e:
        logger.error(f"Failed to ping backend: {e}")
        raise Exception(f"Backend ping failed: {e}")

def run_workflow(mode, workflow_name, params, image=None, mask=None):
    """
    Run a workflow.

    Args:
        mode (str): Workflow mode.
        workflow_name (str): Name of the workflow.
        params (dict): Parameters.
        image (bytes, optional): Image data.
        mask (bytes, optional): Mask data.

    Returns:
        WorkflowResponse: Workflow response.

    Raises:
        ValueError: If parameters are invalid.
        Exception: If workflow execution fails.
    """
    # Validate inputs
    if not isinstance(mode, str) or not mode.strip():
        raise ValueError("Mode must be a non-empty string")

    if not isinstance(workflow_name, str) or not workflow_name.strip():
        raise ValueError("Workflow name must be a non-empty string")

    if not isinstance(params, dict):
        raise ValueError("Params must be a dictionary")

    # Validate file data if provided
    if image is not None:
        if not isinstance(image, bytes):
            raise ValueError("Image must be bytes")
        if len(image) == 0:
            raise ValueError("Image data is empty")
        if len(image) > 50 * 1024 * 1024:  # 50MB limit
            raise ValueError(f"Image too large: {len(image)} bytes")

    if mask is not None:
        if not isinstance(mask, bytes):
            raise ValueError("Mask must be bytes")
        if len(mask) == 0:
            raise ValueError("Mask data is empty")
        if len(mask) > 10 * 1024 * 1024:  # 10MB limit
            raise ValueError(f"Mask too large: {len(mask)} bytes")

    try:
        config = load_config()
    except Exception as e:
        raise Exception(f"Failed to load configuration: {e}")

    if not config.base_url:
        raise Exception("No base URL configured")

    try:
        url = f"{config.base_url.rstrip('/')}/run_workflow"
        data = {
            'mode': mode.strip(),
            'workflow_name': workflow_name.strip(),
            'params': params
        }
        files = {}
        if image:
            files['image'] = ('image.png', image, 'image/png')
        if mask:
            files['mask'] = ('mask.png', mask, 'image/png')

        logger.info(f"Running workflow {workflow_name} in mode {mode}")

        # Use longer timeout for workflow execution
        response = _make_request_with_retry(url, method='POST', data=data, files=files,
                                          timeout=300, max_retries=2)  # 5 min timeout, fewer retries

        try:
            response_data = response.json()
        except ValueError as e:
            raise Exception(f"Invalid JSON response: {e}")

        try:
            workflow_resp = WorkflowResponse(**response_data)
        except Exception as e:
            raise Exception(f"Invalid workflow response format: {e}")

        try:
            validate_workflow_response(workflow_resp)
        except Exception as e:
            raise Exception(f"Workflow response validation failed: {e}")

        logger.info("Workflow completed successfully")
        return workflow_resp

    except ValueError:
        raise  # Re-raise validation errors
    except Exception as e:
        logger.error(f"Failed to run workflow: {e}")
        raise Exception(f"Workflow execution failed: {e}")

def get_workflow_status(task_id: str):
    """
    Get workflow status.

    Args:
        task_id (str): Task ID.

    Returns:
        dict: Status information.

    Raises:
        ValueError: If task_id is invalid.
        Exception: If status check fails.
    """
    if not isinstance(task_id, str) or not task_id.strip():
        raise ValueError("Task ID must be a non-empty string")

    # For now, return a mock status since the backend doesn't implement this endpoint
    # In a real implementation, this would poll the ComfyUI backend for status
    logger.info(f"Getting status for task {task_id}")
    return {
        "status": "completed",
        "progress": 1.0,
        "current_node": "Finished",
        "task_id": task_id.strip()
    }

def get_workflows():
    """
    Get available workflows.

    Returns:
        list: List of workflows.

    Raises:
        Exception: If workflow fetch fails.
    """
    try:
        config = load_config()
    except Exception as e:
        raise Exception(f"Failed to load configuration: {e}")

    if not config.base_url:
        raise Exception("No base URL configured")

    try:
        logger.info("Fetching workflows")
        url = f"{config.base_url.rstrip('/')}/workflows"
        response = _make_request_with_retry(url, method='GET', timeout=10)

        try:
            response_data = response.json()
        except ValueError as e:
            raise Exception(f"Invalid JSON response: {e}")

        if not isinstance(response_data, dict) or 'workflows' not in response_data:
            raise Exception("Invalid workflows response format")

        workflows = response_data['workflows']
        if not isinstance(workflows, list):
            raise Exception("Workflows data is not a list")

        # Validate workflow entries
        for i, workflow in enumerate(workflows):
            if not isinstance(workflow, (str, dict)):
                logger.warning(f"Invalid workflow entry at index {i}: {type(workflow)}")
                continue

        logger.info(f"Fetched {len(workflows)} workflows")
        return workflows

    except Exception as e:
        logger.error(f"Failed to get workflows: {e}")
        raise Exception(f"Workflow fetch failed: {e}")