# gimp_comfy_bridge/extensions/__init__.py

"""
Plugin Ecosystem + Extension API for Comfy Gimpy Studio

This module provides a comprehensive extension system that allows third-party
developers to extend Comfy Gimpy Studio with new workflows, UI panels, asset
types, template generators, copywriting modules, brand kit tools, and layout
optimization heuristics.

Key Features:
- Extension manifest format with metadata and permissions
- Sandboxed execution environment for security
- Hot-reload support for development
- UI injection capabilities
- Asset and workflow registration
- Marketplace integration
"""

from .api import ExtensionAPI
from .loader import ExtensionLoader
from .registry import ExtensionRegistry
from .sandbox import ExtensionSandbox
from .permissions import PermissionManager
from .manifest import ExtensionManifest

__all__ = [
    'ExtensionAPI',
    'ExtensionLoader',
    'ExtensionRegistry',
    'ExtensionSandbox',
    'PermissionManager',
    'ExtensionManifest'
]

# Global extension registry instance
_extension_registry = None
_extension_loader = None

def get_extension_registry():
    """Get the global extension registry instance."""
    global _extension_registry
    if _extension_registry is None:
        _extension_registry = ExtensionRegistry()
    return _extension_registry

def get_extension_loader():
    """Get the global extension loader instance."""
    global _extension_loader
    if _extension_loader is None:
        _extension_loader = ExtensionLoader(get_extension_registry())
    return _extension_loader

def initialize_extensions():
    """Initialize the extension system."""
    registry = get_extension_registry()
    loader = get_extension_loader()

    # Load built-in extensions
    loader.load_builtin_extensions()

    # Load user extensions
    loader.load_user_extensions()

    return registry, loader