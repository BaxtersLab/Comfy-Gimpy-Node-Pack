#!/usr/bin/env python3
"""
Minimal test for progress tracking components.
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from task_engine.progress import ProgressTracker, TaskController, RetryPolicy
    print("✓ Progress tracking imports successful")

    from task_engine.progress.retry import RetryManager
    print("✓ Retry manager imports successful")

    from task_engine.progress.web_ui import ProgressWebAPI
    print("✓ Web UI imports successful")

    from task_engine.manager import TaskManager
    print("✓ Task manager imports successful")

    # Test basic initialization
    progress_tracker = ProgressTracker()
    task_controller = TaskController(progress_tracker)
    retry_manager = RetryManager(task_controller, progress_tracker)

    print("✓ Component initialization successful")

    # Test retry policy
    policy = RetryPolicy(max_attempts=3, base_delay=1.0)
    print(f"✓ Retry policy created: {policy.max_attempts} attempts, {policy.base_delay}s base delay")

    print("\nAll progress tracking components initialized successfully!")

except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Initialization error: {e}")
    sys.exit(1)