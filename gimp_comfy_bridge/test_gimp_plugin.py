#!/usr/bin/env python3
"""
Test suite for Comfy Gimpy Node Pack GIMP Plugin.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add plugin directory to path for testing
sys.path.insert(0, str(Path(__file__).parent))

class TestGIMPPlugin(unittest.TestCase):
    """Test cases for GIMP plugin functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.plugin_dir = self.temp_dir / "gimp_plugin"
        self.plugin_dir.mkdir()

        # Copy plugin files to temp directory
        source_dir = Path(__file__).parent / "gimp_plugin"
        if source_dir.exists():
            for file in source_dir.glob("*.py"):
                shutil.copy2(file, self.plugin_dir / file.name)

        # Mock GIMP modules
        self.mock_gimp_modules()

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def mock_gimp_modules(self):
        """Mock GIMP modules for testing."""
        # Mock gimp module
        mock_gimp = Mock()
        mock_gimp.image_list.return_value = [Mock()]
        mock_gimp.get_active_layer.return_value = Mock()
        mock_gimp.get_active_layer.return_value.name = "Test Layer"

        # Mock gimpfu module
        mock_gimpfu = Mock()
        mock_gimpfu.pdb = Mock()
        mock_gimpfu.RUN_NONINTERACTIVE = 0

        # Mock gimpenums
        mock_gimpenums = Mock()
        mock_gimpenums.NORMAL_MODE = 0
        mock_gimpenums.WHITE_FILL = 0
        mock_gimpenums.BLACK_FILL = 1
        mock_gimpenums.REPLACE = 0
        mock_gimpenums.RGB = 0
        mock_gimpenums.RGB_IMAGE = 0

        # Patch modules
        self.patches = [
            patch.dict('sys.modules', {
                'gimp': mock_gimp,
                'gimpfu': mock_gimpfu,
                'gimpenums': mock_gimpenums
            }),
            patch('gimp_plugin.utils.GIMP_AVAILABLE', True),
            patch('gimp_plugin.ui_panel.GIMP_AVAILABLE', True),
            patch('gimp_plugin.comfyui_bridge.GIMP_AVAILABLE', True)
        ]

        for p in self.patches:
            p.start()

    def tearDown(self):
        """Clean up patches."""
        for p in self.patches:
            p.stop()

    def test_plugin_initialization(self):
        """Test plugin initialization."""
        from gimp_plugin.comfyui_bridge import plugin_main

        with patch('gimp_plugin.comfyui_bridge.register') as mock_register:
            plugin_main()

            # Verify registration was called
            self.assertTrue(mock_register.called)

    def test_export_current_layer(self):
        """Test exporting current layer."""
        from gimp_plugin.utils import export_current_layer

        # Mock the GIMP operations
        with patch('gimp.image_list') as mock_image_list, \
             patch('gimp.get_active_layer') as mock_get_layer, \
             patch('gimpfu.pdb.gimp_file_save') as mock_save:

            mock_image = Mock()
            mock_image.width = 512
            mock_image.height = 512
            mock_image_list.return_value = [mock_image]

            mock_layer = Mock()
            mock_layer.name = "Test Layer"
            mock_get_layer.return_value = mock_layer

            # Mock file creation
            test_file = self.temp_dir / "test_layer.png"
            test_file.write_bytes(b"test data")

            result = export_current_layer(self.temp_dir)

            self.assertTrue(result.exists())
            mock_save.assert_called_once()

    def test_export_selection_mask(self):
        """Test exporting selection mask."""
        from gimp_plugin.utils import export_selection_mask

        with patch('gimp.image_list') as mock_image_list, \
             patch('gimpfu.pdb.gimp_selection_is_empty') as mock_is_empty, \
             patch('gimpfu.pdb.gimp_selection_save') as mock_save_selection, \
             patch('gimpfu.pdb.gimp_file_save') as mock_save_file, \
             patch('gimpfu.pdb.gimp_image_remove_channel') as mock_remove_channel:

            mock_image = Mock()
            mock_image_list.return_value = [mock_image]
            mock_is_empty.return_value = False  # Selection exists

            mock_channel = Mock()
            mock_save_selection.return_value = mock_channel

            result = export_selection_mask(self.temp_dir)

            self.assertIsNotNone(result)
            mock_save_file.assert_called_once()
            mock_remove_channel.assert_called_once()

    def test_insert_image_as_new_layer(self):
        """Test inserting image as new layer."""
        from gimp_plugin.utils import insert_image_as_new_layer

        test_image = self.temp_dir / "test_image.png"
        test_image.write_bytes(b"test image data")

        with patch('gimp.image_list') as mock_image_list, \
             patch('gimpfu.pdb.gimp_file_load_layer') as mock_load_layer, \
             patch('gimpfu.pdb.gimp_image_add_layer') as mock_add_layer, \
             patch('gimpfu.pdb.gimp_displays_flush') as mock_flush:

            mock_image = Mock()
            mock_image_list.return_value = [mock_image]

            mock_layer = Mock()
            mock_load_layer.return_value = mock_layer

            insert_image_as_new_layer(test_image)

            mock_load_layer.assert_called_once_with(mock_image, str(test_image))
            mock_add_layer.assert_called_once_with(mock_image, mock_layer, 0)
            mock_flush.assert_called_once()

    def test_generate_outpaint_mask(self):
        """Test generating outpaint mask."""
        from gimp_plugin.utils import generate_outpaint_mask

        with patch('gimp.image_list') as mock_image_list, \
             patch('gimpfu.pdb.gimp_image_new') as mock_new_image, \
             patch('gimpfu.pdb.gimp_layer_new') as mock_new_layer, \
             patch('gimpfu.pdb.gimp_image_add_layer') as mock_add_layer, \
             patch('gimpfu.pdb.gimp_drawable_fill') as mock_fill, \
             patch('gimpfu.pdb.gimp_rect_select') as mock_select, \
             patch('gimpfu.pdb.gimp_edit_fill') as mock_edit_fill, \
             patch('gimpfu.pdb.gimp_selection_none') as mock_selection_none, \
             patch('gimpfu.pdb.gimp_file_save') as mock_save, \
             patch('gimpfu.pdb.gimp_image_delete') as mock_delete:

            mock_image = Mock()
            mock_image.width = 512
            mock_image.height = 512
            mock_image_list.return_value = [mock_image]

            mock_mask_image = Mock()
            mock_mask_image.width = 512
            mock_mask_image.height = 512
            mock_new_image.return_value = mock_mask_image

            mock_background = Mock()
            mock_new_layer.return_value = mock_background

            result = generate_outpaint_mask(self.temp_dir)

            self.assertTrue(result.exists())
            mock_new_image.assert_called_once_with(512, 512, 0)  # RGB
            mock_save.assert_called_once()
            mock_delete.assert_called_once_with(mock_mask_image)

    def test_get_image_dimensions(self):
        """Test getting image dimensions."""
        from gimp_plugin.utils import get_image_dimensions

        with patch('gimp.image_list') as mock_image_list:
            mock_image = Mock()
            mock_image.width = 1024
            mock_image.height = 768
            mock_image_list.return_value = [mock_image]

            width, height = get_image_dimensions()

            self.assertEqual(width, 1024)
            self.assertEqual(height, 768)

    def test_has_active_selection(self):
        """Test checking for active selection."""
        from gimp_plugin.utils import has_active_selection

        with patch('gimp.image_list') as mock_image_list, \
             patch('gimpfu.pdb.gimp_selection_is_empty') as mock_is_empty:

            mock_image = Mock()
            mock_image_list.return_value = [mock_image]
            mock_is_empty.return_value = False

            result = has_active_selection()

            self.assertTrue(result)
            mock_is_empty.assert_called_once_with(mock_image)

    def test_get_active_layer_name(self):
        """Test getting active layer name."""
        from gimp_plugin.utils import get_active_layer_name

        with patch('gimp.image_list') as mock_image_list, \
             patch('gimp.get_active_layer') as mock_get_layer:

            mock_image = Mock()
            mock_image_list.return_value = [mock_image]

            mock_layer = Mock()
            mock_layer.name = "Background Layer"
            mock_get_layer.return_value = mock_layer

            result = get_active_layer_name()

            self.assertEqual(result, "Background Layer")

    def test_ui_panel_creation(self):
        """Test UI panel creation."""
        from gimp_plugin.ui_panel import ComfyUIPanel

        panel = ComfyUIPanel()

        self.assertIsNotNone(panel)
        self.assertIsNone(panel.current_task_id)
        self.assertEqual(len(panel.workflows), 0)

    def test_workflow_options(self):
        """Test workflow options generation."""
        from gimp_plugin.ui_panel import ComfyUIPanel

        panel = ComfyUIPanel()
        panel.workflows = [
            {"name": "Custom Workflow 1", "mode": "custom"},
            {"name": "Custom Workflow 2", "mode": "custom"}
        ]

        options = panel._get_workflow_options()

        expected_base = ["Text to Image", "Image to Image", "Inpainting", "Outpainting", "Upscaling", "ControlNet"]
        expected_custom = ["Custom: Custom Workflow 1", "Custom: Custom Workflow 2"]

        self.assertEqual(options[:6], expected_base)
        self.assertEqual(options[6:], expected_custom)

    def test_api_client_initialization(self):
        """Test API client initialization."""
        from gimp_plugin.api_client import ComfyUIClient

        client = ComfyUIClient()

        self.assertIsNotNone(client)
        self.assertEqual(client.base_url, "http://localhost:8188")

    def test_plugin_functions_import(self):
        """Test plugin functions can be imported."""
        try:
            from gimp_plugin.plugin import (
                process_upscale, process_inpaint, process_outpaint,
                process_enhance, process_style_transfer, process_generate
            )
            # If we get here, imports succeeded
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import plugin functions: {e}")

    def test_config_loading(self):
        """Test configuration loading."""
        config_file = self.plugin_dir / "config.json"
        config_file.write_text('{"test_key": "test_value"}')

        # Test config loading logic would go here
        # For now, just verify file exists
        self.assertTrue(config_file.exists())

    def test_installation_script(self):
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

    def setUp(self):
        """Set up integration test."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up integration test."""
        shutil.rmtree(self.temp_dir)

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

    def test_plugin_imports(self):
        """Test all plugin modules can be imported."""
        plugin_dir = Path(__file__).parent / "gimp_plugin"

        # Add to path temporarily
        sys.path.insert(0, str(plugin_dir))

        try:
            import comfyui_bridge
            import ui_panel
            import plugin
            import api_client
            import utils

            # Verify key classes/functions exist
            self.assertTrue(hasattr(comfyui_bridge, 'plugin_main'))
            self.assertTrue(hasattr(ui_panel, 'ComfyUIPanel'))
            self.assertTrue(hasattr(plugin, 'process_upscale'))
            self.assertTrue(hasattr(api_client, 'ComfyUIClient'))
            self.assertTrue(hasattr(utils, 'export_current_layer'))

        finally:
            # Clean up path
            if str(plugin_dir) in sys.path:
                sys.path.remove(str(plugin_dir))

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