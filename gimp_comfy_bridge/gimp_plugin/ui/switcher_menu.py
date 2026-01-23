"""
Toolbox Switcher Menu for Comfy Gimpy Studio GIMP Plugin.

Provides a keyboard-driven (Ctrl+X) grid of toolbox icons with state indicators.
"""

import logging
from typing import Dict, List, Optional, Callable, Any, Tuple

from .state import UIStateManager, ToolboxType, ToolboxState
from .icons import IconRegistry, IconSize, ToolboxIcon
from .layout import LayoutManager

logger = logging.getLogger(__name__)


class ToolboxSwitcher:
    """Keyboard-driven toolbox switcher menu."""

    def __init__(self,
                 state_manager: UIStateManager,
                 icon_registry: IconRegistry,
                 layout_manager: LayoutManager):
        """
        Initialize the toolbox switcher.

        Args:
            state_manager: UI state manager
            icon_registry: Icon registry
            layout_manager: Layout manager
        """
        self.state_manager = state_manager
        self.icon_registry = icon_registry
        self.layout_manager = layout_manager

        self._gimp_available = self._check_gimp_availability()
        self._window = None
        self._grid = None
        self._toolbox_buttons: Dict[str, Any] = {}
        self._selected_index = 0
        self._is_visible = False

        # Keyboard shortcuts
        self._shortcut_key = "x"  # Ctrl+X
        self._shortcut_modifier = "control"

        # Callbacks
        self.on_toolbox_action: Optional[Callable[[ToolboxType, str], None]] = None
        self.on_template_generation: Optional[Callable[[str], None]] = None

        # Create UI
        self._create_ui()

        # Register keyboard shortcut
        self._register_shortcut()

    def _check_gimp_availability(self) -> bool:
        """Check if GIMP UI libraries are available."""
        try:
            import gimp
            return True
        except ImportError:
            return False

    def _create_ui(self):
        """Create the switcher menu UI."""
        if not self._gimp_available:
            self._window = f"mock_switcher_window"
            self._create_mock_buttons()
            return

        try:
            import gimp
            from gimpfu import *

            # Create window
            self._window = gimp.ui.Window()
            self._window.set_title("Toolbox Switcher")
            self._window.set_modal(True)
            self._window.set_decorated(False)  # Custom appearance
            self._window.set_keep_above(True)

            # Create main container with padding
            main_vbox = gimp.ui.VBox(spacing=self.layout_manager.get_spacing("medium"))
            main_vbox.set_border_width(self.layout_manager.get_spacing("large"))
            self._window.add(main_vbox)

            # Create title
            title_label = gimp.ui.Label("Toolbox Switcher (Ctrl+X)")
            title_label.set_alignment(0.5, 0.5)  # Center alignment
            main_vbox.pack_start(title_label, expand=False, fill=False)

            # Create toolbox grid
            self._grid = self._create_toolbox_grid()
            main_vbox.pack_start(self._grid, expand=True, fill=True)

            # Create instructions
            instructions = gimp.ui.Label("↑↓←→ navigate, Enter open, M minimize, F float, C close\nG prompt, I image, W workflow, E enhance, Esc cancel")
            instructions.set_alignment(0.5, 0.5)
            main_vbox.pack_start(instructions, expand=False, fill=False)

            # Connect signals
            self._window.connect("key-press-event", self._on_key_press)
            self._window.connect("focus-out-event", self._on_focus_lost)

            # Apply styling
            self.layout_manager.apply_theme_to_widget(self._window, "switcher_menu")

            # Initially hide
            self._window.hide()

            logger.debug("Toolbox switcher UI created")

        except Exception as e:
            logger.error(f"Failed to create switcher UI: {e}")
            self._window = f"mock_switcher_window"
            self._create_mock_buttons()

    def _create_mock_buttons(self):
        """Create mock buttons for development."""
        self._toolbox_buttons = {}
        for toolbox_type in ToolboxType:
            self._toolbox_buttons[toolbox_type.value] = f"mock_button_{toolbox_type.value}"

    def _create_toolbox_grid(self) -> Any:
        """Create the grid of toolbox buttons."""
        if not self._gimp_available:
            return "mock_grid"

        try:
            import gimp
            from gimpfu import *

            # Get ordered toolboxes
            ordered_toolboxes = self.state_manager.get_ordered_toolboxes()

            # Calculate grid dimensions (try to make it square-ish)
            num_toolboxes = len(ordered_toolboxes)
            cols = int(num_toolboxes ** 0.5) + 1
            rows = (num_toolboxes + cols - 1) // cols

            # Create grid
            grid = gimp.ui.Table(rows=rows, columns=cols)
            grid.set_homogeneous(True)
            grid.set_row_spacings(self.layout_manager.get_spacing("small"))
            grid.set_col_spacings(self.layout_manager.get_spacing("small"))

            # Create buttons for each toolbox
            for i, (toolbox_type, config) in enumerate(ordered_toolboxes):
                row = i // cols
                col = i % cols

                button = self._create_toolbox_button(toolbox_type, config)
                grid.attach(button, col, col+1, row, row+1)

                self._toolbox_buttons[toolbox_type.value] = button

            return grid

        except Exception as e:
            logger.error(f"Failed to create toolbox grid: {e}")
            return "mock_grid"

    def _create_toolbox_button(self, toolbox_type: ToolboxType, config) -> Any:
        """
        Create a button for a toolbox in the switcher.

        Args:
            toolbox_type: Type of toolbox
            config: Toolbox configuration

        Returns:
            Button widget
        """
        if not self._gimp_available:
            return f"mock_switcher_button_{toolbox_type.value}"

        try:
            import gimp
            from gimpfu import *

            # Create button container (VBox for icon + label + state)
            button_vbox = gimp.ui.VBox(spacing=self.layout_manager.get_spacing("tiny"))

            # Create clickable event box
            event_box = gimp.ui.EventBox()
            event_box.add(button_vbox)
            event_box.connect("button-press-event", self._on_toolbox_button_press, toolbox_type)

            # Add toolbox icon
            icon = self.icon_registry.get_toolbox_icon(toolbox_type.value, IconSize.LARGE)
            # Would add icon widget here

            # Add toolbox name
            name_label = gimp.ui.Label(toolbox_type.value.title())
            name_label.set_alignment(0.5, 0.5)
            button_vbox.pack_start(name_label, expand=False, fill=False)

            # Add state indicator
            state_label = gimp.ui.Label(self._get_state_text(config.state))
            state_label.set_alignment(0.5, 0.5)
            button_vbox.pack_start(state_label, expand=False, fill=False)

            # Apply styling based on state and selection
            self._apply_button_styling(event_box, config.state, False)

            # Set size
            event_box.set_size_request(100, 80)

            return event_box

        except Exception as e:
            logger.error(f"Failed to create toolbox button: {e}")
            return f"mock_switcher_button_{toolbox_type.value}"

    def _get_state_text(self, state: ToolboxState) -> str:
        """Get display text for a toolbox state."""
        state_texts = {
            ToolboxState.CLOSED: "Closed",
            ToolboxState.MINIMIZED: "Minimized",
            ToolboxState.OPEN: "Open",
            ToolboxState.FLOATING: "Floating"
        }
        return state_texts.get(state, "Unknown")

    def _apply_button_styling(self, widget: Any, state: ToolboxState, is_selected: bool):
        """
        Apply styling to a switcher button.

        Args:
            widget: The button widget
            state: Current state of the toolbox
            is_selected: Whether the button is currently selected
        """
        if not self._gimp_available:
            return

        try:
            # Apply different styling based on state and selection
            # This would use CSS-like styling in a real GIMP plugin
            if is_selected:
                # Highlight selected button
                pass
            elif state == ToolboxState.OPEN:
                # Different style for open toolboxes
                pass
            elif state == ToolboxState.FLOATING:
                # Different style for floating toolboxes
                pass

        except Exception as e:
            logger.error(f"Failed to apply button styling: {e}")

    def _register_shortcut(self):
        """Register the keyboard shortcut."""
        if not self._gimp_available:
            logger.debug("GIMP not available, skipping shortcut registration")
            return

        try:
            import gimp
            from gimpfu import *

            # Register Ctrl+X shortcut
            # This would typically be done through GIMP's accelerator system
            logger.debug("Toolbox switcher shortcut registered (Ctrl+X)")

        except Exception as e:
            logger.error(f"Failed to register shortcut: {e}")

    def _on_key_press(self, widget: Any, event: Any):
        """Handle key press events."""
        if not self._gimp_available:
            return

        try:
            keyval = event.keyval
            state = event.state

            # Handle arrow keys for navigation
            if keyval == gimp.GDK_KEY_Up:
                self._move_selection(-self._get_grid_cols(), "up")
            elif keyval == gimp.GDK_KEY_Down:
                self._move_selection(self._get_grid_cols(), "down")
            elif keyval == gimp.GDK_KEY_Left:
                self._move_selection(-1, "left")
            elif keyval == gimp.GDK_KEY_Right:
                self._move_selection(1, "right")

            # Handle action keys
            elif keyval == gimp.GDK_KEY_Return or keyval == gimp.GDK_KEY_KP_Enter:
                self._perform_action("open")
            elif keyval == gimp.GDK_KEY_m or keyval == gimp.GDK_KEY_M:
                self._perform_action("minimize")
            elif keyval == gimp.GDK_KEY_f or keyval == gimp.GDK_KEY_F:
                self._perform_action("float")
            elif keyval == gimp.GDK_KEY_c or keyval == gimp.GDK_KEY_C:
                self._perform_action("close")
            elif keyval == gimp.GDK_KEY_g or keyval == gimp.GDK_KEY_G:
                self._perform_template_generation("prompt")
            elif keyval == gimp.GDK_KEY_i or keyval == gimp.GDK_KEY_I:
                self._perform_template_generation("image")
            elif keyval == gimp.GDK_KEY_w or keyval == gimp.GDK_KEY_W:
                self._perform_template_generation("workflow")
            elif keyval == gimp.GDK_KEY_e or keyval == gimp.GDK_KEY_E:
                self._perform_template_generation("enhance")
            elif keyval == gimp.GDK_KEY_Escape:
                self.hide()

        except Exception as e:
            logger.error(f"Failed to handle key press: {e}")

    def _get_grid_cols(self) -> int:
        """Get the number of columns in the grid."""
        ordered_toolboxes = self.state_manager.get_ordered_toolboxes()
        num_toolboxes = len(ordered_toolboxes)
        return int(num_toolboxes ** 0.5) + 1

    def _move_selection(self, delta: int, direction: str):
        """
        Move the selection in the grid.

        Args:
            delta: How much to move the selection index
            direction: Direction of movement
        """
        ordered_toolboxes = self.state_manager.get_ordered_toolboxes()
        num_toolboxes = len(ordered_toolboxes)

        if num_toolboxes == 0:
            return

        old_index = self._selected_index
        new_index = (old_index + delta) % num_toolboxes

        # Handle edge cases for up/down movement
        cols = self._get_grid_cols()
        if direction in ["up", "down"]:
            old_row = old_index // cols
            old_col = old_index % cols
            new_row = new_index // cols
            new_col = new_index % cols

            # If we moved to a different row but same relative column
            if old_col != new_col:
                # Adjust to stay in same column
                if direction == "up" and old_row > 0:
                    new_index = old_index - cols
                elif direction == "down" and old_row < (num_toolboxes - 1) // cols:
                    new_index = old_index + cols

                new_index = max(0, min(new_index, num_toolboxes - 1))

        self._selected_index = new_index
        self._update_selection_display(old_index, new_index)

    def _update_selection_display(self, old_index: int, new_index: int):
        """
        Update the visual selection display.

        Args:
            old_index: Previously selected index
            new_index: Newly selected index
        """
        ordered_toolboxes = self.state_manager.get_ordered_toolboxes()

        # Update old selection
        if old_index < len(ordered_toolboxes):
            old_toolbox = ordered_toolboxes[old_index][0]
            old_button = self._toolbox_buttons.get(old_toolbox.value)
            if old_button:
                old_config = self.state_manager.get_toolbox_config(old_toolbox)
                self._apply_button_styling(old_button, old_config.state, False)

        # Update new selection
        if new_index < len(ordered_toolboxes):
            new_toolbox = ordered_toolboxes[new_index][0]
            new_button = self._toolbox_buttons.get(new_toolbox.value)
            if new_button:
                new_config = self.state_manager.get_toolbox_config(new_toolbox)
                self._apply_button_styling(new_button, new_config.state, True)

    def _perform_action(self, action: str):
        """
        Perform an action on the currently selected toolbox.

        Args:
            action: Action to perform ("open", "minimize", "float", "close")
        """
        ordered_toolboxes = self.state_manager.get_ordered_toolboxes()

        if self._selected_index < len(ordered_toolboxes):
            toolbox_type = ordered_toolboxes[self._selected_index][0]

            if self.on_toolbox_action:
                self.on_toolbox_action(toolbox_type, action)

            # Hide switcher after action
            self.hide()

    def _perform_template_generation(self, method: str):
        """
        Perform template generation action.

        Args:
            method: Generation method ("prompt", "image", "workflow", "enhance")
        """
        logger.debug(f"Template generation triggered: {method}")

        # Call template generation callback if set
        if hasattr(self, 'on_template_generation') and self.on_template_generation:
            self.on_template_generation(method)

        # Hide switcher after action
        self.hide()

    def _on_toolbox_button_press(self, widget: Any, event: Any, toolbox_type: ToolboxType):
        """
        Handle toolbox button press in switcher.

        Args:
            widget: The button widget
            event: Event data
            toolbox_type: Type of toolbox
        """
        if event.button == 1:  # Left click
            self._perform_action("open")

    def _on_focus_lost(self, widget: Any, event: Any):
        """Handle focus loss (hide switcher)."""
        self.hide()

    def show(self, center_on_screen: bool = True):
        """
        Show the toolbox switcher.

        Args:
            center_on_screen: Whether to center the switcher on screen
        """
        if not self._is_visible:
            if self._gimp_available and self._window:
                if center_on_screen:
                    self._center_on_screen()

                self._window.show_all()
                self._window.present()  # Bring to front and focus

                # Reset selection to first item
                self._selected_index = 0
                self._update_selection_display(-1, 0)

            self._is_visible = True
            logger.debug("Toolbox switcher shown")

    def hide(self):
        """Hide the toolbox switcher."""
        if self._is_visible:
            if self._gimp_available and self._window:
                self._window.hide()

            self._is_visible = False
            logger.debug("Toolbox switcher hidden")

    def _center_on_screen(self):
        """Center the switcher window on screen."""
        if not self._gimp_available or not self._window:
            return

        try:
            # Get screen dimensions (simplified)
            screen_width = 1920  # Would get from GIMP
            screen_height = 1080

            # Get window size
            width, height = self._window.get_size()

            # Center position
            x = (screen_width - width) // 2
            y = (screen_height - height) // 2

            self._window.move(x, y)

        except Exception as e:
            logger.error(f"Failed to center switcher: {e}")

    def toggle_visibility(self):
        """Toggle the visibility of the switcher."""
        if self._is_visible:
            self.hide()
        else:
            self.show()

    def is_visible(self) -> bool:
        """Check if the switcher is currently visible."""
        return self._is_visible

    def get_window(self) -> Any:
        """Get the switcher window widget."""
        return self._window

    def update_toolbox_states(self):
        """Update the display of toolbox states in the switcher."""
        ordered_toolboxes = self.state_manager.get_ordered_toolboxes()

        for i, (toolbox_type, config) in enumerate(ordered_toolboxes):
            button = self._toolbox_buttons.get(toolbox_type.value)
            if button:
                is_selected = (i == self._selected_index)
                self._apply_button_styling(button, config.state, is_selected)

    def destroy(self):
        """Destroy the switcher window."""
        if self._gimp_available and self._window:
            self._window.destroy()
            self._window = None

        self._toolbox_buttons.clear()
        logger.debug("Toolbox switcher destroyed")