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
    def __init__(self, host="localhost", port=8188, comfyui_host="localhost", comfyui_port=8188, workflows_dir=None, temp_dir=None, templates_dir=None, styles_dir=None, task_db_path=None, log_level="INFO",
                 # Async engine configuration
                 async_queue_max_size=1000, async_max_workers=4, async_task_timeout=300, async_enable_web_ui=True, async_web_ui_port=None,
                 # Template generation configuration
                 template_gen_enabled=True, template_gen_max_variants=10, template_gen_default_quality=95, template_gen_output_format="xcf", template_gen_ai_model=None, template_gen_cache_dir=None,
                 # Remote execution configuration
                 remote_enabled=True, remote_nodes=None, remote_health_check_interval=30, remote_max_retry_attempts=3,
                 # Cloud sync configuration
                 sync_enabled=True, sync_providers=None, sync_auto_sync=True, sync_interval_minutes=60, sync_conflict_resolution="newer_wins", sync_encrypt=False,
                 # Brand kit configuration
                 brandkit_enabled=True, brandkit_directory=None, brandkit_sync_enabled=True, brandkit_auto_apply=False, brandkit_preview_enabled=True):
        """
        Initialize configuration with validation.

        Args:
            host (str): Bridge host address.
            port (int): Bridge port number.
            comfyui_host (str): ComfyUI host address.
            comfyui_port (int): ComfyUI port number.
            workflows_dir (str, optional): Workflows directory.
            temp_dir (str, optional): Temporary directory.
            templates_dir (str, optional): Templates directory.
            styles_dir (str, optional): Styles directory.
            task_db_path (str, optional): Task database path.
            log_level (str): Logging level.
            async_queue_max_size (int): Maximum async task queue size.
            async_max_workers (int): Maximum async worker threads.
            async_task_timeout (int): Default async task timeout in seconds.
            async_enable_web_ui (bool): Enable async web UI.
            async_web_ui_port (int, optional): Async web UI port.
            brandkit_enabled (bool): Enable brand kit system.
            brandkit_directory (str, optional): Brand kit storage directory.
            brandkit_sync_enabled (bool): Enable brand kit cloud sync.
            brandkit_auto_apply (bool): Auto-apply brand kits to new content.
            brandkit_preview_enabled (bool): Enable brand kit preview generation.

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

        if templates_dir is not None:
            if not isinstance(templates_dir, str):
                raise ValueError("Templates directory must be a string or None")
            templates_path = Path(templates_dir)
        else:
            templates_path = Path(__file__).parent.parent / "templates"

        if styles_dir is not None:
            if not isinstance(styles_dir, str):
                raise ValueError("Styles directory must be a string or None")
            styles_path = Path(styles_dir)
        else:
            styles_path = Path(__file__).parent.parent / "styles"

        if task_db_path is not None:
            if not isinstance(task_db_path, str):
                raise ValueError("Task database path must be a string or None")
            task_db = Path(task_db_path)
        else:
            task_db = Path(__file__).parent.parent / "task_db.sqlite"

        # Log level validation
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if log_level not in valid_log_levels:
            raise ValueError(f"Log level must be one of {valid_log_levels}")

        # Async engine validation
        if not isinstance(async_queue_max_size, int) or async_queue_max_size < 1:
            raise ValueError("Async queue max size must be a positive integer")

        if not isinstance(async_max_workers, int) or async_max_workers < 1:
            raise ValueError("Async max workers must be a positive integer")

        if not isinstance(async_task_timeout, int) or async_task_timeout < 1:
            raise ValueError("Async task timeout must be a positive integer")

        if async_web_ui_port is not None:
            if not isinstance(async_web_ui_port, int) or not (1 <= async_web_ui_port <= 65535):
                raise ValueError("Async web UI port must be an integer between 1 and 65535")
            if async_web_ui_port == port:
                raise ValueError("Async web UI port cannot be the same as bridge port")

        # Template generation validation
        if not isinstance(template_gen_enabled, bool):
            raise ValueError("Template generation enabled must be a boolean")

        if not isinstance(template_gen_max_variants, int) or template_gen_max_variants < 1:
            raise ValueError("Template generation max variants must be a positive integer")

        if not isinstance(template_gen_default_quality, int) or not (1 <= template_gen_default_quality <= 100):
            raise ValueError("Template generation default quality must be an integer between 1 and 100")

        valid_output_formats = ["xcf", "psd", "svg", "png", "jpg"]
        if template_gen_output_format not in valid_output_formats:
            raise ValueError(f"Template generation output format must be one of {valid_output_formats}")

        if template_gen_ai_model is not None and not isinstance(template_gen_ai_model, str):
            raise ValueError("Template generation AI model must be a string or None")

        if template_gen_cache_dir is not None:
            if not isinstance(template_gen_cache_dir, str):
                raise ValueError("Template generation cache directory must be a string or None")
            cache_path = Path(template_gen_cache_dir)
        else:
            cache_path = Path(__file__).parent.parent / "cache" / "template_gen"

        # Remote execution validation
        if not isinstance(remote_enabled, bool):
            raise ValueError("Remote execution enabled must be a boolean")

        if remote_nodes is not None:
            if not isinstance(remote_nodes, list):
                raise ValueError("Remote nodes must be a list or None")
            for node in remote_nodes:
                if not isinstance(node, dict) or 'url' not in node:
                    raise ValueError("Each remote node must be a dict with 'url' key")

        if not isinstance(remote_health_check_interval, int) or remote_health_check_interval < 5:
            raise ValueError("Remote health check interval must be an integer >= 5 seconds")

        if not isinstance(remote_max_retry_attempts, int) or remote_max_retry_attempts < 0:
            raise ValueError("Remote max retry attempts must be a non-negative integer")

        # Cloud sync validation
        if not isinstance(sync_enabled, bool):
            raise ValueError("Sync enabled must be a boolean")

        if sync_providers is not None:
            if not isinstance(sync_providers, list):
                raise ValueError("Sync providers must be a list or None")
            for provider in sync_providers:
                if not isinstance(provider, dict) or 'name' not in provider or 'type' not in provider:
                    raise ValueError("Each sync provider must be a dict with 'name' and 'type' keys")

        if not isinstance(sync_auto_sync, bool):
            raise ValueError("Sync auto sync must be a boolean")

        if not isinstance(sync_interval_minutes, int) or sync_interval_minutes < 1:
            raise ValueError("Sync interval minutes must be a positive integer")

        valid_conflict_resolutions = ["local_wins", "remote_wins", "newer_wins", "manual", "merge"]
        if sync_conflict_resolution not in valid_conflict_resolutions:
            raise ValueError(f"Sync conflict resolution must be one of {valid_conflict_resolutions}")

        if not isinstance(sync_encrypt, bool):
            raise ValueError("Sync encrypt must be a boolean")

        # Brand kit validation
        if not isinstance(brandkit_enabled, bool):
            raise ValueError("Brand kit enabled must be a boolean")

        if brandkit_directory is not None:
            if not isinstance(brandkit_directory, str) or not brandkit_directory.strip():
                raise ValueError("Brand kit directory must be a non-empty string")

        if not isinstance(brandkit_sync_enabled, bool):
            raise ValueError("Brand kit sync enabled must be a boolean")

        if not isinstance(brandkit_auto_apply, bool):
            raise ValueError("Brand kit auto apply must be a boolean")

        if not isinstance(brandkit_preview_enabled, bool):
            raise ValueError("Brand kit preview enabled must be a boolean")

        # Set attributes
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}/gimp_bridge/"
        self.comfyui_host = comfyui_host
        self.comfyui_port = comfyui_port
        self.workflows_dir = workflows_path
        self.temp_dir = temp_path
        self.templates_dir = templates_path
        self.styles_dir = styles_path
        self.task_db_path = task_db
        self.log_level = log_level

        # Async engine attributes
        self.async_queue_max_size = async_queue_max_size
        self.async_max_workers = async_max_workers
        self.async_task_timeout = async_task_timeout
        self.async_enable_web_ui = async_enable_web_ui
        self.async_web_ui_port = async_web_ui_port or (port + 1)  # Default to bridge port + 1

        # Template generation attributes
        self.template_gen_enabled = template_gen_enabled
        self.template_gen_max_variants = template_gen_max_variants
        self.template_gen_default_quality = template_gen_default_quality
        self.template_gen_output_format = template_gen_output_format
        self.template_gen_ai_model = template_gen_ai_model
        self.template_gen_cache_dir = cache_path

        # Remote execution attributes
        self.remote_enabled = remote_enabled
        self.remote_nodes = remote_nodes or []
        self.remote_health_check_interval = remote_health_check_interval
        self.remote_max_retry_attempts = remote_max_retry_attempts

        # Cloud sync attributes
        self.sync_enabled = sync_enabled
        self.sync_providers = sync_providers or []
        self.sync_auto_sync = sync_auto_sync
        self.sync_interval_minutes = sync_interval_minutes
        self.sync_conflict_resolution = sync_conflict_resolution
        self.sync_encrypt = sync_encrypt

        # Brand kit attributes
        self.brandkit_enabled = brandkit_enabled
        self.brandkit_directory = Path(brandkit_directory) if brandkit_directory else self.base_dir / "brand_kits"
        self.brandkit_sync_enabled = brandkit_sync_enabled
        self.brandkit_auto_apply = brandkit_auto_apply
        self.brandkit_preview_enabled = brandkit_preview_enabled

        # Ensure directories exist with proper permissions
        try:
            self.workflows_dir.mkdir(parents=True, exist_ok=True)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            self.templates_dir.mkdir(parents=True, exist_ok=True)
            self.styles_dir.mkdir(parents=True, exist_ok=True)
            self.template_gen_cache_dir.mkdir(parents=True, exist_ok=True)
            self.brandkit_directory.mkdir(parents=True, exist_ok=True)
            # Task database is a file, ensure parent directory exists
            self.task_db_path.parent.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            raise ValueError(f"Cannot create required directories: {e}")

        # Validate directory accessibility
        if not self._is_directory_accessible(self.workflows_dir):
            raise ValueError(f"Workflows directory not accessible: {self.workflows_dir}")
        if not self._is_directory_accessible(self.temp_dir):
            raise ValueError(f"Temp directory not accessible: {self.temp_dir}")
        if not self._is_directory_accessible(self.templates_dir):
            raise ValueError(f"Templates directory not accessible: {self.templates_dir}")
        if not self._is_directory_accessible(self.styles_dir):
            raise ValueError(f"Styles directory not accessible: {self.styles_dir}")
        if not self._is_directory_accessible(self.brandkit_directory):
            raise ValueError(f"Brand kit directory not accessible: {self.brandkit_directory}")
        if not self._is_directory_accessible(self.template_gen_cache_dir):
            raise ValueError(f"Template generation cache directory not accessible: {self.template_gen_cache_dir}")
        if not self._is_directory_accessible(self.task_db_path.parent):
            raise ValueError(f"Task database directory not accessible: {self.task_db_path.parent}")

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

    def get_remote_config(self) -> dict:
        """
        Get remote execution configuration.

        Returns:
            dict: Remote execution configuration
        """
        return {
            'enabled': self.remote_enabled,
            'nodes': self.remote_nodes,
            'health_check_interval': self.remote_health_check_interval,
            'max_retry_attempts': self.remote_max_retry_attempts
        }

    def get_sync_config(self):
        """
        Get cloud sync configuration.

        Returns:
            SyncConfig: Cloud sync configuration
        """
        from .types import SyncConfig

        providers = []
        for provider in self.sync_providers:
            providers.append(SyncConfig.ProviderConfig(
                name=provider['name'],
                type=provider['type'],
                settings=provider.get('settings', {})
            ))

        return SyncConfig(
            providers=providers,
            auto_sync=self.sync_auto_sync,
            sync_interval_minutes=self.sync_interval_minutes,
            conflict_resolution=self.sync_conflict_resolution,
            encrypt_sync=self.sync_encrypt
        )

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
        templates_dir = os.getenv("COMFY_TEMPLATES_DIR")
        styles_dir = os.getenv("COMFY_STYLES_DIR")
        task_db_path = os.getenv("COMFY_TASK_DB_PATH")
        log_level = os.getenv("COMFY_LOG_LEVEL", "INFO")

        # Template generation environment variables
        template_gen_enabled_str = os.getenv("COMFY_TEMPLATE_GEN_ENABLED", "true")
        try:
            template_gen_enabled = template_gen_enabled_str.lower() in ("true", "1", "yes", "on")
        except ValueError:
            template_gen_enabled = True

        template_gen_max_variants_str = os.getenv("COMFY_TEMPLATE_GEN_MAX_VARIANTS", "10")
        try:
            template_gen_max_variants = int(template_gen_max_variants_str)
        except ValueError:
            template_gen_max_variants = 10

        template_gen_default_quality_str = os.getenv("COMFY_TEMPLATE_GEN_DEFAULT_QUALITY", "95")
        try:
            template_gen_default_quality = int(template_gen_default_quality_str)
        except ValueError:
            template_gen_default_quality = 95

        template_gen_output_format = os.getenv("COMFY_TEMPLATE_GEN_OUTPUT_FORMAT", "xcf")
        template_gen_ai_model = os.getenv("COMFY_TEMPLATE_GEN_AI_MODEL")
        template_gen_cache_dir = os.getenv("COMFY_TEMPLATE_GEN_CACHE_DIR")

        # Remote execution environment variables
        remote_enabled_str = os.getenv("COMFY_REMOTE_ENABLED", "true")
        try:
            remote_enabled = remote_enabled_str.lower() in ("true", "1", "yes", "on")
        except ValueError:
            remote_enabled = True

        remote_nodes = None
        remote_nodes_str = os.getenv("COMFY_REMOTE_NODES")
        if remote_nodes_str:
            try:
                import json
                remote_nodes = json.loads(remote_nodes_str)
            except (json.JSONDecodeError, ValueError):
                logger.warning(f"Invalid COMFY_REMOTE_NODES JSON: {remote_nodes_str}")
                remote_nodes = []

        remote_health_check_interval_str = os.getenv("COMFY_REMOTE_HEALTH_CHECK_INTERVAL", "30")
        try:
            remote_health_check_interval = int(remote_health_check_interval_str)
        except ValueError:
            remote_health_check_interval = 30

        remote_max_retry_attempts_str = os.getenv("COMFY_REMOTE_MAX_RETRY_ATTEMPTS", "3")
        try:
            remote_max_retry_attempts = int(remote_max_retry_attempts_str)
        except ValueError:
            remote_max_retry_attempts = 3

        # Cloud sync environment variables
        sync_enabled_str = os.getenv("COMFY_SYNC_ENABLED", "true")
        try:
            sync_enabled = sync_enabled_str.lower() in ("true", "1", "yes", "on")
        except ValueError:
            sync_enabled = True

        sync_providers = None
        sync_providers_str = os.getenv("COMFY_SYNC_PROVIDERS")
        if sync_providers_str:
            try:
                import json
                sync_providers = json.loads(sync_providers_str)
            except (json.JSONDecodeError, ValueError):
                logger.warning(f"Invalid COMFY_SYNC_PROVIDERS JSON: {sync_providers_str}")
                sync_providers = []

        sync_auto_sync_str = os.getenv("COMFY_SYNC_AUTO_SYNC", "true")
        try:
            sync_auto_sync = sync_auto_sync_str.lower() in ("true", "1", "yes", "on")
        except ValueError:
            sync_auto_sync = True

        sync_interval_minutes_str = os.getenv("COMFY_SYNC_INTERVAL_MINUTES", "60")
        try:
            sync_interval_minutes = int(sync_interval_minutes_str)
        except ValueError:
            sync_interval_minutes = 60

        sync_conflict_resolution = os.getenv("COMFY_SYNC_CONFLICT_RESOLUTION", "newer_wins")

        sync_encrypt_str = os.getenv("COMFY_SYNC_ENCRYPT", "false")
        try:
            sync_encrypt = sync_encrypt_str.lower() in ("true", "1", "yes", "on")
        except ValueError:
            sync_encrypt = False

        # Brand kit environment variables
        brandkit_enabled_str = os.getenv("COMFY_BRANDKIT_ENABLED", "true")
        try:
            brandkit_enabled = brandkit_enabled_str.lower() in ("true", "1", "yes", "on")
        except ValueError:
            brandkit_enabled = True

        brandkit_directory = os.getenv("COMFY_BRANDKIT_DIRECTORY")

        brandkit_sync_enabled_str = os.getenv("COMFY_BRANDKIT_SYNC_ENABLED", "true")
        try:
            brandkit_sync_enabled = brandkit_sync_enabled_str.lower() in ("true", "1", "yes", "on")
        except ValueError:
            brandkit_sync_enabled = True

        brandkit_auto_apply_str = os.getenv("COMFY_BRANDKIT_AUTO_APPLY", "false")
        try:
            brandkit_auto_apply = brandkit_auto_apply_str.lower() in ("true", "1", "yes", "on")
        except ValueError:
            brandkit_auto_apply = False

        brandkit_preview_enabled_str = os.getenv("COMFY_BRANDKIT_PREVIEW_ENABLED", "true")
        try:
            brandkit_preview_enabled = brandkit_preview_enabled_str.lower() in ("true", "1", "yes", "on")
        except ValueError:
            brandkit_preview_enabled = True

        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if log_level not in valid_log_levels:
            logger.warning(f"Invalid COMFY_LOG_LEVEL '{log_level}', using 'INFO'")
            log_level = "INFO"

        # Create and validate configuration
        config = Config(host, port, comfyui_host, comfyui_port, workflows_dir, temp_dir, templates_dir, styles_dir, task_db_path, log_level,
                       async_queue_max_size, async_max_workers, async_task_timeout, async_enable_web_ui, async_web_ui_port,
                       template_gen_enabled, template_gen_max_variants, template_gen_default_quality, template_gen_output_format, template_gen_ai_model, template_gen_cache_dir,
                       remote_enabled, remote_nodes, remote_health_check_interval, remote_max_retry_attempts,
                       sync_enabled, sync_providers, sync_auto_sync, sync_interval_minutes, sync_conflict_resolution, sync_encrypt,
                       brandkit_enabled, brandkit_directory, brandkit_sync_enabled, brandkit_auto_apply, brandkit_preview_enabled)
        logger.info("Configuration loaded successfully")
        return config

    except (ValueError, RuntimeError) as e:
        logger.error(f"Configuration error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading configuration: {e}")
        raise RuntimeError(f"Failed to load configuration: {e}")