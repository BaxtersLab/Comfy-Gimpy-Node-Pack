"""
Settings API for web interface.
"""

import logging
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)


def get_settings() -> Dict[str, Any]:
    """
    Get current settings.

    Returns:
        Settings dictionary
    """
    try:
        from gimp_comfy_bridge.shared.config import load_config
        config = load_config()

        return {
            "comfyui_host": config.comfyui_host,
            "comfyui_port": config.comfyui_port,
            "bridge_host": config.host,
            "bridge_port": config.port,
            "workflows_dir": str(config.workflows_dir),
            "temp_dir": str(config.temp_dir),
            "templates_dir": str(config.templates_dir),
            "styles_dir": str(config.styles_dir),
            "log_level": config.log_level
        }

    except Exception as e:
        logger.error(f"Failed to get settings: {e}")
        return {}


def update_settings(new_settings: Dict[str, Any]) -> bool:
    """
    Update settings.

    Args:
        new_settings (dict): New settings values

    Returns:
        bool: True if successful
    """
    try:
        # Update environment variables
        env_vars = {
            "COMFYUI_HOST": new_settings.get("comfyui_host"),
            "COMFYUI_PORT": str(new_settings.get("comfyui_port", 8188)),
            "COMFY_HOST": new_settings.get("bridge_host"),
            "COMFY_PORT": str(new_settings.get("bridge_port", 8188)),
            "COMFY_WORKFLOWS_DIR": new_settings.get("workflows_dir"),
            "COMFY_TEMP_DIR": new_settings.get("temp_dir"),
            "COMFY_TEMPLATES_DIR": new_settings.get("templates_dir"),
            "COMFY_STYLES_DIR": new_settings.get("styles_dir"),
            "COMFY_LOG_LEVEL": new_settings.get("log_level", "INFO")
        }

        # Set environment variables (these will persist for the session)
        for key, value in env_vars.items():
            if value is not None:
                os.environ[key] = str(value)

        logger.info("Settings updated successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        return False