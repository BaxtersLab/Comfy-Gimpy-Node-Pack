"""
Configuration management for GIMP-ComfyUI bridge.
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class Config:
    """
    Configuration class for the bridge with comprehensive validation.
    """
    def __init__(self, host="localhost", port=8188, comfyui_host="localhost", comfyui_port=8188, workflows_dir=None, temp_dir=None, log_level="INFO"):
        """
        Initialize configuration with validation.

        Args:
            host (str): Bridge host address.
            port (int): Bridge port number.
            comfyui_host (str): ComfyUI host address.
            comfyui_port (int): ComfyUI port number.
            workflows_dir (str, optional): Workflows directory.
            temp_dir (str, optional): Temporary directory.
            log_level (str): Logging level.

        Raises:
            ValueError: If configuration is invalid.
        """
        # Host validation
        if not isinstance(host, str) or not host.strip():
            raise ValueError("Host must be a non-empty string")
        if len(host) > 253:  # Max hostname length
            raise ValueError("Host name too long (>253 characters)")

        if not isinstance(comfyui_host, str) or not comfyui_host.strip():
            raise ValueError("ComfyUI host must be a non-empty string")
        if len(comfyui_host) > 253:
            raise ValueError("ComfyUI host name too long (>253 characters)")

        # Port validation
        if not isinstance(port, int) or not (1 <= port <= 65535):
            raise ValueError("Port must be an integer between 1 and 65535")

        if not isinstance(comfyui_port, int) or not (1 <= comfyui_port <= 65535):
            raise ValueError("ComfyUI port must be an integer between 1 and 65535")

        # Directory validation and creation
        if workflows_dir is not None:
            if not isinstance(workflows_dir, str):
                raise ValueError("Workflows directory must be a string or None")
            workflows_path = Path(workflows_dir)
        else:
            workflows_path = Path(__file__).parent.parent / "examples" / "workflows"

        if temp_dir is not None:
            if not isinstance(temp_dir, str):
                raise ValueError("Temp directory must be a string or None")
            temp_path = Path(temp_dir)
        else:
            temp_path = Path(__file__).parent.parent / "temp"

        # Log level validation
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if log_level not in valid_log_levels:
            raise ValueError(f"Log level must be one of {valid_log_levels}")

        # Set attributes
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}/gimp_bridge/"
        self.comfyui_host = comfyui_host
        self.comfyui_port = comfyui_port
        self.workflows_dir = workflows_path
        self.temp_dir = temp_path
        self.log_level = log_level

        # Ensure directories exist with proper permissions
        try:
            self.workflows_dir.mkdir(parents=True, exist_ok=True)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            raise ValueError(f"Cannot create required directories: {e}")

        # Validate directory accessibility
        if not self._is_directory_accessible(self.workflows_dir):
            raise ValueError(f"Workflows directory not accessible: {self.workflows_dir}")
        if not self._is_directory_accessible(self.temp_dir):
            raise ValueError(f"Temp directory not accessible: {self.temp_dir}")

    def _is_directory_accessible(self, path: Path) -> bool:
        """
        Check if directory is accessible for read/write operations.

        Args:
            path (Path): Directory path to check.

        Returns:
            bool: True if accessible.
        """
        try:
            # Test write access
            test_file = path / ".test_access"
            test_file.write_text("test")
            test_file.unlink()
            return True
        except (OSError, PermissionError):
            return False

    def get_safe_temp_dir(self) -> Path:
        """
        Get a safe temporary directory with validation.

        Returns:
            Path: Safe temporary directory path.
        """
        if not self.temp_dir.exists():
            raise RuntimeError(f"Temp directory does not exist: {self.temp_dir}")
        if not self._is_directory_accessible(self.temp_dir):
            raise RuntimeError(f"Temp directory not accessible: {self.temp_dir}")
        return self.temp_dir

def load_config():
    """
    Load configuration from environment with comprehensive validation and error handling.

    Returns:
        Config: The loaded configuration instance.

    Raises:
        ValueError: If configuration is invalid.
        RuntimeError: If configuration cannot be loaded.
    """
    try:
        # Load environment variables with validation
        host = os.getenv("COMFY_HOST", "localhost")
        if not isinstance(host, str) or not host.strip():
            raise ValueError("COMFY_HOST must be a non-empty string")

        port_str = os.getenv("COMFY_PORT", "8188")
        try:
            port = int(port_str)
        except ValueError:
            raise ValueError(f"COMFY_PORT must be a valid integer, got: {port_str}")

        comfyui_host = os.getenv("COMFYUI_HOST", "localhost")
        if not isinstance(comfyui_host, str) or not comfyui_host.strip():
            raise ValueError("COMFYUI_HOST must be a non-empty string")

        comfyui_port_str = os.getenv("COMFYUI_PORT", "8188")
        try:
            comfyui_port = int(comfyui_port_str)
        except ValueError:
            raise ValueError(f"COMFYUI_PORT must be a valid integer, got: {comfyui_port_str}")

        workflows_dir = os.getenv("COMFY_WORKFLOWS_DIR")
        temp_dir = os.getenv("COMFY_TEMP_DIR")
        log_level = os.getenv("COMFY_LOG_LEVEL", "INFO")

        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if log_level not in valid_log_levels:
            logger.warning(f"Invalid COMFY_LOG_LEVEL '{log_level}', using 'INFO'")
            log_level = "INFO"

        # Create and validate configuration
        config = Config(host, port, comfyui_host, comfyui_port, workflows_dir, temp_dir, log_level)
        logger.info("Configuration loaded successfully")
        return config

    except (ValueError, RuntimeError) as e:
        logger.error(f"Configuration error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading configuration: {e}")
        raise RuntimeError(f"Failed to load configuration: {e}")