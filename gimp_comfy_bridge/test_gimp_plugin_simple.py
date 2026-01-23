#!/usr/bin/env python3
"""
Simple test suite for Comfy Gimpy Node Pack GIMP Plugin.
"""

import unittest
from pathlib import Path
import sys
import json

# Add plugin directory to path for testing
sys.path.insert(0, str(Path(__file__).parent))

class TestGIMPPlugin(unittest.TestCase):
    """Test cases for GIMP plugin functionality."""

    def test_plugin_file_structure(self):
        """Test plugin file structure is correct."""
        plugin_dir = Path(__file__).parent / "gimp_plugin"

        required_files = [
            "comfyui_bridge.py",
            "ui_panel.py",
            "plugin.py",
            "api_client.py",
            "utils.py",
            "config.json"
        ]

        for filename in required_files:
            file_path = plugin_dir / filename
            self.assertTrue(file_path.exists(), f"Required file missing: {filename}")

    def test_config_loading(self):
        """Test configuration loading."""
        config_file = Path(__file__).parent / "gimp_plugin" / "config.json"
        self.assertTrue(config_file.exists(), "Config file should exist")

        with open(config_file, 'r') as f:
            config = json.load(f)

        required_keys = [
            "comfyui_endpoint", "websocket_endpoint", "temp_dir",
            "default_workflow", "auto_save", "progress_update_interval"
        ]

        for key in required_keys:
            self.assertIn(key, config, f"Config missing required key: {key}")

    def test_api_client_initialization(self):
        """Test API client functions exist."""
        from gimp_plugin import api_client

        # Test that key functions exist
        self.assertTrue(hasattr(api_client, 'ping_backend'))
        self.assertTrue(hasattr(api_client, 'run_workflow'))

    def test_utils_functions_exist(self):
        """Test utils functions exist."""
        from gimp_plugin import utils

        # Test that key functions exist
        self.assertTrue(hasattr(utils, 'export_current_layer'))
        self.assertTrue(hasattr(utils, 'export_selection_mask'))
        self.assertTrue(hasattr(utils, 'insert_image_as_new_layer'))
        self.assertTrue(hasattr(utils, 'generate_outpaint_mask'))
        self.assertTrue(hasattr(utils, 'get_image_dimensions'))
        self.assertTrue(hasattr(utils, 'has_active_selection'))
        self.assertTrue(hasattr(utils, 'get_active_layer_name'))

    def test_plugin_module_imports(self):
        """Test plugin module imports."""
        try:
            from gimp_plugin import plugin
            from gimp_plugin import ui_panel
            from gimp_plugin import api_client
            from gimp_plugin import utils

        # Verify key classes exist
            self.assertTrue(hasattr(ui_panel, 'ComfyUIPanel'))
            # Note: api_client has functions, not classes

        except ImportError as e:
            self.fail(f"Failed to import plugin modules: {e}")

    def test_installation_script_functions(self):
        """Test installation script functions."""
        from install import get_gimp_plugin_dir, find_gimp_executable

        # Test plugin dir detection (will return None in test environment)
        plugin_dir = get_gimp_plugin_dir()
        self.assertIsNone(plugin_dir)  # Expected in test environment

        # Test executable finding (will return None in test environment)
        exe_path = find_gimp_executable()
        self.assertIsNone(exe_path)  # Expected in test environment

class TestPluginIntegration(unittest.TestCase):
    """Integration tests for plugin components."""

    def test_plugin_files_compile(self):
        """Test that all plugin files compile without syntax errors."""
        import py_compile

        plugin_dir = Path(__file__).parent / "gimp_plugin"

        for py_file in plugin_dir.glob("*.py"):
            try:
                py_compile.compile(str(py_file), doraise=True)
            except py_compile.PyCompileError as e:
                self.fail(f"Failed to compile {py_file.name}: {e}")

    def test_main_plugin_file_structure(self):
        """Test main plugin file has required components."""
        plugin_file = Path(__file__).parent / "gimp_plugin" / "comfyui_bridge.py"

        with open(plugin_file, 'r') as f:
            content = f.read()

        # Check for required functions
        required_functions = [
            "plugin_main", "show_main_dialog", "upscale_current_layer",
            "inpaint_selection", "generate_text_to_image"
        ]

        for func in required_functions:
            self.assertIn(f"def {func}", content, f"Function {func} not found in main plugin file")

    def test_ui_panel_structure(self):
        """Test UI panel has required components."""
        ui_file = Path(__file__).parent / "gimp_plugin" / "ui_panel.py"

        with open(ui_file, 'r') as f:
            content = f.read()

        # Check for required class
        self.assertIn("class ComfyUIPanel", content, "ComfyUIPanel class not found")

        # Check for required methods
        required_methods = [
            "show_main_dialog", "show_progress_dialog", "update_progress"
        ]

        for method in required_methods:
            self.assertIn(f"def {method}", content, f"Method {method} not found in UI panel")

def run_tests():
    """Run the test suite."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test cases
    suite.addTest(loader.loadTestsFromTestCase(TestGIMPPlugin))
    suite.addTest(loader.loadTestsFromTestCase(TestPluginIntegration))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)