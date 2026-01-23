"""
Layout Management for Comfy Gimpy Studio GIMP Plugin.

Provides utilities for consistent spacing, sizing, and layout.
"""

import logging
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Spacing:
    """Spacing configuration."""
    tiny: int = 2
    small: int = 4
    medium: int = 8
    large: int = 16
    xlarge: int = 24
    xxlarge: int = 32


@dataclass
class BorderRadius:
    """Border radius configuration."""
    small: int = 2
    medium: int = 4
    large: int = 8
    xlarge: int = 12
    round: int = 999  # Effectively round


@dataclass
class FontSize:
    """Font size configuration."""
    tiny: int = 8
    small: int = 10
    medium: int = 12
    large: int = 14
    xlarge: int = 16
    xxlarge: int = 20


@dataclass
class LayoutConfig:
    """Complete layout configuration."""
    spacing: Spacing
    border_radius: BorderRadius
    font_size: FontSize
    dark_mode: bool = True
    compact_mode: bool = False

    # Color scheme
    background_color: str = "#2d2d2d"
    foreground_color: str = "#ffffff"
    accent_color: str = "#007acc"
    border_color: str = "#404040"
    hover_color: str = "#3c3c3c"
    selected_color: str = "#007acc"

    # Component sizes
    toolbox_bar_width: int = 48
    toolbox_bar_height: int = 400
    toolbox_panel_width: int = 280
    toolbox_panel_max_height: int = 600
    floating_panel_min_width: int = 200
    floating_panel_min_height: int = 150

    # Animation settings
    animation_duration: int = 200  # milliseconds
    expand_collapse_duration: int = 150

    def __post_init__(self):
        if self.dark_mode:
            self._set_dark_theme()
        else:
            self._set_light_theme()

        if self.compact_mode:
            self._set_compact_mode()

    def _set_dark_theme(self):
        """Set dark theme colors."""
        self.background_color = "#2d2d2d"
        self.foreground_color = "#ffffff"
        self.accent_color = "#007acc"
        self.border_color = "#404040"
        self.hover_color = "#3c3c3c"
        self.selected_color = "#007acc"

    def _set_light_theme(self):
        """Set light theme colors."""
        self.background_color = "#f5f5f5"
        self.foreground_color = "#000000"
        self.accent_color = "#0066cc"
        self.border_color = "#cccccc"
        self.hover_color = "#e6e6e6"
        self.selected_color = "#0066cc"

    def _set_compact_mode(self):
        """Adjust settings for compact mode."""
        self.spacing = Spacing(
            tiny=1, small=2, medium=4, large=8, xlarge=12, xxlarge=16
        )
        self.toolbox_bar_width = 40
        self.toolbox_panel_width = 240


class LayoutManager:
    """Manages layout and styling for UI components."""

    def __init__(self, config: Optional[LayoutConfig] = None):
        """
        Initialize the layout manager.

        Args:
            config: Layout configuration. If None, uses defaults.
        """
        self.config = config or LayoutConfig()
        self._gimp_available = self._check_gimp_availability()

    def _check_gimp_availability(self) -> bool:
        """Check if GIMP UI libraries are available."""
        try:
            import gimp
            from gimpfu import *
            return True
        except ImportError:
            return False

    def get_spacing(self, size: str = "medium") -> int:
        """
        Get spacing value.

        Args:
            size: Size name ("tiny", "small", "medium", "large", "xlarge", "xxlarge")

        Returns:
            Spacing value in pixels
        """
        return getattr(self.config.spacing, size, self.config.spacing.medium)

    def get_border_radius(self, size: str = "medium") -> int:
        """
        Get border radius value.

        Args:
            size: Size name ("small", "medium", "large", "xlarge", "round")

        Returns:
            Border radius value in pixels
        """
        return getattr(self.config.border_radius, size, self.config.border_radius.medium)

    def get_font_size(self, size: str = "medium") -> int:
        """
        Get font size value.

        Args:
            size: Size name ("tiny", "small", "medium", "large", "xlarge", "xxlarge")

        Returns:
            Font size value in points
        """
        return getattr(self.config.font_size, size, self.config.font_size.medium)

    def get_color(self, color_type: str) -> str:
        """
        Get color value.

        Args:
            color_type: Color type name

        Returns:
            Color value as hex string
        """
        return getattr(self.config, f"{color_type}_color", self.config.background_color)

    def get_component_size(self, component: str, dimension: str) -> int:
        """
        Get component size.

        Args:
            component: Component name
            dimension: Dimension name ("width", "height", etc.)

        Returns:
            Size value in pixels
        """
        attr_name = f"{component}_{dimension}"
        return getattr(self.config, attr_name, 100)

    def create_gimp_container(self, container_type: str = "vbox", **kwargs) -> Any:
        """
        Create a GIMP UI container with consistent styling.

        Args:
            container_type: Type of container ("vbox", "hbox", "frame", etc.)
            **kwargs: Additional arguments for container creation

        Returns:
            GIMP container object
        """
        if not self._gimp_available:
            logger.warning("GIMP not available, cannot create container")
            return None

        try:
            import gimp
            from gimpfu import *

            # Apply consistent styling
            default_kwargs = {
                "border_width": self.get_spacing("small"),
                "spacing": self.get_spacing("small")
            }
            default_kwargs.update(kwargs)

            if container_type == "vbox":
                return gimp.ui.VBox(**default_kwargs)
            elif container_type == "hbox":
                return gimp.ui.HBox(**default_kwargs)
            elif container_type == "frame":
                frame = gimp.ui.Frame(**default_kwargs)
                frame.set_shadow_type(gimp.SHADOW_IN)
                return frame
            elif container_type == "scrolled_window":
                return gimp.ui.ScrolledWindow(**default_kwargs)
            else:
                logger.warning(f"Unknown container type: {container_type}")
                return None

        except Exception as e:
            logger.error(f"Failed to create GIMP container: {e}")
            return None

    def apply_theme_to_widget(self, widget: Any, widget_type: str = "default"):
        """
        Apply consistent theming to a widget.

        Args:
            widget: The widget to theme
            widget_type: Type of widget for specific styling
        """
        if not self._gimp_available:
            return

        try:
            # This would apply CSS-like styling in a real GIMP plugin
            # For now, we'll just log the intent
            logger.debug(f"Applying {widget_type} theme to widget")
        except Exception as e:
            logger.error(f"Failed to apply theme: {e}")

    def calculate_panel_size(self, content_width: int, content_height: int,
                           include_padding: bool = True) -> Tuple[int, int]:
        """
        Calculate appropriate panel size including padding.

        Args:
            content_width: Content width
            content_height: Content height
            include_padding: Whether to include padding

        Returns:
            Tuple of (width, height)
        """
        if include_padding:
            padding = self.get_spacing("medium") * 2
            width = min(content_width + padding, self.config.toolbox_panel_width)
            height = min(content_height + padding, self.config.toolbox_panel_max_height)
        else:
            width = min(content_width, self.config.toolbox_panel_width)
            height = min(content_height, self.config.toolbox_panel_max_height)

        return width, height

    def get_animation_settings(self) -> Dict[str, Any]:
        """
        Get animation settings for UI transitions.

        Returns:
            Dictionary of animation settings
        """
        return {
            "duration": self.config.animation_duration,
            "expand_duration": self.config.expand_collapse_duration,
            "easing": "ease-in-out"  # Would be used with CSS transitions
        }

    def update_theme(self, dark_mode: bool, compact_mode: bool = False):
        """
        Update the theme configuration.

        Args:
            dark_mode: Whether to use dark mode
            compact_mode: Whether to use compact mode
        """
        self.config.dark_mode = dark_mode
        self.config.compact_mode = compact_mode

        # Reinitialize to apply new settings
        old_config = self.config
        self.config = LayoutConfig(
            dark_mode=dark_mode,
            compact_mode=compact_mode
        )

        # Preserve custom sizes if they were set
        if hasattr(old_config, 'toolbox_bar_width'):
            self.config.toolbox_bar_width = old_config.toolbox_bar_width
        if hasattr(old_config, 'toolbox_panel_width'):
            self.config.toolbox_panel_width = old_config.toolbox_panel_width

        logger.info(f"Theme updated: dark_mode={dark_mode}, compact_mode={compact_mode}")

    def get_responsive_sizes(self, screen_width: int, screen_height: int) -> Dict[str, int]:
        """
        Get responsive sizes based on screen dimensions.

        Args:
            screen_width: Screen width
            screen_height: Screen height

        Returns:
            Dictionary of responsive sizes
        """
        # Scale down for smaller screens
        scale_factor = min(1.0, screen_width / 1920.0)

        return {
            "toolbox_bar_width": int(self.config.toolbox_bar_width * scale_factor),
            "toolbox_panel_width": int(self.config.toolbox_panel_width * scale_factor),
            "font_size_medium": max(10, int(self.config.font_size.medium * scale_factor)),
            "spacing_medium": max(4, int(self.config.spacing.medium * scale_factor))
        }