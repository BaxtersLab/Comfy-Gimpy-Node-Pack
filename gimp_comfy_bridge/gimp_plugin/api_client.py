"""
API client for communicating with ComfyUI backend.
"""

import requests
import logging
from shared.config import load_config
from shared.protocol import PingResponse, WorkflowResponse, validate_workflow_response

logger = logging.getLogger(__name__)

def ping_backend():
    """
    Ping the backend.

    Returns:
        PingResponse: Ping response.
    """
    config = load_config()
    try:
        logger.info("Pinging backend")
        response = requests.post(f"{config.base_url}ping", json={}, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.info("Ping successful")
        return PingResponse(**data)
    except requests.RequestException as e:
        logger.error(f"Failed to ping backend: {e}")
        raise Exception(f"Failed to ping backend: {e}")
    except ValueError as e:
        logger.error(f"Invalid ping response: {e}")
        raise Exception(f"Invalid response: {e}")

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
    """
    config = load_config()
    url = f"{config.base_url}run_workflow"
    data = {
        'mode': mode,
        'workflow_name': workflow_name,
        'params': params
    }
    files = {}
    if image:
        files['image'] = ('image.png', image, 'image/png')
    if mask:
        files['mask'] = ('mask.png', mask, 'image/png')
    
    try:
        logger.info(f"Running workflow {workflow_name} in mode {mode}")
        response = requests.post(url, data=data, files=files, timeout=300)  # 5 min timeout
        response.raise_for_status()
        data = response.json()
        workflow_resp = WorkflowResponse(**data)
        validate_workflow_response(workflow_resp)
        logger.info("Workflow completed")
        return workflow_resp
    except requests.RequestException as e:
        logger.error(f"Failed to run workflow: {e}")
        raise Exception(f"Failed to run workflow: {e}")
    except ValueError as e:
        logger.error(f"Invalid workflow response: {e}")
        raise Exception(f"Invalid response: {e}")

def get_workflows():
    """
    Get available workflows.

    Returns:
        list: List of workflows.
    """
    config = load_config()
    try:
        logger.info("Fetching workflows")
        response = requests.get(f"{config.base_url}workflows", timeout=10)
        response.raise_for_status()
        workflows = response.json()['workflows']
        logger.info(f"Fetched {len(workflows)} workflows")
        return workflows
    except requests.RequestException as e:
        logger.error(f"Failed to get workflows: {e}")
        raise Exception(f"Failed to get workflows: {e}")
    except ValueError as e:
        logger.error(f"Invalid workflows response: {e}")
        raise Exception(f"Invalid response: {e}")