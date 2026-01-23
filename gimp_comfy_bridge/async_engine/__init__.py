"""
Async Task Engine for Comfy Gimpy Studio.

This module provides asynchronous task execution capabilities for GIMP-ComfyUI integration,
including task queuing, worker management, progress tracking, and API endpoints.
"""

from .queue import TaskQueue
from .worker import TaskWorker
from .task import Task, TaskState, TaskPriority
from .api import (
    initialize,
    shutdown,
    submit_task,
    get_task_status,
    cancel_task,
    list_tasks,
    get_queue_stats
)
from .state import TaskStateManager
from .errors import TaskError, TaskTimeoutError, TaskCancelledError

__all__ = [
    'initialize',
    'shutdown',
    'TaskQueue',
    'TaskWorker',
    'Task',
    'TaskState',
    'TaskPriority',
    'submit_task',
    'get_task_status',
    'cancel_task',
    'list_tasks',
    'get_queue_stats',
    'TaskStateManager',
    'TaskError',
    'TaskTimeoutError',
    'TaskCancelledError'
]