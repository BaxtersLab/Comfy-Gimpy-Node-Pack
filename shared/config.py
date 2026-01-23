"""
Configuration management for Comfy Gimpy Studio.
Handles settings, paths, and pack-related configuration.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class Config:
    """
    Configuration manager for Comfy Gimpy Studio.
    """

    def __init__(self):
        """Initialize configuration."""
        # Base paths
        self.base_dir = Path(__file__).parent.parent
        self.data_dir = self.base_dir / "data"
        self.temp_dir = self.base_dir / "temp"
        self.packs_dir = self.data_dir / "packs"
        self.exports_dir = self.data_dir / "exports"

        # Create directories
        self._ensure_directories()

        # Pack configuration
        self.pack_config = {
            "registry_db": str(self.data_dir / "packs.db"),
            "default_license": "MIT",
            "max_pack_size": 100 * 1024 * 1024,  # 100MB
            "supported_formats": ["zip", "directory"],
            "auto_validate": True,
            "backup_on_update": True,
            "max_backups": 5,
        }

        # Workflow configuration
        self.workflow_config = {
            "cache_db": str(self.data_dir / "workflow_cache.db"),
            "cache_ttl": 3600,  # 1 hour
            "max_cache_size": 100 * 1024 * 1024,  # 100MB
            "max_cache_entries": 1000,
            "auto_validate_workflows": True,
            "enable_rule_engine": True,
            "default_template_dir": str(self.data_dir / "templates"),
            "default_style_dir": str(self.data_dir / "styles"),
            "max_build_time": 300,  # 5 minutes
            "enable_caching": True,
            "cache_cleanup_interval": 3600,  # 1 hour
        }

        # Load user config if exists
        self._load_user_config()

    def _ensure_directories(self):
        """Ensure all required directories exist."""
        directories = [
            self.data_dir,
            self.temp_dir,
            self.packs_dir,
            self.exports_dir,
            self.packs_dir / "installed",
            self.packs_dir / "backups",
            self.packs_dir / "temp",
            self.workflow_template_dir,
            self.workflow_style_dir,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def _load_user_config(self):
        """Load user configuration from file."""
        config_file = self.data_dir / "config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)

                # Update pack config with user settings
                if "packs" in user_config:
                    self.pack_config.update(user_config["packs"])

                # Update workflow config with user settings
                if "workflows" in user_config:
                    self.workflow_config.update(user_config["workflows"])

                logger.info("Loaded user configuration")

            except Exception as e:
                logger.error(f"Failed to load user config: {e}")

    def save_user_config(self):
        """Save current configuration to file."""
        config_file = self.data_dir / "config.json"
        try:
            config_data = {
                "packs": self.pack_config,
                "workflows": self.workflow_config
            }

            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)

            logger.info("Saved user configuration")

        except Exception as e:
            logger.error(f"Failed to save user config: {e}")

    # Pack-related properties
    @property
    def registry_db_path(self) -> Path:
        """Get pack registry database path."""
        return Path(self.pack_config["registry_db"])

    @property
    def packs_install_dir(self) -> Path:
        """Get packs installation directory."""
        return self.packs_dir / "installed"

    @property
    def packs_backup_dir(self) -> Path:
        """Get packs backup directory."""
        return self.packs_dir / "backups"

    @property
    def packs_temp_dir(self) -> Path:
        """Get packs temporary directory."""
        return self.packs_dir / "temp"

    @property
    def default_pack_license(self) -> str:
        """Get default pack license."""
        return self.pack_config["default_license"]

    @property
    def max_pack_size(self) -> int:
        """Get maximum pack size in bytes."""
        return self.pack_config["max_pack_size"]

    @property
    def supported_pack_formats(self) -> list:
        """Get supported pack formats."""
        return self.pack_config["supported_formats"]

    @property
    def auto_validate_packs(self) -> bool:
        """Get auto-validation setting."""
        return self.pack_config["auto_validate"]

    @property
    def backup_on_pack_update(self) -> bool:
        """Get backup on update setting."""
        return self.pack_config["backup_on_update"]

    @property
    def max_pack_backups(self) -> int:
        """Get maximum number of pack backups."""
        return self.pack_config["max_backups"]

    def get_pack_config(self, key: str, default: Any = None) -> Any:
        """Get a pack configuration value."""
        return self.pack_config.get(key, default)

    def set_pack_config(self, key: str, value: Any):
        """Set a pack configuration value."""
        self.pack_config[key] = value
        self.save_user_config()

    def get_all_pack_config(self) -> Dict[str, Any]:
        """Get all pack configuration."""
        return self.pack_config.copy()

    # Workflow-related properties
    @property
    def workflow_cache_db_path(self) -> Path:
        """Get workflow cache database path."""
        return Path(self.workflow_config["cache_db"])

    @property
    def workflow_cache_ttl(self) -> int:
        """Get workflow cache TTL in seconds."""
        return self.workflow_config["cache_ttl"]

    @property
    def workflow_max_cache_size(self) -> int:
        """Get maximum workflow cache size in bytes."""
        return self.workflow_config["max_cache_size"]

    @property
    def workflow_max_cache_entries(self) -> int:
        """Get maximum number of workflow cache entries."""
        return self.workflow_config["max_cache_entries"]

    @property
    def auto_validate_workflows(self) -> bool:
        """Get auto-validation setting for workflows."""
        return self.workflow_config["auto_validate_workflows"]

    @property
    def enable_workflow_rule_engine(self) -> bool:
        """Get rule engine enable setting."""
        return self.workflow_config["enable_rule_engine"]

    @property
    def workflow_template_dir(self) -> Path:
        """Get workflow template directory."""
        return Path(self.workflow_config["default_template_dir"])

    @property
    def workflow_style_dir(self) -> Path:
        """Get workflow style directory."""
        return Path(self.workflow_config["default_style_dir"])

    @property
    def workflow_max_build_time(self) -> int:
        """Get maximum workflow build time in seconds."""
        return self.workflow_config["max_build_time"]

    @property
    def workflow_enable_caching(self) -> bool:
        """Get workflow caching enable setting."""
        return self.workflow_config["enable_caching"]

    @property
    def workflow_cache_cleanup_interval(self) -> int:
        """Get workflow cache cleanup interval in seconds."""
        return self.workflow_config["cache_cleanup_interval"]

    def get_workflow_config(self, key: str, default: Any = None) -> Any:
        """Get a workflow configuration value."""
        return self.workflow_config.get(key, default)

    def set_workflow_config(self, key: str, value: Any):
        """Set a workflow configuration value."""
        self.workflow_config[key] = value
        self.save_user_config()

    def get_all_workflow_config(self) -> Dict[str, Any]:
        """Get all workflow configuration."""
        return self.workflow_config.copy()


# Global config instance
_config_instance = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


def load_config() -> Config:
    """Load configuration (alias for get_config)."""
    return get_config()