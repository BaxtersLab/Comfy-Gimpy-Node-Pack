"""
Configuration management for GIMP-ComfyUI bridge.
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class Config:
    """
    Configuration class for the bridge.
    """
    def __init__(self, host="localhost", port=8188, workflows_dir=None, temp_dir=None, log_level="INFO"):
        """
        Initialize configuration.

        Args:
            host (str): Host address.
            port (int): Port number.
            workflows_dir (str, optional): Workflows directory.
            temp_dir (str, optional): Temporary directory.
            log_level (str): Logging level.
        """
        if not isinstance(port, int) or not (1 <= port <= 65535):
            raise ValueError("Port must be an integer between 1 and 65535")
        
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}/gimp_bridge/"
        self.workflows_dir = Path(workflows_dir) if workflows_dir else Path(__file__).parent.parent / "examples" / "workflows"
        self.temp_dir = Path(temp_dir) if temp_dir else Path(__file__).parent.parent / "temp"
        self.log_level = log_level
        
        # Ensure directories exist
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

def load_config():
    """
    Load configuration from environment or defaults.

    Returns:
        Config: The loaded configuration instance.
    """
    try:
        host = os.getenv("COMFY_HOST", "localhost")
        port_str = os.getenv("COMFY_PORT", "8188")
        port = int(port_str)
        workflows_dir = os.getenv("COMFY_WORKFLOWS_DIR")
        temp_dir = os.getenv("COMFY_TEMP_DIR")
        log_level = os.getenv("COMFY_LOG_LEVEL", "INFO")
        return Config(host, port, workflows_dir, temp_dir, log_level)
    except ValueError as e:
        logger.error(f"Invalid configuration: {e}")
        raise