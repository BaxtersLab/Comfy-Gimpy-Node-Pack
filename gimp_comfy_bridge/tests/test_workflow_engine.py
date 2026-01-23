"""
Tests for workflow engine.
"""

import unittest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from comfy_extension.workflow_engine import WorkflowExecutionEngine, WorkflowStatus
from shared.protocol import WorkflowRequest

class TestWorkflowExecutionEngine(unittest.TestCase):
    """Test cases for WorkflowExecutionEngine."""

    def setUp(self):
        """Set up test fixtures."""
        self.engine = WorkflowExecutionEngine()

    def tearDown(self):
        """Clean up test fixtures."""
        self.engine.stop()

    def test_engine_initialization(self):
        """Test engine initialization."""
        self.assertIsNotNone(self.engine.config)
        self.assertEqual(len(self.engine.active_executions), 0)
        self.assertEqual(len(self.engine.execution_queue), 0)
        self.assertEqual(len(self.engine.result_cache), 0)

    def test_submit_workflow(self):
        """Test workflow submission."""
        request = WorkflowRequest(
            mode="generate",
            workflow_name="test_workflow",
            params={"prompt": "test"}
        )

        task_id = self.engine.submit_workflow(request)
        self.assertIsInstance(task_id, str)
        self.assertEqual(len(self.engine.execution_queue), 1)

        execution = self.engine.execution_queue[0]
        self.assertEqual(execution.request, request)
        self.assertEqual(execution.status, WorkflowStatus.PENDING)

    def test_get_execution_status(self):
        """Test getting execution status."""
        # Test non-existent task
        status = self.engine.get_execution_status("nonexistent")
        self.assertIsNone(status)

        # Test existing task
        request = WorkflowRequest(mode="generate", workflow_name="test", params={})
        task_id = self.engine.submit_workflow(request)

        execution = self.engine.get_execution_status(task_id)
        self.assertIsNotNone(execution)
        self.assertEqual(execution.task_id, task_id)

    def test_cancel_execution(self):
        """Test execution cancellation."""
        request = WorkflowRequest(mode="generate", workflow_name="test", params={})
        task_id = self.engine.submit_workflow(request)

        # Cancel non-running execution
        cancelled = self.engine.cancel_execution(task_id)
        self.assertFalse(cancelled)  # Not running yet

        # Move to active executions
        execution = self.engine.execution_queue.pop(0)
        self.engine.active_executions[task_id] = execution
        execution.status = WorkflowStatus.RUNNING

        # Cancel running execution
        cancelled = self.engine.cancel_execution(task_id)
        self.assertTrue(cancelled)
        self.assertEqual(execution.status, WorkflowStatus.CANCELLED)

    @patch('comfy_extension.workflow_engine.WorkflowExecutionEngine._load_workflow_template')
    def test_prepare_workflow_generation(self, mock_load):
        """Test workflow preparation for generation."""
        workflow_data = {
            "1": {"class_type": "CLIPTextEncode", "_meta": {"title": "CLIP Text Encode (Prompt)"}, "inputs": {"text": ""}},
            "2": {"class_type": "EmptyLatentImage", "inputs": {"width": 512, "height": 512}},
            "3": {"class_type": "KSampler", "inputs": {"steps": 20, "cfg": 8}}
        }
        mock_load.return_value = workflow_data

        request = WorkflowRequest(
            mode="generate",
            workflow_name="test",
            params={
                "prompt": "beautiful landscape",
                "width": 1024,
                "height": 768,
                "steps": 30,
                "cfg": 10
            }
        )

        prepared = self.engine._prepare_workflow(workflow_data, request)

        # Check prompt was updated
        prompt_node = None
        for node in prepared.values():
            if node.get("class_type") == "CLIPTextEncode":
                prompt_node = node
                break

        self.assertIsNotNone(prompt_node)
        self.assertEqual(prompt_node["inputs"]["text"], "beautiful landscape")

        # Check dimensions were updated
        latent_node = None
        for node in prepared.values():
            if node.get("class_type") == "EmptyLatentImage":
                latent_node = node
                break

        self.assertIsNotNone(latent_node)
        self.assertEqual(latent_node["inputs"]["width"], 1024)
        self.assertEqual(latent_node["inputs"]["height"], 768)

    def test_generate_cache_key(self):
        """Test cache key generation."""
        request = WorkflowRequest(
            mode="generate",
            workflow_name="test_workflow",
            params={"prompt": "test", "steps": 20}
        )

        key1 = self.engine._generate_cache_key(request)
        key2 = self.engine._generate_cache_key(request)

        self.assertEqual(key1, key2)
        self.assertIsInstance(key1, str)

        # Different request should give different key
        request2 = WorkflowRequest(
            mode="generate",
            workflow_name="test_workflow",
            params={"prompt": "different", "steps": 20}
        )

        key3 = self.engine._generate_cache_key(request2)
        self.assertNotEqual(key1, key3)

if __name__ == '__main__':
    unittest.main()