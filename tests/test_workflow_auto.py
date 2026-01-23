"""
Tests for Workflow Automation Engine (Phase 7)
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from gimp_comfy_bridge.workflow_auto import (
    WorkflowAutomationEngine,
    WorkflowTemplate,
    WorkflowStep,
    WorkflowExecution,
    WorkflowStatus,
    WorkflowResult
)
from shared.types import WorkflowInfo, StepInfo


class TestWorkflowStep:
    """Test the WorkflowStep class."""

    def test_step_creation(self):
        """Test creating a workflow step."""
        step = WorkflowStep(
            id="step1",
            name="Test Step",
            operation="gimp_operation",
            parameters={"param1": "value1"},
            dependencies=[]
        )

        assert step.id == "step1"
        assert step.name == "Test Step"
        assert step.operation == "gimp_operation"
        assert step.parameters == {"param1": "value1"}
        assert step.dependencies == []

    def test_step_with_dependencies(self):
        """Test step with dependencies."""
        step = WorkflowStep(
            id="step2",
            name="Dependent Step",
            operation="comfy_operation",
            parameters={"input": "from_step1"},
            dependencies=["step1"]
        )

        assert step.dependencies == ["step1"]

    def test_step_to_dict(self):
        """Test converting step to dictionary."""
        step = WorkflowStep(
            id="step1",
            name="Test Step",
            operation="test_op",
            parameters={"param": "value"},
            dependencies=[]
        )

        step_dict = step.to_dict()
        assert step_dict["id"] == "step1"
        assert step_dict["name"] == "Test Step"
        assert step_dict["operation"] == "test_op"


class TestWorkflowTemplate:
    """Test the WorkflowTemplate class."""

    def test_template_creation(self):
        """Test creating a workflow template."""
        steps = [
            WorkflowStep("step1", "Step 1", "op1", {}, []),
            WorkflowStep("step2", "Step 2", "op2", {}, ["step1"])
        ]

        template = WorkflowTemplate(
            id="test_workflow",
            name="Test Workflow",
            description="A test workflow",
            steps=steps,
            metadata={"version": "1.0"}
        )

        assert template.id == "test_workflow"
        assert template.name == "Test Workflow"
        assert len(template.steps) == 2
        assert template.metadata["version"] == "1.0"

    def test_template_validation(self):
        """Test template validation."""
        # Valid template
        valid_steps = [
            WorkflowStep("step1", "Step 1", "op1", {}, []),
            WorkflowStep("step2", "Step 2", "op2", {}, ["step1"])
        ]
        valid_template = WorkflowTemplate("valid", "Valid", "", valid_steps)

        assert valid_template.validate() is True

        # Invalid template - circular dependency
        invalid_steps = [
            WorkflowStep("step1", "Step 1", "op1", {}, ["step2"]),
            WorkflowStep("step2", "Step 2", "op2", {}, ["step1"])
        ]
        invalid_template = WorkflowTemplate("invalid", "Invalid", "", invalid_steps)

        assert invalid_template.validate() is False

    def test_template_to_dict(self):
        """Test converting template to dictionary."""
        steps = [WorkflowStep("step1", "Step 1", "op1", {}, [])]
        template = WorkflowTemplate("test", "Test", "Description", steps)

        template_dict = template.to_dict()
        assert template_dict["id"] == "test"
        assert template_dict["name"] == "Test"
        assert len(template_dict["steps"]) == 1


class TestWorkflowExecution:
    """Test the WorkflowExecution class."""

    def test_execution_creation(self):
        """Test creating a workflow execution."""
        execution = WorkflowExecution(
            id="exec1",
            template_id="template1",
            parameters={"input": "value"},
            status=WorkflowStatus.PENDING
        )

        assert execution.id == "exec1"
        assert execution.template_id == "template1"
        assert execution.status == WorkflowStatus.PENDING
        assert execution.current_step is None

    def test_execution_progress(self):
        """Test execution progress tracking."""
        execution = WorkflowExecution("exec1", "template1", {})

        # Start execution
        execution.start()
        assert execution.status == WorkflowStatus.RUNNING
        assert execution.started_at is not None

        # Complete execution
        execution.complete({"result": "success"})
        assert execution.status == WorkflowStatus.COMPLETED
        assert execution.result == {"result": "success"}
        assert execution.completed_at is not None

    def test_execution_failure(self):
        """Test execution failure handling."""
        execution = WorkflowExecution("exec1", "template1", {})

        execution.start()
        execution.fail("Test error")
        assert execution.status == WorkflowStatus.FAILED
        assert execution.error_message == "Test error"


class TestWorkflowAutomationEngine:
    """Test the workflow automation engine."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = WorkflowAutomationEngine()

        # Mock the async task engine
        self.mock_async_engine = Mock()
        self.engine.async_engine = self.mock_async_engine

    def test_engine_initialization(self):
        """Test engine initializes correctly."""
        assert len(self.engine.templates) == 0
        assert len(self.engine.executions) == 0

    def test_register_template(self):
        """Test registering a workflow template."""
        steps = [WorkflowStep("step1", "Step 1", "test_op", {}, [])]
        template = WorkflowTemplate("test_template", "Test", "", steps)

        self.engine.register_template(template)
        assert "test_template" in self.engine.templates

    def test_get_template(self):
        """Test getting a template."""
        steps = [WorkflowStep("step1", "Step 1", "test_op", {}, [])]
        template = WorkflowTemplate("test_template", "Test", "", steps)

        self.engine.register_template(template)
        retrieved = self.engine.get_template("test_template")
        assert retrieved == template

        # Test non-existent template
        assert self.engine.get_template("nonexistent") is None

    def test_execute_workflow(self):
        """Test executing a workflow."""
        # Create template
        steps = [
            WorkflowStep("step1", "Step 1", "async_op", {"param": "value"}, []),
            WorkflowStep("step2", "Step 2", "async_op2", {"param": "value2"}, ["step1"])
        ]
        template = WorkflowTemplate("test_workflow", "Test Workflow", "", steps)
        self.engine.register_template(template)

        # Mock async task submission
        self.mock_async_engine.submit_task = Mock(return_value="task_123")

        # Execute workflow
        execution_id = self.engine.execute_workflow("test_workflow", {"input": "test"})

        assert execution_id is not None
        assert execution_id in self.engine.executions

        execution = self.engine.executions[execution_id]
        assert execution.template_id == "test_workflow"
        assert execution.status == WorkflowStatus.RUNNING

    def test_get_execution_status(self):
        """Test getting execution status."""
        # Create and register template
        steps = [WorkflowStep("step1", "Step 1", "test_op", {}, [])]
        template = WorkflowTemplate("test", "Test", "", steps)
        self.engine.register_template(template)

        # Execute workflow
        execution_id = self.engine.execute_workflow("test", {})

        # Get status
        status = self.engine.get_execution_status(execution_id)
        assert status is not None
        assert status["id"] == execution_id
        assert status["status"] == "running"

    def test_cancel_execution(self):
        """Test canceling a workflow execution."""
        # Create and execute workflow
        steps = [WorkflowStep("step1", "Step 1", "test_op", {}, [])]
        template = WorkflowTemplate("test", "Test", "", steps)
        self.engine.register_template(template)

        execution_id = self.engine.execute_workflow("test", {})

        # Cancel execution
        cancelled = self.engine.cancel_execution(execution_id)
        assert cancelled is True

        execution = self.engine.executions[execution_id]
        assert execution.status == WorkflowStatus.CANCELLED

    def test_list_templates(self):
        """Test listing templates."""
        # Register multiple templates
        template1 = WorkflowTemplate("temp1", "Template 1", "", [])
        template2 = WorkflowTemplate("temp2", "Template 2", "", [])

        self.engine.register_template(template1)
        self.engine.register_template(template2)

        templates = self.engine.list_templates()
        assert len(templates) == 2
        assert all(isinstance(t, WorkflowInfo) for t in templates)

    def test_list_executions(self):
        """Test listing executions."""
        # Create executions
        steps = [WorkflowStep("step1", "Step 1", "test_op", {}, [])]
        template = WorkflowTemplate("test", "Test", "", steps)
        self.engine.register_template(template)

        exec1 = self.engine.execute_workflow("test", {})
        exec2 = self.engine.execute_workflow("test", {})

        executions = self.engine.list_executions()
        assert len(executions) >= 2  # May have more from other tests

    @patch('builtins.open')
    @patch('json.dump')
    def test_save_template_to_file(self, mock_json_dump, mock_open):
        """Test saving template to file."""
        steps = [WorkflowStep("step1", "Step 1", "test_op", {}, [])]
        template = WorkflowTemplate("test", "Test", "", steps)

        self.engine.save_template_to_file(template, "test.json")

        # Verify file operations
        mock_open.assert_called_once_with("test.json", 'w')
        mock_json_dump.assert_called_once()

    @patch('builtins.open')
    @patch('json.load')
    def test_load_template_from_file(self, mock_json_load, mock_open):
        """Test loading template from file."""
        # Mock file content
        mock_json_load.return_value = {
            "id": "loaded_template",
            "name": "Loaded Template",
            "description": "A loaded template",
            "steps": [{
                "id": "step1",
                "name": "Step 1",
                "operation": "test_op",
                "parameters": {},
                "dependencies": []
            }],
            "metadata": {}
        }

        template = self.engine.load_template_from_file("test.json")

        assert template.id == "loaded_template"
        assert template.name == "Loaded Template"
        assert len(template.steps) == 1

    def test_validate_workflow_dependencies(self):
        """Test workflow dependency validation."""
        # Valid dependencies
        steps = [
            WorkflowStep("step1", "Step 1", "op1", {}, []),
            WorkflowStep("step2", "Step 2", "op2", {}, ["step1"]),
            WorkflowStep("step3", "Step 3", "op3", {}, ["step1", "step2"])
        ]
        template = WorkflowTemplate("valid", "Valid", "", steps)

        assert self.engine._validate_dependencies(template) is True

        # Circular dependency
        circular_steps = [
            WorkflowStep("step1", "Step 1", "op1", {}, ["step3"]),
            WorkflowStep("step2", "Step 2", "op2", {}, ["step1"]),
            WorkflowStep("step3", "Step 3", "op3", {}, ["step2"])
        ]
        circular_template = WorkflowTemplate("circular", "Circular", "", circular_steps)

        assert self.engine._validate_dependencies(circular_template) is False

    def test_execution_result_conversion(self):
        """Test converting execution to WorkflowResult."""
        execution = WorkflowExecution("exec1", "template1", {})
        execution.status = WorkflowStatus.COMPLETED
        execution.result = {"output": "success"}

        result = self.engine._execution_to_result(execution)
        assert isinstance(result, WorkflowResult)
        assert result.execution_id == "exec1"
        assert result.status == "completed"
        assert result.result == {"output": "success"}