# gimp_comfy_bridge/extensions/loader.py

"""
Extension Loader System

Handles loading, unloading, and hot-reloading of extensions.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
import importlib
import sys

from .registry import ExtensionRegistry
from .manifest import ExtensionManifest

logger = logging.getLogger(__name__)

class ExtensionLoader:
    """Loader for extensions with hot-reload support."""

    def __init__(self, registry: ExtensionRegistry):
        self.registry = registry
        self._watch_tasks: Dict[str, asyncio.Task] = {}
        self._file_watchers: Dict[str, Dict[Path, float]] = {}
        self._hot_reload_enabled = True

    def load_builtin_extensions(self) -> int:
        """Load built-in extensions."""
        loaded_count = 0

        builtin_path = Path(__file__).parent / "builtin"
        if not builtin_path.exists():
            logger.info("No builtin extensions directory found")
            return 0

        for ext_dir in builtin_path.iterdir():
            if not ext_dir.is_dir():
                continue

            manifest_path = ext_dir / "manifest.json"
            if not manifest_path.exists():
                continue

            try:
                manifest = ExtensionManifest.from_file(manifest_path)
                self.registry.register_extension(manifest, ext_dir)
                self.registry.load_extension(manifest.extension_id)
                loaded_count += 1
                logger.info(f"Loaded builtin extension: {manifest.extension_id}")

            except Exception as e:
                logger.error(f"Failed to load builtin extension {ext_dir.name}: {e}")

        return loaded_count

    def load_user_extensions(self) -> int:
        """Load user-installed extensions."""
        loaded_count = 0

        # Discover extensions
        discovered = self.registry.discover_extensions()

        for manifest in discovered:
            try:
                # Skip if already registered
                if manifest.extension_id in self.registry.list_extensions():
                    continue

                # Register and load
                ext_path = manifest._manifest_path.parent
                self.registry.register_extension(manifest, ext_path)

                if self.registry.load_extension(manifest.extension_id):
                    loaded_count += 1
                    logger.info(f"Loaded user extension: {manifest.extension_id}")

                    # Start watching for changes if hot reload enabled
                    if self._hot_reload_enabled:
                        self._start_watching(manifest.extension_id)

            except Exception as e:
                logger.error(f"Failed to load user extension {manifest.name}: {e}")

        return loaded_count

    def unload_extension(self, extension_id: str) -> bool:
        """Unload an extension."""
        # Stop watching
        self._stop_watching(extension_id)

        # Unload from registry
        return self.registry.unload_extension(extension_id)

    def reload_extension(self, extension_id: str) -> bool:
        """Reload an extension."""
        logger.info(f"Reloading extension: {extension_id}")

        # Unload
        if not self.unload_extension(extension_id):
            logger.error(f"Failed to unload extension: {extension_id}")
            return False

        # Small delay to ensure cleanup
        time.sleep(0.1)

        # Load again
        if self.registry.load_extension(extension_id):
            logger.info(f"Successfully reloaded extension: {extension_id}")

            # Restart watching
            if self._hot_reload_enabled:
                self._start_watching(extension_id)

            return True
        else:
            logger.error(f"Failed to reload extension: {extension_id}")
            return False

    def install_extension(self, extension_path: Path) -> Optional[str]:
        """Install an extension from a directory."""
        manifest_path = extension_path / "manifest.json"
        if not manifest_path.exists():
            raise ValueError(f"No manifest.json found in {extension_path}")

        try:
            manifest = ExtensionManifest.from_file(manifest_path)

            # Copy to user extensions directory
            user_ext_dir = Path.home() / ".comfy_gimpy" / "extensions"
            user_ext_dir.mkdir(parents=True, exist_ok=True)

            target_dir = user_ext_dir / manifest.extension_id
            if target_dir.exists():
                # Remove existing
                import shutil
                shutil.rmtree(target_dir)

            # Copy extension
            shutil.copytree(extension_path, target_dir)

            # Register and load
            self.registry.register_extension(manifest, target_dir)
            if self.registry.load_extension(manifest.extension_id):
                logger.info(f"Installed extension: {manifest.extension_id}")
                return manifest.extension_id
            else:
                # Cleanup on failure
                shutil.rmtree(target_dir)
                return None

        except Exception as e:
            logger.error(f"Failed to install extension: {e}")
            return None

    def uninstall_extension(self, extension_id: str) -> bool:
        """Uninstall an extension."""
        info = self.registry.get_extension_info(extension_id)
        if not info:
            return False

        # Unload first
        self.unload_extension(extension_id)

        # Remove from registry
        self.registry.unregister_extension(extension_id)

        # Remove files
        try:
            import shutil
            shutil.rmtree(info.path)
            logger.info(f"Uninstalled extension: {extension_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove extension files: {e}")
            return False

    def enable_hot_reload(self, enabled: bool = True) -> None:
        """Enable or disable hot reload."""
        self._hot_reload_enabled = enabled

        if enabled:
            # Start watching all loaded extensions
            for ext_id in self.registry.list_loaded_extensions():
                self._start_watching(ext_id)
        else:
            # Stop watching all
            for ext_id in list(self._watch_tasks.keys()):
                self._stop_watching(ext_id)

    def _start_watching(self, extension_id: str) -> None:
        """Start watching an extension for changes."""
        if extension_id in self._watch_tasks:
            return

        info = self.registry.get_extension_info(extension_id)
        if not info:
            return

        # Initialize file timestamps
        self._file_watchers[extension_id] = {}
        self._scan_extension_files(extension_id)

        # Start watch task
        task = asyncio.create_task(self._watch_extension(extension_id))
        self._watch_tasks[extension_id] = task

        logger.debug(f"Started watching extension: {extension_id}")

    def _stop_watching(self, extension_id: str) -> None:
        """Stop watching an extension."""
        if extension_id in self._watch_tasks:
            self._watch_tasks[extension_id].cancel()
            del self._watch_tasks[extension_id]

        if extension_id in self._file_watchers:
            del self._file_watchers[extension_id]

        logger.debug(f"Stopped watching extension: {extension_id}")

    async def _watch_extension(self, extension_id: str) -> None:
        """Watch an extension for file changes."""
        try:
            while True:
                await asyncio.sleep(1.0)  # Check every second

                if not self._has_changes(extension_id):
                    continue

                logger.info(f"Detected changes in extension: {extension_id}")

                # Reload extension
                if self.reload_extension(extension_id):
                    # Rescan files
                    self._scan_extension_files(extension_id)
                else:
                    logger.error(f"Failed to reload extension: {extension_id}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error watching extension {extension_id}: {e}")

    def _scan_extension_files(self, extension_id: str) -> None:
        """Scan extension files and record timestamps."""
        info = self.registry.get_extension_info(extension_id)
        if not info:
            return

        watchers = self._file_watchers[extension_id]

        # Clear existing
        watchers.clear()

        # Scan Python files
        for py_file in info.path.rglob("*.py"):
            watchers[py_file] = py_file.stat().st_mtime

        # Scan manifest
        manifest_file = info.path / "manifest.json"
        if manifest_file.exists():
            watchers[manifest_file] = manifest_file.stat().st_mtime

    def _has_changes(self, extension_id: str) -> bool:
        """Check if extension files have changed."""
        if extension_id not in self._file_watchers:
            return False

        watchers = self._file_watchers[extension_id]

        for file_path, last_mtime in watchers.items():
            if not file_path.exists():
                return True  # File deleted

            current_mtime = file_path.stat().st_mtime
            if current_mtime > last_mtime:
                return True  # File modified

        return False

    def get_extension_status(self, extension_id: str) -> Dict[str, Any]:
        """Get detailed status of an extension."""
        info = self.registry.get_extension_info(extension_id)
        if not info:
            return {"status": "not_found"}

        return {
            "extension_id": extension_id,
            "enabled": info.enabled,
            "loaded": info.loaded,
            "path": str(info.path),
            "manifest": info.manifest.to_dict(),
            "watching": extension_id in self._watch_tasks,
            "capabilities": info.capabilities,
            "hooks": list(info.hooks.keys())
        }

    def list_extension_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all extensions."""
        status = {}
        for ext_id in self.registry.list_extensions():
            status[ext_id] = self.get_extension_status(ext_id)
        return status