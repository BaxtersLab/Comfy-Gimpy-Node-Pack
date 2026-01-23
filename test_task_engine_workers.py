#!/usr/bin/env python3
"""
Test script for the async task engine worker execution model.
"""

import sys
import os
import tempfile
import asyncio
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from task_engine import TaskManager, Task, TaskState, TaskPriority


async def test_image_processing_task():
    """Test image processing task."""
    print("Testing image processing task...")

    # Create a temporary image file for testing
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
        # Create a simple test image
        try:
            from PIL import Image
            img = Image.new('RGB', (100, 100), color='red')
            img.save(tmp_file.name)
            tmp_path = tmp_file.name
        except ImportError:
            print("PIL not available, skipping image processing test")
            return

    # Create temporary database
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_tasks.db"

        # Create task manager
        manager = TaskManager(db_path, temp_dir=temp_dir)
        print("✓ TaskManager created")

        # Start manager
        manager.start()
        print("✓ Task manager started")

        # Submit image processing task
        task_id = manager.submit_task(
            "image_resize",
            {
                "input_path": tmp_path,
                "output_path": str(Path(temp_dir) / "resized.png"),
                "params": {"width": 50, "height": 50}
            },
            priority=TaskPriority.NORMAL
        )
        print(f"✓ Image processing task submitted with ID: {task_id}")

        # Wait for task completion
        import time
        timeout = 30
        start_time = time.time()

        while time.time() - start_time < timeout:
            task = manager.get_task(task_id)
            if task and task.is_completed():
                print(f"✓ Task completed with state: {task.state}")
                if task.result and task.result.success:
                    print("✓ Image processing successful")
                    print(f"✓ Output files: {len(task.result.output_files)}")
                else:
                    print(f"✗ Task failed: {task.result.error_message if task.result else 'Unknown error'}")
                break
            time.sleep(0.5)
        else:
            print("✗ Task did not complete within timeout")

        # Stop manager
        manager.stop()
        print("✓ Task manager stopped")

        # Clean up
        try:
            os.unlink(tmp_path)
        except:
            pass


def test_resource_monitoring():
    """Test resource monitoring."""
    print("Testing resource monitoring...")

    from task_engine import ResourceMonitor
    monitor = ResourceMonitor()

    # Get initial stats
    resources = monitor.get_available_resources()
    print(f"✓ Available resources: CPU {resources['cpu_available']:.1f}%, Memory {resources['memory_available']:.1f}%")

    # Test resource checking
    requirements = {'cpu_percent': 50.0, 'memory_percent': 20.0}
    has_resources = monitor.has_sufficient_resources(requirements)
    print(f"✓ Sufficient resources for test requirements: {has_resources}")


def test_executor_selection():
    """Test executor selection logic."""
    print("Testing executor selection...")

    from task_engine import ComfyUIWorkflowExecutor, ModelDownloadExecutor, ImageProcessingExecutor

    # Test ComfyUI executor
    comfy_executor = ComfyUIWorkflowExecutor()
    task1 = Task(type="comfyui_workflow", parameters={})
    task2 = Task(type="image_generation", parameters={})
    task3 = Task(type="model_download", parameters={})

    print(f"✓ ComfyUI executor handles 'comfyui_workflow': {comfy_executor.can_execute(task1)}")
    print(f"✓ ComfyUI executor handles 'image_generation': {comfy_executor.can_execute(task2)}")
    print(f"✓ ComfyUI executor handles 'model_download': {comfy_executor.can_execute(task3)}")

    # Test model download executor
    model_executor = ModelDownloadExecutor(Path("./models"))
    print(f"✓ Model executor handles 'model_download': {model_executor.can_execute(task3)}")

    # Test image processing executor
    image_executor = ImageProcessingExecutor(Path("./temp"))
    task4 = Task(type="image_resize", parameters={})
    print(f"✓ Image executor handles 'image_resize': {image_executor.can_execute(task4)}")


async def main():
    """Run all tests."""
    print("Testing Comfy Gimpy Studio Task Engine - Worker Execution Model")
    print("=" * 60)

    test_resource_monitoring()
    print()

    test_executor_selection()
    print()

    await test_image_processing_task()
    print()

    print("✓ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())