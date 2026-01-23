"""
Floating Panel for Comfy Gimpy Studio GIMP Plugin.

Provides draggable, resizable, dockable panels with close/minimize controls.
"""

import logging
from typing import Optional, Callable, Tuple, Any

from .state import UIStateManager, ToolboxType, ToolboxState
from .icons import IconRegistry, IconSize, ToolboxIcon
from .layout import LayoutManager

logger = logging.getLogger(__name__)


class FloatingPanel:
    """Floating/dockable toolbox panel."""

    def __init__(self,
                 toolbox_type: ToolboxType,
                 state_manager: UIStateManager,
                 icon_registry: IconRegistry,
                 layout_manager: LayoutManager,
                 initial_position: Optional[Tuple[int, int]] = None,
                 initial_size: Optional[Tuple[int, int]] = None):
        """
        Initialize a floating panel.

        Args:
            toolbox_type: Type of toolbox
            state_manager: UI state manager
            icon_registry: Icon registry
            layout_manager: Layout manager
            initial_position: Initial (x, y) position
            initial_size: Initial (width, height) size
        """
        self.toolbox_type = toolbox_type
        self.state_manager = state_manager
        self.icon_registry = icon_registry
        self.layout_manager = layout_manager

        self._gimp_available = self._check_gimp_availability()
        self._window = None
        self._content_area = None
        self._title_bar = None
        self._is_dragging = False
        self._drag_offset = (0, 0)
        self._is_docked = False

        # Position and size
        self.position = initial_position or (100, 100)
        self.size = initial_size or self._get_default_size()

        # Callbacks
        self.on_close: Optional[Callable[[], None]] = None
        self.on_minimize: Optional[Callable[[], None]] = None
        self.on_dock: Optional[Callable[[], None]] = None
        self.on_position_changed: Optional[Callable[[Tuple[int, int]], None]] = None
        self.on_size_changed: Optional[Callable[[Tuple[int, int]], None]] = None

        # Create UI
        self._create_ui()

    def _check_gimp_availability(self) -> bool:
        """Check if GIMP UI libraries are available."""
        try:
            import gimp
            return True
        except ImportError:
            return False

    def _get_default_size(self) -> Tuple[int, int]:
        """Get default panel size."""
        return (
            self.layout_manager.config.toolbox_panel_width,
            self.layout_manager.config.toolbox_panel_max_height // 2
        )

    def _create_ui(self):
        """Create the floating panel UI."""
        if not self._gimp_available:
            self._window = f"mock_floating_panel_{self.toolbox_type.value}"
            return

        try:
            import gimp
            from gimpfu import *

            # Create window
            self._window = gimp.ui.Window()
            self._window.set_title(f"{self.toolbox_type.value.title()} Toolbox")
            self._window.set_default_size(*self.size)
            self._window.move(*self.position)

            # Set window properties
            self._window.set_type_hint(gimp.WINDOW_TYPE_HINT_DIALOG)
            self._window.set_decorated(False)  # We'll create our own title bar

            # Create main container
            main_vbox = gimp.ui.VBox(spacing=0)
            self._window.add(main_vbox)

            # Create title bar
            self._title_bar = self._create_title_bar()
            main_vbox.pack_start(self._title_bar, expand=False, fill=False)

            # Create content area
            self._content_area = gimp.ui.Frame()
            self._content_area.set_shadow_type(gimp.SHADOW_IN)

            scrolled = gimp.ui.ScrolledWindow()
            scrolled.set_policy(gimp.POLICY_NEVER, gimp.POLICY_AUTOMATIC)
            scrolled.add_with_viewport(self._content_area)

            main_vbox.pack_start(scrolled, expand=True, fill=True)

            # Connect window signals
            self._window.connect("delete-event", self._on_window_delete)
            self._window.connect("configure-event", self._on_window_configure)

            # Apply styling
            self.layout_manager.apply_theme_to_widget(self._window, "floating_panel")

            logger.debug(f"Floating panel created for {self.toolbox_type}")

        except Exception as e:
            logger.error(f"Failed to create floating panel UI: {e}")
            self._window = f"mock_floating_panel_{self.toolbox_type.value}"

    def _create_title_bar(self) -> Any:
        """Create the title bar with controls."""
        if not self._gimp_available:
            return f"mock_title_bar_{self.toolbox_type.value}"

        try:
            import gimp
            from gimpfu import *

            # Create title bar container
            title_bar = gimp.ui.HBox(spacing=self.layout_manager.get_spacing("small"))
            title_bar.set_size_request(-1, 28)  # Fixed height

            # Add drag handle (invisible event box)
            drag_handle = gimp.ui.EventBox()
            drag_handle.connect("button-press-event", self._on_title_drag_start)
            drag_handle.connect("motion-notify-event", self._on_title_drag_motion)
            drag_handle.connect("button-release-event", self._on_title_drag_end)

            # Make it fill available space
            title_hbox = gimp.ui.HBox()
            drag_handle.add(title_hbox)

            # Add toolbox icon
            icon = self.icon_registry.get_toolbox_icon(self.toolbox_type.value, IconSize.SMALL)
            # Would add icon here

            # Add title label
            title_label = gimp.ui.Label(self.toolbox_type.value.title())
            title_hbox.pack_start(title_label, expand=True, fill=True)

            title_bar.pack_start(drag_handle, expand=True, fill=True)

            # Add control buttons
            controls_hbox = gimp.ui.HBox(spacing=0)

            # Minimize button
            minimize_button = self._create_title_button(ToolboxIcon.MINIMIZE, self._on_minimize_click)
            controls_hbox.pack_start(minimize_button, expand=False, fill=False)

            # Dock/Float toggle button
            dock_icon = ToolboxIcon.DOCK if not self._is_docked else ToolboxIcon.FLOAT
            dock_button = self._create_title_button(dock_icon, self._on_dock_toggle)
            controls_hbox.pack_start(dock_button, expand=False, fill=False)

            # Close button
            close_button = self._create_title_button(ToolboxIcon.CLOSE, self._on_close_click)
            controls_hbox.pack_start(close_button, expand=False, fill=False)

            title_bar.pack_start(controls_hbox, expand=False, fill=False)

            # Apply title bar styling
            self.layout_manager.apply_theme_to_widget(title_bar, "title_bar")

            return title_bar

        except Exception as e:
            logger.error(f"Failed to create title bar: {e}")
            return f"mock_title_bar_{self.toolbox_type.value}"

    def _create_title_button(self, icon: ToolboxIcon, callback: Callable) -> Any:
        """Create a title bar button."""
        if not self._gimp_available:
            return f"mock_button_{icon.value}"

        try:
            import gimp
            from gimpfu import *

            button = gimp.ui.Button()
            button.set_size_request(24, 24)  # Small square buttons
            button.set_relief(gimp.RELIEF_NONE)  # Flat buttons

            # Set icon
            icon_pixbuf = self.icon_registry.get_icon(icon, IconSize.SMALL)
            # button.set_image(icon_pixbuf)

            button.connect("clicked", callback)

            # Apply button styling
            self.layout_manager.apply_theme_to_widget(button, "title_button")

            return button

        except Exception as e:
            logger.error(f"Failed to create title button: {e}")
            return f"mock_button_{icon.value}"

    def _on_title_drag_start(self, widget: Any, event: Any):
        """Handle start of title bar drag."""
        if event.button == 1:  # Left mouse button
            self._is_dragging = True
            window_x, window_y = self._window.get_position()
            self._drag_offset = (event.x_root - window_x, event.y_root - window_y)
            logger.debug("Started dragging floating panel")

    def _on_title_drag_motion(self, widget: Any, event: Any):
        """Handle title bar drag motion."""
        if self._is_dragging:
            new_x = event.x_root - self._drag_offset[0]
            new_y = event.y_root - self._drag_offset[1]
            self._window.move(new_x, new_y)

    def _on_title_drag_end(self, widget: Any, event: Any):
        """Handle end of title bar drag."""
        if self._is_dragging:
            self._is_dragging = False
            # Update position in state
            new_position = self._window.get_position()
            self.position = new_position
            self.state_manager.update_toolbox_position(self.toolbox_type, new_position)

            if self.on_position_changed:
                self.on_position_changed(new_position)

            logger.debug(f"Floating panel moved to {new_position}")

    def _on_window_configure(self, widget: Any, event: Any):
        """Handle window configure event (resize/move)."""
        if not self._is_dragging:  # Avoid updating during drag
            new_position = self._window.get_position()
            if new_position != self.position:
                self.position = new_position
                self.state_manager.update_toolbox_position(self.toolbox_type, new_position)

                if self.on_position_changed:
                    self.on_position_changed(new_position)

    def _on_minimize_click(self, button: Any):
        """Handle minimize button click."""
        logger.debug(f"Minimizing floating panel: {self.toolbox_type}")
        self.minimize()

    def _on_dock_toggle(self, button: Any):
        """Handle dock/float toggle."""
        if self._is_docked:
            self.float_panel()
        else:
            self.dock_panel()

    def _on_close_click(self, button: Any):
        """Handle close button click."""
        logger.debug(f"Closing floating panel: {self.toolbox_type}")
        self.close()

    def _on_window_delete(self, widget: Any, event: Any):
        """Handle window delete event."""
        self.close()
        return True  # Prevent default handling

    def set_content(self, content_widget: Any):
        """
        Set the content of the floating panel.

        Args:
            content_widget: Widget to place in the content area
        """
        if self._gimp_available and self._content_area:
            # Clear existing content
            for child in self._content_area.get_children():
                self._content_area.remove(child)

            # Add new content
            self._content_area.add(content_widget)

    def show(self):
        """Show the floating panel."""
        if self._gimp_available and self._window:
            self._window.show_all()
            # Bring to front
            self._window.present()

    def hide(self):
        """Hide the floating panel."""
        if self._gimp_available and self._window:
            self._window.hide()

    def close(self):
        """Close the floating panel."""
        self.hide()

        # Update state
        self.state_manager.update_toolbox_state(self.toolbox_type, ToolboxState.CLOSED)

        if self.on_close:
            self.on_close()

    def minimize(self):
        """Minimize the floating panel."""
        # For floating panels, minimize could mean hide or shrink
        # For now, we'll just hide it
        self.hide()

        # Update state to minimized
        self.state_manager.update_toolbox_state(self.toolbox_type, ToolboxState.MINIMIZED)

        if self.on_minimize:
            self.on_minimize()

    def dock_panel(self):
        """Dock the floating panel."""
        logger.debug(f"Docking panel: {self.toolbox_type}")
        self._is_docked = True

        # Update state
        self.state_manager.update_toolbox_state(self.toolbox_type, ToolboxState.OPEN)

        if self.on_dock:
            self.on_dock()

    def float_panel(self):
        """Float the docked panel."""
        logger.debug(f"Floating panel: {self.toolbox_type}")
        self._is_docked = False

        # Update state
        self.state_manager.update_toolbox_state(self.toolbox_type, ToolboxState.FLOATING)

        self.show()

    def resize(self, width: int, height: int):
        """
        Resize the floating panel.

        Args:
            width: New width
            height: New height
        """
        self.size = (width, height)

        if self._gimp_available and self._window:
            self._window.resize(width, height)

        # Update state
        self.state_manager.update_toolbox_size(self.toolbox_type, self.size)

        if self.on_size_changed:
            self.on_size_changed(self.size)

    def move_to(self, x: int, y: int):
        """
        Move the floating panel to a new position.

        Args:
            x: New x coordinate
            y: New y coordinate
        """
        self.position = (x, y)

        if self._gimp_available and self._window:
            self._window.move(x, y)

        # Update state
        self.state_manager.update_toolbox_position(self.toolbox_type, self.position)

        if self.on_position_changed:
            self.on_position_changed(self.position)

    def bring_to_front(self):
        """Bring the floating panel to the front."""
        if self._gimp_available and self._window:
            self._window.present()

    def get_geometry(self) -> Tuple[int, int, int, int]:
        """
        Get the panel geometry.

        Returns:
            Tuple of (x, y, width, height)
        """
        if self._gimp_available and self._window:
            x, y = self._window.get_position()
            width, height = self._window.get_size()
            return x, y, width, height
        else:
            return self.position[0], self.position[1], self.size[0], self.size[1]

    def is_visible(self) -> bool:
        """
        Check if the panel is currently visible.

        Returns:
            True if visible, False otherwise
        """
        if self._gimp_available and self._window:
            return self._window.get_visible()
        else:
            return True  # Assume visible for mock

    def set_title(self, title: str):
        """
        Set the panel title.

        Args:
            title: New title
        """
        if self._gimp_available and self._window:
            self._window.set_title(title)

    def get_window(self) -> Any:
        """Get the window widget."""
        return self._window

    def destroy(self):
        """Destroy the floating panel."""
        if self._gimp_available and self._window:
            self._window.destroy()
            self._window = None

        logger.debug(f"Floating panel destroyed: {self.toolbox_type}")