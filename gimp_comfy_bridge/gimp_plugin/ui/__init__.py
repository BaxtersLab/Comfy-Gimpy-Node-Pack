"""
GIMP UI Overhaul for Comfy Gimpy Studio (Phase 11)

This module provides a modern, modular UI layer for GIMP integration,
featuring toolbox bars, floating panels, and keyboard-driven navigation.
"""

from .toolbox_bar import ToolboxBar, ToolboxBarPosition
from .toolbox_panel import ToolboxPanel, PanelSection
from .floating_panel import FloatingPanel
from .switcher_menu import ToolboxSwitcher
from .icons import IconRegistry, IconSize, ToolboxIcon
from .layout import LayoutManager, Spacing, BorderRadius, FontSize
from .state import UIStateManager, ToolboxType, ToolboxState, UIConfig, ToolboxConfig

__all__ = [
    # Core components
    'ToolboxBar',
    'ToolboxBarPosition',
    'ToolboxPanel',
    'PanelSection',
    'FloatingPanel',
    'ToolboxSwitcher',

    # Supporting systems
    'IconRegistry',
    'IconSize',
    'ToolboxIcon',
    'LayoutManager',
    'Spacing',
    'BorderRadius',
    'FontSize',
    'UIStateManager',
    'ToolboxType',
    'ToolboxState',
    'UIConfig',
    'ToolboxConfig'
]