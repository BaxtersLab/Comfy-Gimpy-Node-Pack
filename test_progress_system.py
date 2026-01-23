#!/usr/bin/env python3
"""
Test script for Phase 1.3 - Progress Tracking & Control implementation.
"""

import asyncio
import time
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from task_engine.manager import TaskManager
from task_engine.progress import RetryPolicy
from task_engine.task import TaskPriority


async def test_progress_tracking():
    """Test progress tracking functionality."""
    print("Testing Progress Tracking & Control Systems...")

    # Create task manager with web UI enabled
    storage_path = Path("./test_task_progress.db")
    manager = TaskManager(
        storage_path=storage_path,
        enable_web_ui=True,
        web_ui_host="localhost",
        web_ui_port=8080
    )

    try:
        # Start the manager
        manager.start()

        # Test 1: Submit a task with progress tracking
        print("\n1. Testing task submission with progress tracking...")

        task_id = manager.submit_task(
            task_type="image_process",
            parameters={
                "operation": "resize",
                "input_path": "test_image.jpg",
                "output_path": "output.jpg",
                "width": 800,
                "height": 600
            },
            priority=TaskPriority.NORMAL,
            timeout_seconds=30,
            metadata={"test": "progress_tracking"}
        )

        print(f"Submitted task: {task_id}")

        # Test 2: Monitor progress
        print("\n2. Monitoring task progress...")

        for i in range(10):
            progress = manager.get_task_progress(task_id)
            if progress:
                print(f"Progress: {progress['percentage']:.1f}% - {progress['stage']} - {progress['message']}")
            else:
                print("No progress information available yet")

            await asyncio.sleep(1)

        # Test 3: Test cancellation
        print("\n3. Testing task cancellation...")

        # Submit another task
        task_id2 = manager.submit_task(
            task_type="image_process",
            parameters={
                "operation": "convert",
                "input_path": "test.jpg",
                "output_path": "converted.png",
                "format": "PNG"
            },
            timeout_seconds=60
        )

        print(f"Submitted second task: {task_id2}")

        # Wait a bit then cancel
        await asyncio.sleep(2)

        cancelled = manager.cancel_task(task_id2)
        print(f"Task cancellation result: {cancelled}")

        # Test 4: Test retry functionality
        print("\n4. Testing retry functionality...")

        # Create a retry policy
        retry_policy = RetryPolicy(max_attempts=3, base_delay=1.0, max_delay=10.0)

        task_id3 = manager.submit_task(
            task_type="model_download",
            parameters={
                "model_url": "https://example.com/model.zip",
                "output_path": "./models/test_model.zip"
            },
            retry_policy=retry_policy,
            timeout_seconds=30
        )

        print(f"Submitted task with retry policy: {task_id3}")

        # Monitor for a while
        for i in range(15):
            task = manager.get_task(task_id3)
            if task:
                print(f"Task {task_id3} state: {task.state.value}")
                if task.state.value == "failed":
                    print("Task failed, testing retry...")
                    retry_success = manager.retry_task_with_policy(task_id3, retry_policy)
                    print(f"Retry result: {retry_success}")
                    break

            await asyncio.sleep(1)

        # Test 5: Check retry history
        print("\n5. Checking retry history...")

        retry_history = manager.get_retry_history(task_id3)
        print(f"Retry attempts for task {task_id3}: {len(retry_history)}")
        for attempt in retry_history:
            print(f"  Attempt {attempt['attempt_number']}: {attempt['exception']} (delay: {attempt['delay_used']}s)")

        # Test 6: Get statistics
        print("\n6. Getting task manager statistics...")

        stats = manager.get_stats()
        print("Task Manager Statistics:")
        print(f"  Queue size: {stats['queue_size']}")
        print(f"  Pending count: {stats['pending_count']}")
        print(f"  Running count: {stats['running_count']}")
        print(f"  Web UI enabled: {manager.enable_web_ui}")

        # Wait for tasks to complete
        print("\n7. Waiting for remaining tasks to complete...")
        await asyncio.sleep(5)

        # Get final task states
        all_tasks = manager.get_all_tasks()
        print(f"\nFinal task states ({len(all_tasks)} total):")
        for task in all_tasks:
            print(f"  {task.id}: {task.state.value} ({task.task_type})")

        print("\nProgress Tracking & Control test completed successfully!")

    finally:
        # Clean up
        await manager.stop_async()

        # Remove test database
        if storage_path.exists():
            storage_path.unlink()


async def test_web_ui():
    """Test web UI functionality."""
    print("\nTesting Web UI...")

    storage_path = Path("./test_web_ui.db")
    manager = TaskManager(
        storage_path=storage_path,
        enable_web_ui=True,
        web_ui_host="localhost",
        web_ui_port=8081  # Different port for testing
    )

    try:
        manager.start()

        # Submit a test task
        task_id = manager.submit_task(
            task_type="image_process",
            parameters={"operation": "resize", "width": 100, "height": 100},
            metadata={"web_ui_test": True}
        )

        print(f"Submitted task {task_id} for web UI testing")
        print("Web UI should be available at http://localhost:8081")
        print("Press Ctrl+C to stop...")

        # Keep running for manual testing
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping web UI test...")
    finally:
        await manager.stop_async()

        if storage_path.exists():
            storage_path.unlink()


def main():
    """Main test function."""
    print("Comfy Gimpy Studio v4.0 - Phase 1.3 Testing")
    print("=" * 50)

    # Test progress tracking
    asyncio.run(test_progress_tracking())

    # Optionally test web UI (commented out for automated testing)
    # print("\nStarting Web UI test (manual testing)...")
    # asyncio.run(test_web_ui())


if __name__ == "__main__":
    main()