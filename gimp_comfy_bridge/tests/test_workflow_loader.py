"""
Tests for comfy_extension/workflow_loader.py
"""

import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch
from comfy_extension.workflow_loader import load_workflow_template, list_available_workflows

class TestWorkflowLoader(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)

    @patch('comfy_extension.workflow_loader.load_config')
    def test_load_workflow_template_exists(self, mock_load_config):
        mock_load_config.return_value = type('Config', (), {'workflows_dir': self.temp_dir})()
        workflow_file = self.temp_dir / "test.json"
        workflow_file.write_text('{"workflow": "data"}')
        
        result = load_workflow_template("test")
        self.assertEqual(result, {"workflow": "data"})

    @patch('comfy_extension.workflow_loader.load_config')
    def test_load_workflow_template_not_exists(self, mock_load_config):
        mock_load_config.return_value = type('Config', (), {'workflows_dir': self.temp_dir})()
        result = load_workflow_template("nonexistent")
        self.assertEqual(result, {"workflow": "placeholder"})

    @patch('comfy_extension.workflow_loader.load_config')
    def test_list_available_workflows(self, mock_load_config):
        mock_load_config.return_value = type('Config', (), {'workflows_dir': self.temp_dir})()
        workflow_file = self.temp_dir / "test.json"
        workflow_file.write_text('{"workflow": "data"}')
        
        result = list_available_workflows()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "test")

if __name__ == '__main__':
    unittest.main()