"""
Tests for Async Task Engine (Phase 6)
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from concurrent.futures import ThreadPoolExecutor

from gimp_comfy_bridge.async_engine import (
    AsyncTaskEngine,
    Task,
    TaskPriority,
    TaskStatus,
    TaskResult
)
from shared.types import TaskInfo, QueueStats


class TestTask:
    """Test the Task class functionality."""

    def test_task_creation(self):
        """Test creating a task."""
        task = Task(
            id="test_task",
            operation="test_operation",
            parameters={"param1": "value1"},
            priority=TaskPriority.NORMAL
        )

        assert task.id == "test_task"
        assert task.operation == "test_operation"
        assert task.parameters == {"param1": "value1"}
        assert task.priority == TaskPriority.NORMAL
        assert task.status == TaskStatus.PENDING
        assert task.result is None
        assert task.error_message is None
        assert task.created_at is not None

    def test_task_to_dict(self):
        """Test converting task to dictionary."""
        task = Task(
            id="test_task",
            operation="test_operation",
            parameters={"param1": "value1"},
            priority=TaskPriority.HIGH
        )

        task_dict = task.to_dict()
        assert task_dict["id"] == "test_task"
        assert task_dict["operation"] == "test_operation"
        assert task_dict["status"] == "pending"
        assert task_dict["priority"] == "high"

    def test_task_from_dict(self):
        """Test creating task from dictionary."""
        task_dict = {
            "id": "test_task",
            "operation": "test_operation",
            "parameters": {"param1": "value1"},
            "priority": "high",
            "status": "running",
            "created_at": "2024-01-01T00:00:00"
        }

        task = Task.from_dict(task_dict)
        assert task.id == "test_task"
        assert task.operation == "test_operation"
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.RUNNING


class TestAsyncTaskEngine:
    """Test the async task engine functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = AsyncTaskEngine(
            queue_max_size=10,
            max_workers=2,
            task_timeout_seconds=30
        )

    def teardown_method(self):
        """Clean up test fixtures."""
        # Stop the engine if running
        if hasattr(self.engine, '_running') and self.engine._running:
            asyncio.run(self.engine.stop())

    @pytest.mark.asyncio
    async def test_engine_initialization(self):
        """Test engine initializes correctly."""
        assert self.engine.queue_max_size == 10
        assert self.engine.max_workers == 2
        assert self.engine.task_timeout_seconds == 30
        assert len(self.engine.tasks) == 0
        assert len(self.engine.completed_tasks) == 0

    @pytest.mark.asyncio
    async def test_start_stop_engine(self):
        """Test starting and stopping the engine."""
        await self.engine.start()
        assert self.engine._running is True

        await self.engine.stop()
        assert self.engine._running is False

    @pytest.mark.asyncio
    async def test_submit_task(self):
        """Test submitting a task."""
        await self.engine.start()

        # Mock operation function
        async def mock_operation(params):
            return {"result": "success", "input": params}

        # Register the operation
        self.engine.register_operation("test_op", mock_operation)

        # Submit task
        task_id = await self.engine.submit_task(
            operation="test_op",
            parameters={"test": "data"},
            priority=TaskPriority.NORMAL
        )

        assert task_id is not None
        assert task_id in self.engine.tasks

        # Wait for task completion
        await asyncio.sleep(0.1)

        # Check task completed
        task = self.engine.tasks[task_id]
        assert task.status == TaskStatus.COMPLETED
        assert task.result == {"result": "success", "input": {"test": "data"}}

        await self.engine.stop()

    @pytest.mark.asyncio
    async def test_task_priority_ordering(self):
        """Test that tasks are executed in priority order."""
        await self.engine.start()

        execution_order = []

        async def record_order(params):
            execution_order.append(params["id"])
            await asyncio.sleep(0.01)  # Small delay to ensure ordering
            return {"executed": params["id"]}

        self.engine.register_operation("record_op", record_order)

        # Submit tasks with different priorities
        await self.engine.submit_task("record_op", {"id": "low"}, TaskPriority.LOW)
        await self.engine.submit_task("record_op", {"id": "high"}, TaskPriority.HIGH)
        await self.engine.submit_task("record_op", {"id": "normal"}, TaskPriority.NORMAL)

        # Wait for all tasks to complete
        await asyncio.sleep(0.1)

        # High priority should execute first
        assert execution_order[0] == "high"

        await self.engine.stop()

    @pytest.mark.asyncio
    async def test_task_timeout(self):
        """Test task timeout functionality."""
        await self.engine.start()

        async def slow_operation(params):
            await asyncio.sleep(2)  # Longer than timeout
            return {"result": "too_late"}

        self.engine.register_operation("slow_op", slow_operation)

        # Submit task with short timeout
        engine_with_timeout = AsyncTaskEngine(
            queue_max_size=10,
            max_workers=2,
            task_timeout_seconds=0.1  # Very short timeout
        )
        await engine_with_timeout.start()

        engine_with_timeout.register_operation("slow_op", slow_operation)

        task_id = await engine_with_timeout.submit_task(
            operation="slow_op",
            parameters={"test": "timeout"}
        )

        # Wait for timeout
        await asyncio.sleep(0.2)

        task = engine_with_timeout.tasks[task_id]
        assert task.status == TaskStatus.FAILED
        assert "timeout" in task.error_message.lower()

        await engine_with_timeout.stop()
        await self.engine.stop()

    @pytest.mark.asyncio
    async def test_get_task_status(self):
        """Test getting task status."""
        await self.engine.start()

        async def quick_operation(params):
            return {"result": "done"}

        self.engine.register_operation("quick_op", quick_operation)

        task_id = await self.engine.submit_task("quick_op", {})

        # Get status
        status = await self.engine.get_task_status(task_id)
        assert status is not None
        assert status["id"] == task_id
        assert status["status"] in ["pending", "running", "completed"]

        await self.engine.stop()

    @pytest.mark.asyncio
    async def test_cancel_task(self):
        """Test canceling a task."""
        await self.engine.start()

        async def cancellable_operation(params):
            await asyncio.sleep(1)  # Long operation
            return {"result": "completed"}

        self.engine.register_operation("cancel_op", cancellable_operation)

        task_id = await self.engine.submit_task("cancel_op", {})

        # Cancel the task
        cancelled = await self.engine.cancel_task(task_id)
        assert cancelled is True

        # Check task status
        task = self.engine.tasks[task_id]
        assert task.status == TaskStatus.CANCELLED

        await self.engine.stop()

    @pytest.mark.asyncio
    async def test_queue_stats(self):
        """Test getting queue statistics."""
        await self.engine.start()

        stats = self.engine.get_queue_stats()
        assert isinstance(stats, QueueStats)
        assert stats.max_size == 10

        await self.engine.stop()

    @pytest.mark.asyncio
    async def test_operation_registration(self):
        """Test registering operations."""
        async def test_operation(params):
            return {"result": "test"}

        self.engine.register_operation("test_op", test_operation)
        assert "test_op" in self.engine.operations

        # Test unregistering
        self.engine.unregister_operation("test_op")
        assert "test_op" not in self.engine.operations

    @pytest.mark.asyncio
    async def test_task_result_conversion(self):
        """Test converting task results to TaskInfo."""
        task = Task(
            id="test_task",
            operation="test_op",
            parameters={"param": "value"}
        )
        task.status = TaskStatus.COMPLETED
        task.result = {"output": "success"}

        task_info = self.engine._task_to_task_info(task)
        assert isinstance(task_info, TaskInfo)
        assert task_info.id == "test_task"
        assert task_info.operation == "test_op"
        assert task_info.result == {"output": "success"}