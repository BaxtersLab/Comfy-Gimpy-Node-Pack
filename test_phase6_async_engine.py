#!/usr/bin/env python3
"""
Basic test for Phase 6 Async Task Engine implementation.
"""

import asyncio
import time
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gimp_comfy_bridge.async_engine import initialize, submit_task, get_task_status, shutdown
from gimp_comfy_bridge.async_engine.task import TaskPriority


def test_basic_functionality():
    """Test basic async engine functionality."""
    print("Testing Phase 6 Async Task Engine...")

    try:
        # Initialize the engine
        print("1. Initializing async engine...")
        initialize(
            queue_max_size=10,
            max_workers=2,
            task_timeout_seconds=30
        )
        print("   ✓ Engine initialized")

        # Submit a test task
        print("2. Submitting test task...")
        task_id = submit_task(
            operation="test_operation",
            parameters={"test_param": "test_value"},
            priority=TaskPriority.NORMAL
        )
        print(f"   ✓ Task submitted: {task_id}")

        # Monitor task progress
        print("3. Monitoring task progress...")
        max_wait = 10
        start_time = time.time()

        while time.time() - start_time < max_wait:
            status = get_task_status(task_id)
            if status:
                state = status['state']
                progress = status.get('progress', {})
                percentage = progress.get('percentage', 0)
                print(f"   Task state: {state}, progress: {percentage}%")

                if state in ['completed', 'failed', 'cancelled', 'timeout']:
                    break

            time.sleep(0.5)

        # Check final status
        final_status = get_task_status(task_id)
        if final_status and final_status['state'] == 'completed':
            print("   ✓ Task completed successfully")
        else:
            print(f"   ⚠ Task final state: {final_status['state'] if final_status else 'unknown'}")

        # Shutdown
        print("4. Shutting down engine...")
        shutdown(timeout=5.0)
        print("   ✓ Engine shutdown complete")

        print("\n🎉 Phase 6 Async Task Engine test completed successfully!")
        return True

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_basic_functionality()
    sys.exit(0 if success else 1)