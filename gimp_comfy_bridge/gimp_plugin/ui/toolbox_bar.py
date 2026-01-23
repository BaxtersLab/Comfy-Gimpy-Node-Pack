"""
Toolbox Bar for Comfy Gimpy Studio GIMP Plugin.

Provides a side-scrollable bar of toolbox icons with drag-to-reorder functionality.
"""

import logging
from typing import List, Dict, Any, Optional, Callable, Tuple
from enum import Enum

from .state import UIStateManager, ToolboxType, ToolboxState
from .icons import IconRegistry, IconSize
from .layout import LayoutManager

logger = logging.getLogger(__name__)


class ToolboxBarPosition(Enum):
    """Position of the toolbox bar."""
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"


class ToolboxBar:
    """Side-scrollable toolbox bar with drag-to-reorder functionality."""

    def __init__(self,
                 state_manager: UIStateManager,
                 icon_registry: IconRegistry,
                 layout_manager: LayoutManager,
                 position: ToolboxBarPosition = ToolboxBarPosition.LEFT):
        """
        Initialize the toolbox bar.

        Args:
            state_manager: UI state manager
            icon_registry: Icon registry
            layout_manager: Layout manager
            position: Position of the bar
        """
        self.state_manager = state_manager
        self.icon_registry = icon_registry
        self.layout_manager = layout_manager
        self.position = position

        self._gimp_available = self._check_gimp_availability()
        self._container = None
        self._toolbox_buttons: Dict[str, Any] = {}
        self._scroll_container = None
        self._is_dragging = False
        self._drag_start_pos = None
        self._drag_button = None

        # Callbacks
        self.on_toolbox_click: Optional[Callable[[ToolboxType], None]] = None
        self.on_toolbox_drag: Optional[Callable[[ToolboxType, int], None]] = None

        # Initialize UI
        self._create_ui()

    def _check_gimp_availability(self) -> bool:
        """Check if GIMP UI libraries are available."""
        try:
            import gimp
            from gimpfu import *
            return True
        except ImportError:
            return False

    def _create_ui(self):
        """Create the toolbox bar UI."""
        if not self._gimp_available:
            logger.warning("GIMP not available, creating mock toolbox bar")
            self._create_mock_ui()
            return

        try:
            import gimp
            from gimpfu import *

            # Create main container based on position
            if self.position in [ToolboxBarPosition.LEFT, ToolboxBarPosition.RIGHT]:
                self._container = gimp.ui.VBox(spacing=0)
                self._scroll_container = gimp.ui.ScrolledWindow()
                self._scroll_container.set_policy(gimp.POLICY_NEVER, gimp.POLICY_AUTOMATIC)
                self._scroll_container.add_with_viewport(self._container)
            else:  # TOP or BOTTOM
                self._container = gimp.ui.HBox(spacing=0)
                self._scroll_container = gimp.ui.ScrolledWindow()
                self._scroll_container.set_policy(gimp.POLICY_AUTOMATIC, gimp.POLICY_NEVER)
                self._scroll_container.add_with_viewport(self._container)

            # Apply styling
            self.layout_manager.apply_theme_to_widget(self._container, "toolbox_bar")

            # Create toolbox buttons
            self._create_toolbox_buttons()

            logger.debug("Toolbox bar UI created")

        except Exception as e:
            logger.error(f"Failed to create toolbox bar UI: {e}")
            self._create_mock_ui()

    def _create_mock_ui(self):
        """Create a mock UI for development/testing."""
        self._container = "mock_toolbox_bar_container"
        self._toolbox_buttons = {}
        logger.debug("Mock toolbox bar created")

    def _create_toolbox_buttons(self):
        """Create buttons for each toolbox."""
        ordered_toolboxes = self.state_manager.get_ordered_toolboxes()

        for toolbox_type, config in ordered_toolboxes:
            button = self._create_toolbox_button(toolbox_type, config)
            if button:
                self._toolbox_buttons[toolbox_type.value] = button
                self._container.pack_start(button, expand=False, fill=False)

    def _create_toolbox_button(self, toolbox_type: ToolboxType, config) -> Optional[Any]:
        """
        Create a button for a specific toolbox.

        Args:
            toolbox_type: Type of toolbox
            config: Toolbox configuration

        Returns:
            Button widget or None
        """
        if not self._gimp_available:
            return f"mock_button_{toolbox_type.value}"

        try:
            import gimp
            from gimpfu import *

            # Create button with icon
            icon = self.icon_registry.get_toolbox_icon(toolbox_type.value, IconSize.MEDIUM)
            button = gimp.ui.Button()

            # Set icon (this would depend on GIMP's API)
            # button.set_image(icon)

            # Set tooltip
            button.set_tooltip_text(f"{toolbox_type.value.title()} Toolbox")

            # Set size
            button.set_size_request(
                self.layout_manager.get_component_size("toolbox_bar", "width"),
                self.layout_manager.get_component_size("toolbox_bar", "width")  # Square buttons
            )

            # Apply styling based on state
            self._apply_button_styling(button, config.state)

            # Connect signals
            button.connect("clicked", self._on_button_clicked, toolbox_type)
            button.connect("button-press-event", self._on_button_press, toolbox_type)
            button.connect("button-release-event", self._on_button_release, toolbox_type)

            return button

        except Exception as e:
            logger.error(f"Failed to create button for {toolbox_type}: {e}")
            return None

    def _apply_button_styling(self, button: Any, state: ToolboxState):
        """
        Apply styling to a button based on its state.

        Args:
            button: The button widget
            state: Current state of the toolbox
        """
        if not self._gimp_available:
            return

        try:
            # Apply different styling based on state
            if state == ToolboxState.OPEN:
                # Highlighted/selected appearance
                pass  # Would apply CSS-like styling
            elif state == ToolboxState.MINIMIZED:
                # Dimmed appearance
                pass
            elif state == ToolboxState.FLOATING:
                # Different appearance for floating
                pass
            # CLOSED state uses default styling

        except Exception as e:
            logger.error(f"Failed to apply button styling: {e}")

    def _on_button_clicked(self, button: Any, toolbox_type: ToolboxType):
        """
        Handle button click.

        Args:
            button: The clicked button
            toolbox_type: Type of toolbox
        """
        logger.debug(f"Toolbox button clicked: {toolbox_type}")

        if self.on_toolbox_click:
            self.on_toolbox_click(toolbox_type)

    def _on_button_press(self, button: Any, event: Any, toolbox_type: ToolboxType):
        """
        Handle button press (for drag start).

        Args:
            button: The pressed button
            event: Event data
            toolbox_type: Type of toolbox
        """
        if event.button == 1:  # Left mouse button
            self._is_dragging = True
            self._drag_start_pos = (event.x_root, event.y_root)
            self._drag_button = button
            logger.debug(f"Started dragging toolbox: {toolbox_type}")

    def _on_button_release(self, button: Any, event: Any, toolbox_type: ToolboxType):
        """
        Handle button release (for drag end).

        Args:
            button: The released button
            event: Event data
            toolbox_type: Type of toolbox
        """
        if self._is_dragging and self._drag_button == button:
            self._is_dragging = False

            # Check if this was a drag or just a click
            if self._drag_start_pos:
                dx = abs(event.x_root - self._drag_start_pos[0])
                dy = abs(event.y_root - self._drag_start_pos[1])
                drag_threshold = 5  # pixels

                if dx > drag_threshold or dy > drag_threshold:
                    # This was a drag, handle reordering
                    self._handle_drag_reorder(toolbox_type, event.x_root, event.y_root)
                else:
                    # This was a click, already handled by _on_button_clicked
                    pass

            self._drag_start_pos = None
            self._drag_button = None

    def _handle_drag_reorder(self, toolbox_type: ToolboxType, x: float, y: float):
        """
        Handle reordering toolboxes via drag and drop.

        Args:
            toolbox_type: Type of toolbox being dragged
            x: X coordinate
            y: Y coordinate
        """
        # Calculate new position based on coordinates
        # This is a simplified implementation
        new_order = self._calculate_new_order(toolbox_type, x, y)

        if new_order != self.state_manager.get_toolbox_config(toolbox_type).order:
            # Update order in state
            toolbox_order = []
            ordered_toolboxes = self.state_manager.get_ordered_toolboxes()
            for t, _ in ordered_toolboxes:
                toolbox_order.append(t)

            # Move the dragged toolbox to new position
            toolbox_order.remove(toolbox_type)
            toolbox_order.insert(new_order, toolbox_type)

            self.state_manager.reorder_toolboxes(toolbox_order)

            # Rebuild UI
            self._rebuild_ui()

            if self.on_toolbox_drag:
                self.on_toolbox_drag(toolbox_type, new_order)

            logger.debug(f"Reordered toolbox {toolbox_type} to position {new_order}")

    def _calculate_new_order(self, toolbox_type: ToolboxType, x: float, y: float) -> int:
        """
        Calculate new order position based on drag coordinates.

        Args:
            toolbox_type: Type of toolbox being dragged
            x: X coordinate
            y: Y coordinate

        Returns:
            New order position
        """
        # Simplified calculation - in a real implementation,
        # this would determine which button the drag is over
        ordered_toolboxes = self.state_manager.get_ordered_toolboxes()
        current_order = None

        for i, (t, _) in enumerate(ordered_toolboxes):
            if t == toolbox_type:
                current_order = i
                break

        # For now, just return current order (no change)
        # Real implementation would analyze coordinates
        return current_order if current_order is not None else 0

    def _rebuild_ui(self):
        """Rebuild the toolbox bar UI after changes."""
        # Clear existing buttons
        if self._gimp_available and self._container:
            for child in self._container.get_children():
                self._container.remove(child)

        self._toolbox_buttons.clear()

        # Recreate buttons
        self._create_toolbox_buttons()

        # Force redraw
        if self._gimp_available and self._container:
            self._container.queue_draw()

    def update_toolbox_state(self, toolbox_type: ToolboxType, state: ToolboxState):
        """
        Update the visual state of a toolbox button.

        Args:
            toolbox_type: Type of toolbox
            state: New state
        """
        button_key = toolbox_type.value
        if button_key in self._toolbox_buttons:
            button = self._toolbox_buttons[button_key]
            self._apply_button_styling(button, state)

            # Update state in manager
            self.state_manager.update_toolbox_state(toolbox_type, state)

    def get_container(self) -> Any:
        """Get the main container widget."""
        return self._scroll_container or self._container

    def show(self):
        """Show the toolbox bar."""
        if self._gimp_available and self._container:
            self._container.show_all()

    def hide(self):
        """Hide the toolbox bar."""
        if self._gimp_available and self._container:
            self._container.hide()

    def set_position(self, position: ToolboxBarPosition):
        """
        Set the position of the toolbox bar.

        Args:
            position: New position
        """
        if position != self.position:
            self.position = position
            # Would need to recreate UI with new orientation
            # For now, just log the change
            logger.info(f"Toolbox bar position changed to {position}")

    def get_toolbox_button(self, toolbox_type: ToolboxType) -> Optional[Any]:
        """
        Get the button widget for a toolbox.

        Args:
            toolbox_type: Type of toolbox

        Returns:
            Button widget or None
        """
        return self._toolbox_buttons.get(toolbox_type.value)

    def scroll_to_toolbox(self, toolbox_type: ToolboxType):
        """
        Scroll the toolbox bar to make a toolbox visible.

        Args:
            toolbox_type: Type of toolbox to scroll to
        """
        if not self._gimp_available or not self._scroll_container:
            return

        button = self.get_toolbox_button(toolbox_type)
        if button:
            # Scroll to make button visible
            # This would use GIMP's scrolling API
            logger.debug(f"Scrolling to toolbox: {toolbox_type}")

    def set_visible_toolboxes(self, visible_types: List[ToolboxType]):
        """
        Set which toolboxes are visible in the bar.

        Args:
            visible_types: List of toolbox types to show
        """
        visible_set = {t.value for t in visible_types}

        for toolbox_type_str, button in self._toolbox_buttons.items():
            if self._gimp_available:
                if toolbox_type_str in visible_set:
                    button.show()
                else:
                    button.hide()
            else:
                # Mock implementation
                logger.debug(f"Setting visibility for {toolbox_type_str}: {toolbox_type_str in visible_set}")

    def get_preferred_size(self) -> Tuple[int, int]:
        """
        Get the preferred size of the toolbox bar.

        Returns:
            Tuple of (width, height)
        """
        if self.position in [ToolboxBarPosition.LEFT, ToolboxBarPosition.RIGHT]:
            width = self.layout_manager.get_component_size("toolbox_bar", "width")
            height = self.layout_manager.get_component_size("toolbox_bar", "height")
        else:
            width = self.layout_manager.get_component_size("toolbox_bar", "height")  # Swapped for horizontal
            height = self.layout_manager.get_component_size("toolbox_bar", "width")

        return width, height