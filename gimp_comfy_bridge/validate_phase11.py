#!/usr/bin/env python3
"""
Quick validation script for Phase 11 UI implementation.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all UI modules can be imported."""
    print("Testing UI module imports...")

    try:
        # Test main module
        from gimp_plugin.ui import (
            UIStateManager, ToolboxType, ToolboxState,
            IconRegistry, IconSize, ToolboxIcon,
            LayoutManager, Spacing, BorderRadius, FontSize,
            ToolboxBar, ToolboxBarPosition,
            ToolboxPanel, PanelSection,
            FloatingPanel, ToolboxSwitcher
        )
        print("✓ All UI components imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality of UI components."""
    print("\nTesting basic functionality...")

    try:
        from gimp_plugin.ui import UIStateManager, ToolboxType, IconRegistry, LayoutManager

        # Test state manager
        state_mgr = UIStateManager()
        print("✓ UIStateManager created")

        # Test toolbox types
        toolbox_types = list(ToolboxType)
        print(f"✓ Toolbox types: {len(toolbox_types)} available")

        # Test icon registry
        icon_reg = IconRegistry()
        print("✓ IconRegistry created")

        # Test layout manager
        layout_mgr = LayoutManager()
        print("✓ LayoutManager created")

        return True
    except Exception as e:
        print(f"✗ Functionality test failed: {e}")
        return False

def test_enum_values():
    """Test that enums have expected values."""
    print("\nTesting enum values...")

    try:
        from gimp_plugin.ui import ToolboxType, ToolboxState, ToolboxIcon, IconSize

        # Check toolbox types
        expected_types = ["templates", "styles", "workflows", "tasks", "settings"]
        actual_types = [t.value for t in ToolboxType]
        if set(expected_types) == set(actual_types):
            print("✓ ToolboxType enum values correct")
        else:
            print(f"✗ ToolboxType mismatch: expected {expected_types}, got {actual_types}")
            return False

        # Check toolbox states
        expected_states = ["closed", "minimized", "open", "floating"]
        actual_states = [s.value for s in ToolboxState]
        if set(expected_states) == set(actual_states):
            print("✓ ToolboxState enum values correct")
        else:
            print(f"✗ ToolboxState mismatch: expected {expected_states}, got {actual_states}")
            return False

        # Check icon sizes
        expected_sizes = ["small", "medium", "large"]
        actual_sizes = [s.value for s in IconSize]
        if set(expected_sizes) == set(actual_sizes):
            print("✓ IconSize enum values correct")
        else:
            print(f"✗ IconSize mismatch: expected {expected_sizes}, got {actual_sizes}")
            return False

        return True
    except Exception as e:
        print(f"✗ Enum test failed: {e}")
        return False

def main():
    """Run all validation tests."""
    print("Phase 11 UI Implementation Validation")
    print("=" * 40)

    all_passed = True

    # Run tests
    all_passed &= test_imports()
    all_passed &= test_basic_functionality()
    all_passed &= test_enum_values()

    print("\n" + "=" * 40)
    if all_passed:
        print("✓ All validation tests passed!")
        return 0
    else:
        print("✗ Some validation tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())