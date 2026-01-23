#!/usr/bin/env python3
"""
ComfyUI Bridge GIMP Plugin
Main plugin file for GIMP integration with ComfyUI workflows.
"""

import os
import sys
import logging
from pathlib import Path

# Add the plugin directory to Python path
plugin_dir = Path(__file__).parent
sys.path.insert(0, str(plugin_dir.parent))

# Import GIMP modules
try:
    import gimp
    from gimpfu import *
    from gimpenums import *
except ImportError:
    # Fallback for development/testing
    print("GIMP modules not available, running in development mode")
    gimp = None

# Import our modules
from gimp_plugin.plugin import (
    undo_ai_step, redo_ai_step, send_current_layer_for_inpaint,
    send_current_layer_for_upscale, generate_from_text,
    send_current_layer_for_img2img, send_current_layer_for_controlnet
)
from gimp_plugin.ui_panel import ComfyUIPanel

# Import new UI system (Phase 11)
try:
    from gimp_plugin.ui import (
        UIStateManager, IconRegistry, LayoutManager,
        ToolboxBar, ToolboxPanel, FloatingPanel, ToolboxSwitcher
    )
    NEW_UI_AVAILABLE = True
except ImportError:
    NEW_UI_AVAILABLE = False
    logger.warning("New UI system not available, falling back to legacy UI")

from gimp_plugin.api_client import ping_backend, get_workflows

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(plugin_dir / "comfyui_bridge.log")),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Global variables
panel = None
ui_state_manager = None
icon_registry = None
layout_manager = None
toolbox_bar = None
toolbox_panel = None
floating_panel = None
toolbox_switcher = None

def _handle_toolbox_action(toolbox_type, action):
    """
    Handle toolbox action from switcher.

    Args:
        toolbox_type: Type of toolbox
        action: Action to perform ("open", "minimize", "float", "close")
    """
    global toolbox_bar, toolbox_panel, floating_panel

    try:
        if action == "open":
            if toolbox_bar:
                toolbox_bar.show_toolbox(toolbox_type.value)
            if toolbox_panel:
                toolbox_panel.show_toolbox(toolbox_type.value)
        elif action == "minimize":
            if toolbox_panel:
                toolbox_panel.minimize_toolbox(toolbox_type.value)
        elif action == "float":
            if floating_panel:
                floating_panel.float_toolbox(toolbox_type.value)
        elif action == "close":
            if toolbox_bar:
                toolbox_bar.hide_toolbox(toolbox_type.value)
            if toolbox_panel:
                toolbox_panel.hide_toolbox(toolbox_type.value)
            if floating_panel:
                floating_panel.close_toolbox(toolbox_type.value)

        logger.debug(f"Handled toolbox action: {toolbox_type.value} -> {action}")

    except Exception as e:
        logger.error(f"Failed to handle toolbox action: {e}")

def _register_keyboard_shortcuts():
    """Register keyboard shortcuts for the new UI system."""
    global toolbox_switcher

    if not NEW_UI_AVAILABLE or not toolbox_switcher:
        return

    try:
        # The toolbox switcher handles its own shortcut registration
        # Additional shortcuts can be registered here if needed
        logger.debug("Keyboard shortcuts registered for new UI system")

    except Exception as e:
        logger.error(f"Failed to register keyboard shortcuts: {e}")

def show_toolbox_switcher():
    """Show the toolbox switcher (Ctrl+X)."""
    global toolbox_switcher

    if toolbox_switcher:
        toolbox_switcher.show()
    else:
        logger.warning("Toolbox switcher not available")

def toggle_toolbox_bar():
    """Toggle the toolbox bar visibility."""
    global toolbox_bar

    if toolbox_bar:
        toolbox_bar.toggle_visibility()
    else:
        logger.warning("Toolbox bar not available")

def toggle_toolbox_panel():
    """Toggle the toolbox panel visibility."""
    global toolbox_panel

    if toolbox_panel:
        toolbox_panel.toggle_visibility()
    else:
        logger.warning("Toolbox panel not available")

def plugin_main():
    """Main plugin entry point."""
    global panel, ui_state_manager, icon_registry, layout_manager
    global toolbox_bar, toolbox_panel, floating_panel, toolbox_switcher

    logger.info("Initializing ComfyUI Bridge GIMP Plugin")

    # Test backend connection
    try:
        if ping_backend():
            logger.info("Backend connection successful")
        else:
            logger.warning("Backend connection failed")
    except Exception as e:
        logger.error(f"Backend connection test failed: {e}")

    # Initialize legacy UI panel (fallback)
    panel = ComfyUIPanel()

    # Initialize new UI system (Phase 11)
    if NEW_UI_AVAILABLE:
        try:
            logger.info("Initializing new UI system (Phase 11)")

            # Initialize core UI systems
            ui_state_manager = UIStateManager()
            icon_registry = IconRegistry()
            layout_manager = LayoutManager()

            # Initialize UI components
            toolbox_bar = ToolboxBar(ui_state_manager, icon_registry, layout_manager)
            toolbox_panel = ToolboxPanel(ui_state_manager, icon_registry, layout_manager)
            floating_panel = FloatingPanel(ui_state_manager, icon_registry, layout_manager)
            toolbox_switcher = ToolboxSwitcher(ui_state_manager, icon_registry, layout_manager)

            # Connect toolbox switcher to UI components
            toolbox_switcher.on_toolbox_action = _handle_toolbox_action

            # Register keyboard shortcut for switcher
            _register_keyboard_shortcuts()

            logger.info("New UI system initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize new UI system: {e}")
            NEW_UI_AVAILABLE = False

    # Load workflows
    try:
        workflows = get_workflows()
        panel.update_workflows(workflows)
        logger.info(f"Loaded {len(workflows)} workflows")
    except Exception as e:
        logger.error(f"Failed to load workflows: {e}")

    logger.info("ComfyUI Bridge GIMP Plugin initialized")

def show_main_dialog():
    """Show the main ComfyUI Bridge dialog."""
    global panel
    if panel:
        panel.show_main_dialog()

def upscale_current_layer(scale_factor, method):
    """Upscale the current layer."""
    try:
        from gimp_plugin.plugin import send_current_layer_for_upscale
        result = send_current_layer_for_upscale(scale_factor)
        if result:
            logger.info("Upscale completed successfully")
        else:
            logger.error("Upscale failed")
    except Exception as e:
        logger.error(f"Upscale failed: {e}")

def inpaint_selection(prompt, negative_prompt):
    """Inpaint the current selection."""
    try:
        from gimp_plugin.plugin import send_current_layer_for_inpaint
        result = send_current_layer_for_inpaint(prompt, negative_prompt)
        if result:
            logger.info("Inpaint completed successfully")
        else:
            logger.error("Inpaint failed")
    except Exception as e:
        logger.error(f"Inpaint failed: {e}")

def generate_text_to_image(prompt, negative_prompt, width, height):
    """Generate image from text."""
    try:
        from gimp_plugin.plugin import generate_from_text
        result = generate_from_text(prompt, negative_prompt, width, height)
        if result:
            logger.info("Text-to-image generation completed successfully")
        else:
            logger.error("Text-to-image generation failed")
    except Exception as e:
        logger.error(f"Text-to-image generation failed: {e}")

# Register plugin functions with GIMP
if gimp:
    try:
        register(
            "comfyui_bridge_main",
            "ComfyUI Bridge Main Dialog",
            "Main dialog for ComfyUI Bridge operations",
            "ComfyUI Bridge Team",
            "ComfyUI Bridge Team",
            "2024",
            "ComfyUI Bridge...",
            "*",
            [],
            [],
            show_main_dialog,
            menu="<Image>/Edit"
        )

        register(
            "comfyui_bridge_upscale",
            "Upscale Layer",
            "Upscale the current layer using ComfyUI",
            "ComfyUI Bridge Team",
            "ComfyUI Bridge Team",
            "2024",
            "Upscale Layer...",
            "*",
            [
                (PF_FLOAT, "scale_factor", "Scale Factor", 2.0),
                (PF_OPTION, "method", "Upscale Method", 0, ["4x-UltraSharp", "4x_NMKD-Superscale", "ESRGAN_4x"])
            ],
            [],
            upscale_current_layer,
            menu="<Image>/Edit"
        )

        register(
            "comfyui_bridge_inpaint",
            "Inpaint Selection",
            "Inpaint the current selection using ComfyUI",
            "ComfyUI Bridge Team",
            "ComfyUI Bridge Team",
            "2024",
            "Inpaint Selection...",
            "*",
            [
                (PF_STRING, "prompt", "Prompt", "beautiful landscape"),
                (PF_STRING, "negative_prompt", "Negative Prompt", "blurry, low quality")
            ],
            [],
            inpaint_selection,
            menu="<Image>/Edit"
        )

        register(
            "comfyui_bridge_generate",
            "Generate from Text",
            "Generate new image from text prompt using ComfyUI",
            "ComfyUI Bridge Team",
            "ComfyUI Bridge Team",
            "2024",
            "Generate from Text...",
            "*",
            [
                (PF_STRING, "prompt", "Prompt", "beautiful landscape"),
                (PF_STRING, "negative_prompt", "Negative Prompt", "blurry, low quality"),
                (PF_INT, "width", "Width", 1024),
                (PF_INT, "height", "Height", 1024)
            ],
            [],
            generate_text_to_image,
            menu="<Image>/Edit"
        )

        register(
            "comfyui_bridge_undo",
            "Undo AI Step",
            "Undo the last AI operation",
            "ComfyUI Bridge Team",
            "ComfyUI Bridge Team",
            "2024",
            "Undo AI Step",
            "*",
            [],
            [],
            undo_ai_step,
            menu="<Image>/Edit"
        )

        register(
            "comfyui_bridge_redo",
            "Redo AI Step",
            "Redo the last undone AI operation",
            "ComfyUI Bridge Team",
            "ComfyUI Bridge Team",
            "2024",
            "Redo AI Step",
            "*",
            [],
            [],
            redo_ai_step,
            menu="<Image>/Edit"
        )

        # Register new UI system functions (Phase 11)
        if NEW_UI_AVAILABLE:
            register(
                "comfyui_bridge_show_switcher",
                "Show Toolbox Switcher",
                "Show the keyboard-driven toolbox switcher (Ctrl+X)",
                "ComfyUI Bridge Team",
                "ComfyUI Bridge Team",
                "2024",
                "Show Toolbox Switcher",
                "*",
                [],
                [],
                show_toolbox_switcher,
                menu="<Image>/ComfyUI Bridge/UI"
            )

            register(
                "comfyui_bridge_toggle_toolbox_bar",
                "Toggle Toolbox Bar",
                "Toggle the side-scrollable toolbox bar",
                "ComfyUI Bridge Team",
                "ComfyUI Bridge Team",
                "2024",
                "Toggle Toolbox Bar",
                "*",
                [],
                [],
                toggle_toolbox_bar,
                menu="<Image>/ComfyUI Bridge/UI"
            )

            register(
                "comfyui_bridge_toggle_toolbox_panel",
                "Toggle Toolbox Panel",
                "Toggle the expandable toolbox panel",
                "ComfyUI Bridge Team",
                "ComfyUI Bridge Team",
                "2024",
                "Toggle Toolbox Panel",
                "*",
                [],
                [],
                toggle_toolbox_panel,
                menu="<Image>/ComfyUI Bridge/UI"
            )

    except Exception as e:
        logger.error(f"Failed to register GIMP plugin functions: {e}")
else:
    logger.info("GIMP not available, skipping plugin registration")
    """Main function."""
    plugin_main()

if __name__ == "__main__":
    main()