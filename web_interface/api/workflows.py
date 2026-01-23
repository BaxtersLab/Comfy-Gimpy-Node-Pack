"""
Workflows API for web interface.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def get_workflows() -> List[Dict[str, Any]]:
    """
    Get available workflows.

    Returns:
        List of workflow dictionaries
    """
    try:
        # For now, return hardcoded workflows
        # In a full implementation, this would scan the workflows directory
        workflows = [
            {
                "name": "txt2img_basic",
                "description": "Basic text to image generation",
                "category": "generation",
                "inputs": ["prompt", "negative_prompt", "width", "height"],
                "outputs": ["image"]
            },
            {
                "name": "img2img_basic",
                "description": "Basic image to image transformation",
                "category": "transformation",
                "inputs": ["image", "prompt", "strength"],
                "outputs": ["image"]
            },
            {
                "name": "inpaint_basic",
                "description": "Basic inpainting with mask",
                "category": "editing",
                "inputs": ["image", "mask", "prompt"],
                "outputs": ["image"]
            },
            {
                "name": "upscale_basic",
                "description": "Basic image upscaling",
                "category": "enhancement",
                "inputs": ["image", "scale_factor"],
                "outputs": ["image"]
            }
        ]
        return workflows

    except Exception as e:
        logger.error(f"Failed to get workflows: {e}")
        return []


def get_workflow_details(name: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a workflow.

    Args:
        name (str): Workflow name

    Returns:
        Workflow details or None if not found
    """
    workflows = get_workflows()
    for workflow in workflows:
        if workflow["name"] == name:
            return workflow
    return None


# Workflow Auto-Generation API Functions

def get_workflow_templates() -> List[Dict[str, Any]]:
    """
    Get available workflow templates for auto-generation.

    Returns:
        List of template dictionaries
    """
    try:
        from gimp_plugin.plugin import get_available_workflow_templates
        return get_available_workflow_templates()
    except Exception as e:
        logger.error(f"Failed to get workflow templates: {e}")
        return []


def get_workflow_template_details(template_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a workflow template.

    Args:
        template_id: Template identifier

    Returns:
        Template details or None if not found
    """
    try:
        from gimp_plugin.plugin import get_workflow_template_info
        return get_workflow_template_info(template_id)
    except Exception as e:
        logger.error(f"Failed to get template details: {e}")
        return None


def build_workflow(template_id: str, style_id: str = None, options: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
    """
    Build a workflow from template and optional style.

    Args:
        template_id: Template identifier
        style_id: Optional style identifier
        options: Build options

    Returns:
        Build result dictionary
    """
    try:
        from gimp_plugin.plugin import build_workflow_from_template
        result = build_workflow_from_template(template_id, style_id, options or {})

        if result:
            return {
                "success": result.success,
                "workflow": result.workflow.dict() if result.workflow else None,
                "errors": result.errors,
                "warnings": result.warnings,
                "build_time": result.build_time,
                "node_count": result.node_count,
                "cache_hit": result.cache_hit
            }
        return None

    except Exception as e:
        logger.error(f"Failed to build workflow: {e}")
        return {"success": False, "error": str(e)}


def validate_template(template_id: str) -> Optional[Dict[str, Any]]:
    """
    Validate a workflow template.

    Args:
        template_id: Template identifier

    Returns:
        Validation result dictionary
    """
    try:
        from gimp_plugin.plugin import validate_workflow_template
        result = validate_workflow_template(template_id)

        if result:
            return {
                "valid": result.valid,
                "errors": result.errors,
                "warnings": result.warnings,
                "suggestions": result.suggestions
            }
        return None

    except Exception as e:
        logger.error(f"Failed to validate template: {e}")
        return {"valid": False, "error": str(e)}


def get_workflow_build_rules() -> List[Dict[str, Any]]:
    """
    Get available workflow build rules.

    Returns:
        List of rule dictionaries
    """
    try:
        from gimp_plugin.plugin import get_workflow_build_rules
        return get_workflow_build_rules()
    except Exception as e:
        logger.error(f"Failed to get workflow rules: {e}")
        return []


def apply_build_rule(template_id: str, rule_id: str, style_id: str = None) -> Optional[Dict[str, Any]]:
    """
    Apply a specific build rule to a template.

    Args:
        template_id: Template identifier
        rule_id: Rule identifier
        style_id: Optional style identifier

    Returns:
        Rule application result
    """
    try:
        from gimp_plugin.plugin import apply_workflow_rule
        return apply_workflow_rule(template_id, rule_id, style_id)
    except Exception as e:
        logger.error(f"Failed to apply build rule: {e}")
        return {"success": False, "error": str(e)}