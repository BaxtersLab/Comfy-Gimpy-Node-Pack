"""
Pack installation and update functionality.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import json
import zipfile
import shutil
import tempfile
from datetime import datetime

logger = logging.getLogger(__name__)


class PackInstaller:
    """Handles installation and updating of packs."""

    def __init__(self, install_base: Optional[Path] = None):
        self.install_base = install_base or Path("installed_packs")
        self.install_base.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path("temp/install")
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def install_pack(self,
                    pack_path: Union[str, Path],
                    verify: bool = True,
                    backup_existing: bool = True) -> Dict[str, Any]:
        """
        Install a pack from file or directory.

        Args:
            pack_path: Path to pack file or directory
            verify: Whether to verify pack integrity
            backup_existing: Whether to backup existing installation

        Returns:
            Installation result
        """
        pack_path = Path(pack_path)

        logger.info(f"Installing pack from: {pack_path}")

        try:
            # Extract or copy pack to temp directory
            temp_pack_dir = self._prepare_pack(pack_path)

            # Read and validate manifest
            manifest_path = temp_pack_dir / "manifest.json"
            if not manifest_path.exists():
                raise FileNotFoundError(f"Pack missing manifest.json: {pack_path}")

            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            # Verify pack if requested
            if verify:
                from .validator import PackValidator
                validator = PackValidator()
                if not validator.validate_pack(manifest):
                    raise ValueError("Pack validation failed")

            # Check dependencies
            if not self._check_dependencies(manifest):
                raise ValueError("Pack dependencies not satisfied")

            # Install pack
            pack_id = manifest["id"]
            install_path = self.install_base / pack_id

            # Backup existing installation
            if backup_existing and install_path.exists():
                self._backup_pack(install_path)

            # Perform installation
            self._install_pack_files(temp_pack_dir, install_path, manifest)

            # Register pack
            from .registry import get_pack_registry
            registry = get_pack_registry()
            registry.register_pack(manifest, install_path)

            # Cleanup temp files
            shutil.rmtree(temp_pack_dir)

            result = {
                "success": True,
                "pack_id": pack_id,
                "install_path": str(install_path),
                "manifest": manifest,
                "installed_at": datetime.now().isoformat()
            }

            logger.info(f"Pack installed successfully: {pack_id}")
            return result

        except Exception as e:
            logger.error(f"Pack installation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "pack_path": str(pack_path)
            }

    def update_pack(self,
                   pack_id: str,
                   new_pack_path: Union[str, Path],
                   keep_backup: bool = True) -> Dict[str, Any]:
        """
        Update an existing pack.

        Args:
            pack_id: ID of pack to update
            new_pack_path: Path to new pack version
            keep_backup: Whether to keep backup of old version

        Returns:
            Update result
        """
        logger.info(f"Updating pack: {pack_id}")

        try:
            # Check if pack is currently installed
            from .registry import get_pack_registry
            registry = get_pack_registry()
            current_pack = registry.get_pack(pack_id)

            if not current_pack:
                raise ValueError(f"Pack not installed: {pack_id}")

            # Install new version
            install_result = self.install_pack(new_pack_path, verify=True, backup_existing=keep_backup)

            if not install_result["success"]:
                raise ValueError(f"New pack installation failed: {install_result.get('error', 'Unknown error')}")

            # Mark old version as inactive
            registry.unregister_pack(pack_id)

            # Update registry with new version
            new_manifest = install_result["manifest"]
            registry.register_pack(new_manifest, Path(install_result["install_path"]))

            result = {
                "success": True,
                "pack_id": pack_id,
                "old_version": current_pack["version"],
                "new_version": new_manifest["version"],
                "updated_at": datetime.now().isoformat()
            }

            logger.info(f"Pack updated successfully: {pack_id} ({current_pack['version']} -> {new_manifest['version']})")
            return result

        except Exception as e:
            logger.error(f"Pack update failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "pack_id": pack_id
            }

    def uninstall_pack(self, pack_id: str, remove_files: bool = True) -> Dict[str, Any]:
        """
        Uninstall a pack.

        Args:
            pack_id: ID of pack to uninstall
            remove_files: Whether to remove pack files

        Returns:
            Uninstall result
        """
        logger.info(f"Uninstalling pack: {pack_id}")

        try:
            # Get pack info
            from .registry import get_pack_registry
            registry = get_pack_registry()
            pack_info = registry.get_pack(pack_id)

            if not pack_info:
                raise ValueError(f"Pack not found: {pack_id}")

            # Remove files if requested
            if remove_files:
                install_path = self.install_base / pack_id
                if install_path.exists():
                    shutil.rmtree(install_path)
                    logger.info(f"Removed pack files: {install_path}")

            # Unregister pack
            registry.unregister_pack(pack_id)

            result = {
                "success": True,
                "pack_id": pack_id,
                "files_removed": remove_files,
                "uninstalled_at": datetime.now().isoformat()
            }

            logger.info(f"Pack uninstalled successfully: {pack_id}")
            return result

        except Exception as e:
            logger.error(f"Pack uninstallation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "pack_id": pack_id
            }

    def _prepare_pack(self, pack_path: Path) -> Path:
        """Prepare pack for installation (extract if needed)."""
        if pack_path.is_file() and pack_path.suffix == '.zip':
            # Extract ZIP file
            temp_dir = self.temp_dir / f"extract_{pack_path.stem}_{datetime.now().strftime('%H%M%S')}"
            temp_dir.mkdir(exist_ok=True)

            with zipfile.ZipFile(pack_path, 'r') as zf:
                zf.extractall(temp_dir)

            return temp_dir

        elif pack_path.is_dir():
            # Copy directory to temp
            temp_dir = self.temp_dir / f"copy_{pack_path.name}_{datetime.now().strftime('%H%M%S')}"
            shutil.copytree(pack_path, temp_dir)
            return temp_dir

        else:
            raise ValueError(f"Invalid pack path: {pack_path}")

    def _check_dependencies(self, manifest: Dict[str, Any]) -> bool:
        """Check if pack dependencies are satisfied."""
        dependencies = manifest.get("dependencies", [])

        if not dependencies:
            return True

        from .registry import get_pack_registry
        registry = get_pack_registry()

        for dep in dependencies:
            dep_name = dep["name"]
            dep_version = dep["version"]
            dep_type = dep.get("type")

            # Check if dependency is installed
            installed_packs = registry.list_packs(pack_type=dep_type)
            found = False

            for pack in installed_packs:
                if pack["name"] == dep_name and pack["version"] == dep_version:
                    found = True
                    break

            if not found:
                logger.error(f"Missing dependency: {dep_name} v{dep_version}")
                return False

        return True

    def _backup_pack(self, install_path: Path):
        """Create backup of existing pack installation."""
        backup_dir = install_path.parent / "backups"
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"{install_path.name}_backup_{timestamp}"

        shutil.copytree(install_path, backup_path)
        logger.info(f"Created backup: {backup_path}")

    def _install_pack_files(self,
                           source_dir: Path,
                           install_path: Path,
                           manifest: Dict[str, Any]):
        """Install pack files to installation directory."""
        # Create install directory
        install_path.mkdir(parents=True, exist_ok=True)

        # Copy manifest
        shutil.copy2(source_dir / "manifest.json", install_path / "manifest.json")

        # Copy content directory if it exists
        content_dir = source_dir / "content"
        if content_dir.exists():
            install_content_dir = install_path / "content"
            if install_content_dir.exists():
                shutil.rmtree(install_content_dir)
            shutil.copytree(content_dir, install_content_dir)

        # Copy previews directory if it exists
        previews_dir = source_dir / "previews"
        if previews_dir.exists():
            install_previews_dir = install_path / "previews"
            if install_previews_dir.exists():
                shutil.rmtree(install_previews_dir)
            shutil.copytree(previews_dir, install_previews_dir)

        logger.info(f"Installed pack files to: {install_path}")

    def get_installation_status(self, pack_id: str) -> Dict[str, Any]:
        """
        Get installation status of a pack.

        Args:
            pack_id: Pack ID

        Returns:
            Installation status
        """
        install_path = self.install_base / pack_id

        if not install_path.exists():
            return {
                "installed": False,
                "pack_id": pack_id
            }

        manifest_path = install_path / "manifest.json"
        if not manifest_path.exists():
            return {
                "installed": True,
                "valid": False,
                "pack_id": pack_id,
                "error": "Missing manifest.json"
            }

        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            # Check if registered
            from .registry import get_pack_registry
            registry = get_pack_registry()
            registered_pack = registry.get_pack(pack_id)

            return {
                "installed": True,
                "valid": True,
                "pack_id": pack_id,
                "version": manifest.get("version"),
                "registered": registered_pack is not None,
                "install_path": str(install_path)
            }

        except Exception as e:
            return {
                "installed": True,
                "valid": False,
                "pack_id": pack_id,
                "error": str(e)
            }

    def cleanup_temp_files(self, max_age_hours: int = 24):
        """
        Clean up old temporary files.

        Args:
            max_age_hours: Maximum age of temp files to keep
        """
        import time

        current_time = time.time()
        max_age_seconds = max_age_hours * 60 * 60

        cleaned_count = 0
        for temp_item in self.temp_dir.iterdir():
            if temp_item.is_dir():
                item_age = current_time - temp_item.stat().st_mtime
                if item_age > max_age_seconds:
                    try:
                        shutil.rmtree(temp_item)
                        cleaned_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to remove temp dir {temp_item}: {e}")

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} temporary directories")


# Convenience functions
def install_pack(pack_path: Union[str, Path],
                verify: bool = True,
                backup_existing: bool = True) -> Dict[str, Any]:
    """
    Convenience function to install a pack.

    Args:
        pack_path: Path to pack file or directory
        verify: Whether to verify pack integrity
        backup_existing: Whether to backup existing installation

    Returns:
        Installation result
    """
    installer = PackInstaller()
    return installer.install_pack(pack_path, verify, backup_existing)


def update_pack(pack_id: str,
               new_pack_path: Union[str, Path],
               keep_backup: bool = True) -> Dict[str, Any]:
    """
    Convenience function to update a pack.

    Args:
        pack_id: ID of pack to update
        new_pack_path: Path to new pack version
        keep_backup: Whether to keep backup of old version

    Returns:
        Update result
    """
    installer = PackInstaller()
    return installer.update_pack(pack_id, new_pack_path, keep_backup)