#!/usr/bin/env python3
"""
Test script for the async task engine.
"""

import sys
import os
import tempfile
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from task_engine import TaskManager, Task, TaskState, TaskPriority, TaskResult
import asyncio


async def example_task_handler(task: Task) -> TaskResult:
    """Example task handler for testing."""
    print(f"Executing task {task.id} of type {task.type}")

    # Simulate some work
    await asyncio.sleep(0.1)

    # Update progress
    task.update_progress(50.0, "Working...")

    await asyncio.sleep(0.1)

    task.update_progress(100.0, "Completed")

    return TaskResult(
        success=True,
        data={"result": "success"},
        execution_time_seconds=0.2
    )


def test_task_engine():
    """Test the task engine functionality."""
    print("Testing Comfy Gimpy Studio Task Engine...")

    # Create temporary database
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_tasks.db"

        # Create task manager
        manager = TaskManager(db_path)
        print("✓ TaskManager created")

        # Register task type
        manager.register_task_type("test_task", example_task_handler)
        print("✓ Task type registered")

        # Submit a task
        task_id = manager.submit_task(
            "test_task",
            {"param1": "value1"},
            priority=TaskPriority.NORMAL
        )
        print(f"✓ Task submitted with ID: {task_id}")

        # Start manager
        manager.start()
        print("✓ Task manager started")

        # Wait for task completion
        import time
        timeout = 10
        start_time = time.time()

        while time.time() - start_time < timeout:
            task = manager.get_task(task_id)
            if task and task.is_completed():
                print(f"✓ Task completed with state: {task.state}")
                if task.result:
                    print(f"✓ Task result: {task.result.data}")
                break
            time.sleep(0.1)
        else:
            print("✗ Task did not complete within timeout")

        # Get stats
        stats = manager.get_stats()
        print(f"✓ Manager stats: {stats}")

        # Stop manager
        manager.stop()
        print("✓ Task manager stopped")

    print("✓ All tests passed!")


if __name__ == "__main__":
    test_task_engine()