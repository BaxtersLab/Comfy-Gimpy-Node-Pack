"""
Brand Kit Loading Module.

Provides functionality to load brand kits from various sources including
local filesystem and cloud sync providers.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Union, Dict, Any
from datetime import datetime

from .kit import BrandKit
from ..shared.config import ConfigManager
from ..sync import SyncManager

logger = logging.getLogger(__name__)


class BrandKitLoadError(Exception):
    """Exception raised when brand kit loading fails."""
    pass


def load_brandkit(name_or_path: str, config_manager: Optional[ConfigManager] = None) -> BrandKit:
    """
    Load a brand kit by name or path.

    Args:
        name_or_path: Brand kit name or file path
        config_manager: Optional config manager for path resolution

    Returns:
        Loaded BrandKit instance

    Raises:
        BrandKitLoadError: If loading fails
    """
    try:
        # Try as file path first
        path = Path(name_or_path)
        if path.exists() and path.is_file():
            return BrandKit.load_from_file(path)

        # Try as name with config manager
        if config_manager:
            brandkit_dir = config_manager.get('brandkit.directory', 'brand_kits')
            full_path = Path(brandkit_dir) / f"{name_or_path}.json"
            if full_path.exists():
                return BrandKit.load_from_file(full_path)

        # Try cloud sync if available
        try:
            from ..sync import get_sync_manager
            sync_manager = get_sync_manager()
            if sync_manager:
                return load_brandkit_from_sync(name_or_path, sync_manager)
        except ImportError:
            logger.debug("Sync manager not available for brand kit loading")

        raise FileNotFoundError(f"Brand kit '{name_or_path}' not found")

    except Exception as e:
        logger.error(f"Failed to load brand kit '{name_or_path}': {e}")
        raise BrandKitLoadError(f"Failed to load brand kit '{name_or_path}': {e}") from e


def load_brandkit_from_path(path: Union[str, Path]) -> BrandKit:
    """
    Load a brand kit from a specific file path.

    Args:
        path: Path to the brand kit JSON file

    Returns:
        Loaded BrandKit instance

    Raises:
        BrandKitLoadError: If loading fails
    """
    try:
        return BrandKit.load_from_file(path)
    except Exception as e:
        logger.error(f"Failed to load brand kit from path '{path}': {e}")
        raise BrandKitLoadError(f"Failed to load brand kit from path '{path}': {e}") from e


def load_brandkit_from_sync(name: str, sync_manager: SyncManager) -> BrandKit:
    """
    Load a brand kit from cloud sync provider.

    Args:
        name: Brand kit name
        sync_manager: Sync manager instance

    Returns:
        Loaded BrandKit instance

    Raises:
        BrandKitLoadError: If loading fails
    """
    try:
        # Construct sync path for brand kit
        sync_path = f"brandkits/{name}.json"

        # Download from sync provider
        content = sync_manager.download_file(sync_path)
        if not content:
            raise FileNotFoundError(f"Brand kit '{name}' not found in sync")

        # Parse JSON content
        data = json.loads(content)
        return BrandKit.from_dict(data)

    except Exception as e:
        logger.error(f"Failed to load brand kit '{name}' from sync: {e}")
        raise BrandKitLoadError(f"Failed to load brand kit '{name}' from sync: {e}") from e


def list_brandkits(config_manager: Optional[ConfigManager] = None,
                   include_sync: bool = True) -> List[Dict[str, Any]]:
    """
    List all available brand kits.

    Args:
        config_manager: Optional config manager for path resolution
        include_sync: Whether to include brand kits from sync providers

    Returns:
        List of brand kit metadata dictionaries
    """
    brandkits = []

    try:
        # List local brand kits
        if config_manager:
            brandkit_dir = Path(config_manager.get('brandkit.directory', 'brand_kits'))
            if brandkit_dir.exists():
                for json_file in brandkit_dir.glob("*.json"):
                    try:
                        kit = BrandKit.load_from_file(json_file)
                        brandkits.append({
                            'name': kit.metadata.name,
                            'description': kit.metadata.description,
                            'version': kit.metadata.version,
                            'path': str(json_file),
                            'source': 'local',
                            'tags': kit.metadata.tags,
                            'updated_at': kit.metadata.updated_at.isoformat(),
                        })
                    except Exception as e:
                        logger.warning(f"Failed to load brand kit '{json_file}': {e}")

        # List sync brand kits
        if include_sync:
            try:
                from ..sync import get_sync_manager
                sync_manager = get_sync_manager()
                if sync_manager:
                    sync_brandkits = list_brandkits_from_sync(sync_manager)
                    brandkits.extend(sync_brandkits)
            except ImportError:
                logger.debug("Sync manager not available for brand kit listing")

    except Exception as e:
        logger.error(f"Failed to list brand kits: {e}")

    return brandkits


def list_brandkits_from_sync(sync_manager: SyncManager) -> List[Dict[str, Any]]:
    """
    List brand kits available in sync provider.

    Args:
        sync_manager: Sync manager instance

    Returns:
        List of brand kit metadata dictionaries
    """
    brandkits = []

    try:
        # List files in brandkits directory
        files = sync_manager.list_files("brandkits/")
        for file_info in files:
            if file_info['name'].endswith('.json'):
                try:
                    # Download and parse metadata
                    content = sync_manager.download_file(file_info['path'])
                    if content:
                        data = json.loads(content)
                        kit = BrandKit.from_dict(data)
                        brandkits.append({
                            'name': kit.metadata.name,
                            'description': kit.metadata.description,
                            'version': kit.metadata.version,
                            'path': file_info['path'],
                            'source': 'sync',
                            'tags': kit.metadata.tags,
                            'updated_at': kit.metadata.updated_at.isoformat(),
                        })
                except Exception as e:
                    logger.warning(f"Failed to parse brand kit '{file_info['path']}': {e}")

    except Exception as e:
        logger.error(f"Failed to list brand kits from sync: {e}")

    return brandkits


def get_brandkit_versions(name: str, config_manager: Optional[ConfigManager] = None) -> List[Dict[str, Any]]:
    """
    Get all versions of a brand kit.

    Args:
        name: Brand kit name
        config_manager: Optional config manager

    Returns:
        List of version information
    """
    versions = []

    try:
        # Check local versions
        if config_manager:
            brandkit_dir = Path(config_manager.get('brandkit.directory', 'brand_kits'))
            backup_dir = brandkit_dir / "backups" / name
            if backup_dir.exists():
                for backup_file in backup_dir.glob("*.json"):
                    try:
                        kit = BrandKit.load_from_file(backup_file)
                        versions.append({
                            'version': kit.metadata.version,
                            'path': str(backup_file),
                            'source': 'local',
                            'updated_at': kit.metadata.updated_at.isoformat(),
                        })
                    except Exception as e:
                        logger.warning(f"Failed to load backup '{backup_file}': {e}")

        # Check sync versions
        try:
            from ..sync import get_sync_manager
            sync_manager = get_sync_manager()
            if sync_manager:
                sync_versions = get_brandkit_versions_from_sync(name, sync_manager)
                versions.extend(sync_versions)
        except ImportError:
            pass

    except Exception as e:
        logger.error(f"Failed to get versions for brand kit '{name}': {e}")

    return sorted(versions, key=lambda x: x['updated_at'], reverse=True)


def get_brandkit_versions_from_sync(name: str, sync_manager: SyncManager) -> List[Dict[str, Any]]:
    """
    Get brand kit versions from sync provider.

    Args:
        name: Brand kit name
        sync_manager: Sync manager instance

    Returns:
        List of version information
    """
    versions = []

    try:
        # List version files in sync
        versions_path = f"brandkits/backups/{name}/"
        files = sync_manager.list_files(versions_path)

        for file_info in files:
            if file_info['name'].endswith('.json'):
                try:
                    content = sync_manager.download_file(file_info['path'])
                    if content:
                        data = json.loads(content)
                        kit = BrandKit.from_dict(data)
                        versions.append({
                            'version': kit.metadata.version,
                            'path': file_info['path'],
                            'source': 'sync',
                            'updated_at': kit.metadata.updated_at.isoformat(),
                        })
                except Exception as e:
                    logger.warning(f"Failed to parse version '{file_info['path']}': {e}")

    except Exception as e:
        logger.error(f"Failed to get versions from sync for '{name}': {e}")

    return versions</content>
<parameter name="filePath">c:\Users\Baxter\Documents\ComfyUI_env\ComfyUI\custom_nodes\Comfy Gimpy Node Pack\gimp_comfy_bridge\brandkit\loader.py