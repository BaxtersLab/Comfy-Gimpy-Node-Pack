"""
Icon Registry for Comfy Gimpy Studio GIMP Plugin.

Manages loading and caching of UI icons.
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class IconSize(Enum):
    """Standard icon sizes."""
    SMALL = 16
    MEDIUM = 24
    LARGE = 32
    XLARGE = 48


class ToolboxIcon(Enum):
    """Icons for different toolbox types."""
    TEMPLATES = "templates"
    STYLES = "styles"
    MODELS = "models"
    WORKFLOWS = "workflows"
    FUSION = "fusion"
    TASKS = "tasks"
    MARKETPLACE = "marketplace"
    SETTINGS = "settings"
    MOBILE_SYNC = "mobile_sync"

    # Action icons
    ADD = "add"
    REMOVE = "remove"
    EDIT = "edit"
    SAVE = "save"
    LOAD = "load"
    REFRESH = "refresh"
    SEARCH = "search"
    FILTER = "filter"

    # State icons
    EXPAND = "expand"
    COLLAPSE = "collapse"
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"
    CLOSE = "close"
    FLOAT = "float"
    DOCK = "dock"

    # Status icons
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PENDING = "pending"
    CANCELLED = "cancelled"


class IconRegistry:
    """Registry for managing UI icons."""

    def __init__(self, icon_dir: Optional[Path] = None):
        """
        Initialize the icon registry.

        Args:
            icon_dir: Directory containing icon files. If None, uses default.
        """
        if icon_dir is None:
            # Try to find icons relative to this file
            current_dir = Path(__file__).parent
            icon_dir = current_dir / "icons"

        self.icon_dir = icon_dir
        self._icon_cache: Dict[str, Any] = {}
        self._gimp_icons: Dict[str, Any] = {}

        # Ensure icon directory exists
        self.icon_dir.mkdir(parents=True, exist_ok=True)

        # Initialize GIMP icon mappings if GIMP is available
        self._init_gimp_icons()

    def _init_gimp_icons(self):
        """Initialize GIMP icon mappings."""
        try:
            import gimp
            from gimpenums import *

            # Map our icon names to GIMP stock icons
            self._gimp_icons = {
                ToolboxIcon.TEMPLATES.value: gimp.ICON_DOCUMENT_NEW,
                ToolboxIcon.STYLES.value: gimp.ICON_TOOL_PAINTBRUSH,
                ToolboxIcon.MODELS.value: gimp.ICON_TOOL_CLONE,
                ToolboxIcon.WORKFLOWS.value: gimp.ICON_TOOL_PATH,
                ToolboxIcon.FUSION.value: gimp.ICON_TOOL_BLUR,
                ToolboxIcon.TASKS.value: gimp.ICON_TOOL_ZOOM,
                ToolboxIcon.MARKETPLACE.value: gimp.ICON_TOOL_MOVE,
                ToolboxIcon.SETTINGS.value: gimp.ICON_PREFERENCES_SYSTEM,
                ToolboxIcon.MOBILE_SYNC.value: gimp.ICON_NETWORK_WIRELESS,

                ToolboxIcon.ADD.value: gimp.ICON_ADD,
                ToolboxIcon.REMOVE.value: gimp.ICON_REMOVE,
                ToolboxIcon.EDIT.value: gimp.ICON_EDIT,
                ToolboxIcon.SAVE.value: gimp.ICON_SAVE,
                ToolboxIcon.LOAD.value: gimp.ICON_OPEN,
                ToolboxIcon.REFRESH.value: gimp.ICON_REFRESH,
                ToolboxIcon.SEARCH.value: gimp.ICON_SEARCH,
                ToolboxIcon.FILTER.value: gimp.ICON_TOOL_COLOR_PICKER,

                ToolboxIcon.EXPAND.value: gimp.ICON_GO_DOWN,
                ToolboxIcon.COLLAPSE.value: gimp.ICON_GO_UP,
                ToolboxIcon.MINIMIZE.value: gimp.ICON_ZOOM_OUT,
                ToolboxIcon.MAXIMIZE.value: gimp.ICON_ZOOM_IN,
                ToolboxIcon.CLOSE.value: gimp.ICON_CLOSE,
                ToolboxIcon.FLOAT.value: gimp.ICON_TOOL_MOVE,
                ToolboxIcon.DOCK.value: gimp.ICON_ANCHOR,

                ToolboxIcon.RUNNING.value: gimp.ICON_EXECUTING,
                ToolboxIcon.COMPLETED.value: gimp.ICON_YES,
                ToolboxIcon.FAILED.value: gimp.ICON_NO,
                ToolboxIcon.PENDING.value: gimp.ICON_GO_NEXT,
                ToolboxIcon.CANCELLED.value: gimp.ICON_STOP,
            }

            logger.debug("GIMP icons initialized")

        except ImportError:
            logger.debug("GIMP not available, using fallback icons")
            self._gimp_icons = {}

    def get_icon(self, icon: ToolboxIcon, size: IconSize = IconSize.MEDIUM) -> Any:
        """
        Get an icon by name and size.

        Args:
            icon: The icon to retrieve
            size: The desired icon size

        Returns:
            Icon object (GIMP stock icon or custom icon)
        """
        icon_name = icon.value
        cache_key = f"{icon_name}_{size.value}"

        # Check cache first
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]

        # Try GIMP stock icon first
        if icon_name in self._gimp_icons:
            icon_obj = self._gimp_icons[icon_name]
            self._icon_cache[cache_key] = icon_obj
            return icon_obj

        # Try to load custom icon file
        icon_obj = self._load_custom_icon(icon_name, size)
        if icon_obj is not None:
            self._icon_cache[cache_key] = icon_obj
            return icon_obj

        # Fallback to text-based icon representation
        icon_obj = self._create_fallback_icon(icon_name, size)
        self._icon_cache[cache_key] = icon_obj
        return icon_obj

    def _load_custom_icon(self, icon_name: str, size: IconSize) -> Optional[Any]:
        """
        Load a custom icon file.

        Args:
            icon_name: Name of the icon
            size: Size of the icon

        Returns:
            Icon object if loaded, None otherwise
        """
        # Try different file extensions
        extensions = ['.png', '.svg', '.ico']

        for ext in extensions:
            icon_file = self.icon_dir / f"{icon_name}_{size.value}{ext}"
            if icon_file.exists():
                try:
                    # For now, return the file path as a placeholder
                    # In a real implementation, this would load the image
                    return str(icon_file)
                except Exception as e:
                    logger.debug(f"Failed to load icon {icon_file}: {e}")

        return None

    def _create_fallback_icon(self, icon_name: str, size: IconSize) -> str:
        """
        Create a fallback text-based icon representation.

        Args:
            icon_name: Name of the icon
            size: Size of the icon

        Returns:
            Text representation of the icon
        """
        # Create a simple text-based icon using the first letter
        first_letter = icon_name[0].upper() if icon_name else "?"

        # Return a formatted string as fallback
        return f"[{first_letter}]"

    def get_toolbox_icon(self, toolbox_type: str, size: IconSize = IconSize.MEDIUM) -> Any:
        """
        Get the icon for a toolbox type.

        Args:
            toolbox_type: Type of toolbox
            size: Size of the icon

        Returns:
            Icon object for the toolbox
        """
        try:
            icon = ToolboxIcon(toolbox_type)
            return self.get_icon(icon, size)
        except ValueError:
            logger.warning(f"Unknown toolbox type: {toolbox_type}")
            return self.get_icon(ToolboxIcon.SETTINGS, size)

    def get_action_icon(self, action: str, size: IconSize = IconSize.SMALL) -> Any:
        """
        Get the icon for an action.

        Args:
            action: Action name
            size: Size of the icon

        Returns:
            Icon object for the action
        """
        try:
            icon = ToolboxIcon(action)
            return self.get_icon(icon, size)
        except ValueError:
            logger.warning(f"Unknown action: {action}")
            return self.get_icon(ToolboxIcon.ADD, size)

    def get_status_icon(self, status: str, size: IconSize = IconSize.SMALL) -> Any:
        """
        Get the icon for a status.

        Args:
            status: Status name
            size: Size of the icon

        Returns:
            Icon object for the status
        """
        try:
            icon = ToolboxIcon(status)
            return self.get_icon(icon, size)
        except ValueError:
            logger.warning(f"Unknown status: {status}")
            return self.get_icon(ToolboxIcon.PENDING, size)

    def preload_icons(self, icons: list[ToolboxIcon], size: IconSize = IconSize.MEDIUM):
        """
        Preload a set of icons into cache.

        Args:
            icons: List of icons to preload
            size: Size to preload
        """
        for icon in icons:
            self.get_icon(icon, size)

    def clear_cache(self):
        """Clear the icon cache."""
        self._icon_cache.clear()
        logger.debug("Icon cache cleared")

    def get_available_icons(self) -> list[str]:
        """Get list of available icon names."""
        return [icon.value for icon in ToolboxIcon]