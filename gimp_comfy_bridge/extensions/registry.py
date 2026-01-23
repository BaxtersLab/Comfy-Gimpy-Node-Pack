# gimp_comfy_bridge/extensions/registry.py

"""
Extension Registry System

Manages extension registration, discovery, and lifecycle.
"""

import asyncio
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
import json
import logging
from dataclasses import dataclass, field

from .manifest import ExtensionManifest
from .permissions import PermissionManager
from .sandbox import ExtensionSandbox

logger = logging.getLogger(__name__)

@dataclass
class ExtensionInfo:
    """Information about a loaded extension."""

    manifest: ExtensionManifest
    path: Path
    enabled: bool = True
    loaded: bool = False
    sandbox: Optional[ExtensionSandbox] = None
    module: Optional[Any] = None
    hooks: Dict[str, List[callable]] = field(default_factory=dict)
    capabilities: Dict[str, Any] = field(default_factory=dict)

class ExtensionRegistry:
    """Registry for managing extensions."""

    def __init__(self):
        self._extensions: Dict[str, ExtensionInfo] = {}
        self._permission_manager = PermissionManager()
        self._extension_paths: List[Path] = []
        self._builtin_extensions_path: Optional[Path] = None

        # Setup default extension paths
        self._setup_extension_paths()

    def _setup_extension_paths(self) -> None:
        """Setup default extension search paths."""
        # User extensions directory
        user_extensions = Path.home() / ".comfy_gimpy" / "extensions"
        self._extension_paths.append(user_extensions)

        # Built-in extensions
        builtin_path = Path(__file__).parent / "builtin"
        self._builtin_extensions_path = builtin_path
        self._extension_paths.append(builtin_path)

        # Create directories if they don't exist
        for path in self._extension_paths:
            path.mkdir(parents=True, exist_ok=True)

    def register_extension(self, manifest: ExtensionManifest, path: Path) -> str:
        """Register an extension."""
        extension_id = manifest.extension_id

        if extension_id in self._extensions:
            raise ValueError(f"Extension {extension_id} already registered")

        # Validate manifest
        errors = manifest.validate()
        if errors:
            raise ValueError(f"Invalid manifest for {extension_id}: {errors}")

        # Create extension info
        info = ExtensionInfo(
            manifest=manifest,
            path=path,
            sandbox=ExtensionSandbox(extension_id, manifest.permissions)
        )

        self._extensions[extension_id] = info

        # Grant permissions
        self._permission_manager.grant_permissions(extension_id, manifest.permissions)

        logger.info(f"Registered extension: {extension_id}")
        return extension_id

    def unregister_extension(self, extension_id: str) -> None:
        """Unregister an extension."""
        if extension_id not in self._extensions:
            return

        info = self._extensions[extension_id]

        # Unload if loaded
        if info.loaded:
            self.unload_extension(extension_id)

        # Revoke permissions
        self._permission_manager.clear_permissions(extension_id)

        # Remove from registry
        del self._extensions[extension_id]

        logger.info(f"Unregistered extension: {extension_id}")

    def load_extension(self, extension_id: str) -> bool:
        """Load an extension."""
        if extension_id not in self._extensions:
            raise ValueError(f"Extension {extension_id} not registered")

        info = self._extensions[extension_id]

        if info.loaded:
            return True

        if not info.enabled:
            return False

        try:
            # Load main module
            main_module_path = info.path / info.manifest.main_module
            if main_module_path.exists():
                info.module = info.sandbox.load_module(str(main_module_path))
            else:
                # Create minimal module
                import types
                info.module = types.ModuleType(f'extension_{extension_id}')

            # Initialize extension
            if hasattr(info.module, 'initialize'):
                info.sandbox.execute_function(info.module.initialize, self)

            # Register capabilities
            self._register_capabilities(extension_id, info)

            # Register hooks
            self._register_hooks(extension_id, info)

            info.loaded = True
            logger.info(f"Loaded extension: {extension_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to load extension {extension_id}: {e}")
            return False

    def unload_extension(self, extension_id: str) -> bool:
        """Unload an extension."""
        if extension_id not in self._extensions:
            return False

        info = self._extensions[extension_id]

        if not info.loaded:
            return True

        try:
            # Call cleanup function
            if hasattr(info.module, 'cleanup'):
                info.sandbox.execute_function(info.module.cleanup)

            # Unregister hooks
            self._unregister_hooks(extension_id, info)

            # Unregister capabilities
            self._unregister_capabilities(extension_id, info)

            info.module = None
            info.loaded = False

            logger.info(f"Unloaded extension: {extension_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to unload extension {extension_id}: {e}")
            return False

    def enable_extension(self, extension_id: str) -> bool:
        """Enable an extension."""
        if extension_id not in self._extensions:
            return False

        info = self._extensions[extension_id]
        if info.enabled:
            return True

        info.enabled = True
        logger.info(f"Enabled extension: {extension_id}")
        return True

    def disable_extension(self, extension_id: str) -> bool:
        """Disable an extension."""
        if extension_id not in self._extensions:
            return False

        info = self._extensions[extension_id]
        if not info.enabled:
            return True

        # Unload if loaded
        if info.loaded:
            self.unload_extension(extension_id)

        info.enabled = False
        logger.info(f"Disabled extension: {extension_id}")
        return True

    def get_extension_info(self, extension_id: str) -> Optional[ExtensionInfo]:
        """Get extension information."""
        return self._extensions.get(extension_id)

    def list_extensions(self) -> List[str]:
        """List all registered extensions."""
        return list(self._extensions.keys())

    def list_enabled_extensions(self) -> List[str]:
        """List enabled extensions."""
        return [eid for eid, info in self._extensions.items() if info.enabled]

    def list_loaded_extensions(self) -> List[str]:
        """List loaded extensions."""
        return [eid for eid, info in self._extensions.items() if info.loaded]

    def discover_extensions(self) -> List[ExtensionManifest]:
        """Discover extensions in search paths."""
        discovered = []

        for search_path in self._extension_paths:
            if not search_path.exists():
                continue

            for ext_dir in search_path.iterdir():
                if not ext_dir.is_dir():
                    continue

                manifest_path = ext_dir / "manifest.json"
                if not manifest_path.exists():
                    continue

                try:
                    manifest = ExtensionManifest.from_file(manifest_path)
                    discovered.append(manifest)
                except Exception as e:
                    logger.warning(f"Failed to load manifest from {manifest_path}: {e}")

        return discovered

    def call_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """Call a hook across all loaded extensions."""
        results = []

        for extension_id, info in self._extensions.items():
            if not info.loaded or not info.enabled:
                continue

            hook_funcs = info.hooks.get(hook_name, [])
            for hook_func in hook_funcs:
                try:
                    result = info.sandbox.execute_function(hook_func, *args, **kwargs)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Hook {hook_name} failed for {extension_id}: {e}")

        return results

    def get_capabilities(self, capability_type: str) -> Dict[str, Any]:
        """Get all capabilities of a specific type."""
        capabilities = {}

        for extension_id, info in self._extensions.items():
            if not info.loaded or not info.enabled:
                continue

            ext_caps = info.capabilities.get(capability_type, {})
            capabilities[extension_id] = ext_caps

        return capabilities

    def _register_capabilities(self, extension_id: str, info: ExtensionInfo) -> None:
        """Register extension capabilities."""
        manifest = info.manifest

        # UI panels
        if manifest.ui_panels:
            info.capabilities['ui_panels'] = manifest.ui_panels

        # Workflows
        if manifest.workflows:
            info.capabilities['workflows'] = manifest.workflows

        # Asset types
        if manifest.asset_types:
            info.capabilities['asset_types'] = manifest.asset_types

        # Template generators
        if manifest.template_generators:
            info.capabilities['template_generators'] = manifest.template_generators

        # Copywriting modules
        if manifest.copywriting_modules:
            info.capabilities['copywriting_modules'] = manifest.copywriting_modules

        # Brand kit tools
        if manifest.brand_kit_tools:
            info.capabilities['brand_kit_tools'] = manifest.brand_kit_tools

        # Layout heuristics
        if manifest.layout_heuristics:
            info.capabilities['layout_heuristics'] = manifest.layout_heuristics

    def _unregister_capabilities(self, extension_id: str, info: ExtensionInfo) -> None:
        """Unregister extension capabilities."""
        info.capabilities.clear()

    def _register_hooks(self, extension_id: str, info: ExtensionInfo) -> None:
        """Register extension hooks."""
        if not info.module:
            return

        # Look for hook functions
        hook_prefixes = ['on_', 'hook_', 'pre_', 'post_']

        for attr_name in dir(info.module):
            if any(attr_name.startswith(prefix) for prefix in hook_prefixes):
                attr = getattr(info.module, attr_name)
                if callable(attr):
                    hook_name = attr_name
                    if hook_name not in info.hooks:
                        info.hooks[hook_name] = []
                    info.hooks[hook_name].append(attr)

    def _unregister_hooks(self, extension_id: str, info: ExtensionInfo) -> None:
        """Unregister extension hooks."""
        info.hooks.clear()

    def save_state(self, path: Path) -> None:
        """Save registry state."""
        state = {
            'extensions': {}
        }

        for ext_id, info in self._extensions.items():
            state['extensions'][ext_id] = {
                'enabled': info.enabled,
                'path': str(info.path)
            }

        with open(path, 'w') as f:
            json.dump(state, f, indent=2)

    def load_state(self, path: Path) -> None:
        """Load registry state."""
        if not path.exists():
            return

        with open(path, 'r') as f:
            state = json.load(f)

        # Restore enabled/disabled state
        for ext_id, ext_state in state.get('extensions', {}).items():
            if ext_id in self._extensions:
                self._extensions[ext_id].enabled = ext_state.get('enabled', True)