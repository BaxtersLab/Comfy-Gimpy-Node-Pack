"""
Workflow loader for ComfyUI extension.
"""

import json
import logging
from pathlib import Path
from shared.config import load_config

logger = logging.getLogger(__name__)

def load_workflow_template(name: str):
    """
    Load workflow template.

    Args:
        name (str): Workflow name.

    Returns:
        dict: Workflow template.
    """
    try:
        config = load_config()
        workflow_path = config.workflows_dir / f"{name}.json"
        if workflow_path.exists():
            with open(workflow_path, 'r') as f:
                data = json.load(f)
            logger.info(f"Loaded workflow template: {name}")
            return data
        else:
            logger.warning(f"Workflow template not found: {name}")
            # Placeholder template
            return {"workflow": "placeholder"}
    except Exception as e:
        logger.error(f"Failed to load workflow template {name}: {e}")
        raise

def list_available_workflows():
    """
    List available workflows.

    Returns:
        list: List of workflow dictionaries.
    """
    try:
        config = load_config()
        workflows = []
        if config.workflows_dir.exists():
            for file in config.workflows_dir.glob("*.json"):
                workflows.append({
                    "name": file.stem,
                    "mode": "inpaint",  # Placeholder
                    "description": f"Workflow {file.stem}"
                })
        logger.info(f"Listed {len(workflows)} workflows")
        return workflows
    except Exception as e:
        logger.error(f"Failed to list workflows: {e}")
        raise