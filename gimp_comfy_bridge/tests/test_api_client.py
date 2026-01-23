"""
Tests for gimp_plugin/api_client.py
"""

import unittest
from unittest.mock import patch, MagicMock
from gimp_plugin.api_client import ping_backend, run_workflow, get_workflows

class TestApiClient(unittest.TestCase):
    @patch('gimp_plugin.api_client.requests.post')
    def test_ping_backend_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok", "comfyui_version": "1.0", "models_available": []}
        mock_post.return_value = mock_response
        
        result = ping_backend()
        self.assertEqual(result.status, "ok")

    @patch('gimp_plugin.api_client.requests.post')
    def test_ping_backend_failure(self, mock_post):
        mock_post.side_effect = Exception("Network error")
        
        with self.assertRaises(Exception):
            ping_backend()

    @patch('gimp_plugin.api_client.requests.post')
    def test_run_workflow_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "completed", "task_id": "123", "result": {"image_base64": "dGVzdA=="}}
        mock_post.return_value = mock_response
        
        result = run_workflow("inpaint", "test", {})
        self.assertEqual(result.status, "completed")

    @patch('gimp_plugin.api_client.requests.get')
    def test_get_workflows_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"workflows": [{"name": "test"}]}
        mock_get.return_value = mock_response
        
        result = get_workflows()
        self.assertEqual(len(result), 1)

if __name__ == '__main__':
    unittest.main()