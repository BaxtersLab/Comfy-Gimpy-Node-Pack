"""
Task queue implementation for the async task engine.
"""

import threading
import time
from collections import deque
from typing import List, Dict, Optional, Callable, Any
from datetime import datetime, timedelta

from .task import Task, TaskState, TaskPriority
from .errors import TaskQueueFullError, TaskNotFoundError


class TaskQueue:
    """
    Thread-safe FIFO task queue with priority support.

    Features:
    - Thread-safe operations
    - Priority queuing (URGENT > HIGH > NORMAL > LOW)
    - FIFO within same priority level
    - Maximum queue size limits
    - Task timeout handling
    """

    def __init__(self, max_size: int = 1000):
        """
        Initialize the task queue.

        Args:
            max_size: Maximum number of tasks in queue
        """
        self.max_size = max_size
        self._queues = {
            TaskPriority.URGENT: deque(),
            TaskPriority.HIGH: deque(),
            TaskPriority.NORMAL: deque(),
            TaskPriority.LOW: deque(),
        }
        self._tasks = {}  # task_id -> Task
        self._lock = threading.RLock()
        self._not_empty = threading.Condition(self._lock)
        self._not_full = threading.Condition(self._lock)

    def put(self, task: Task, block: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Put a task into the queue.

        Args:
            task: Task to add
            block: Whether to block if queue is full
            timeout: Maximum time to wait if blocking

        Returns:
            True if task was added, False otherwise

        Raises:
            TaskQueueFullError: If queue is full and not blocking
        """
        with self._not_full:
            if not block:
                if self.full():
                    raise TaskQueueFullError(self.max_size)
            elif timeout is not None:
                end_time = time.time() + timeout
                while self.full():
                    remaining = end_time - time.time()
                    if remaining <= 0:
                        raise TaskQueueFullError(self.max_size)
                    self._not_full.wait(remaining)
            else:
                while self.full():
                    self._not_full.wait()

            # Add task to appropriate priority queue
            self._queues[task.priority].append(task)
            self._tasks[task.id] = task

            self._not_empty.notify()
            return True

    def get(self, block: bool = True, timeout: Optional[float] = None) -> Optional[Task]:
        """
        Get a task from the queue (highest priority first).

        Args:
            block: Whether to block if queue is empty
            timeout: Maximum time to wait if blocking

        Returns:
            Next task to execute, or None if queue is empty
        """
        with self._not_empty:
            if not block:
                if self.empty():
                    return None
            elif timeout is not None:
                end_time = time.time() + timeout
                while self.empty():
                    remaining = end_time - time.time()
                    if remaining <= 0:
                        return None
                    self._not_empty.wait(remaining)
            else:
                while self.empty():
                    self._not_empty.wait()

            # Get task from highest priority queue
            for priority in [TaskPriority.URGENT, TaskPriority.HIGH, TaskPriority.NORMAL, TaskPriority.LOW]:
                if self._queues[priority]:
                    task = self._queues[priority].popleft()
                    return task

            return None  # Should not reach here if not empty

    def remove(self, task_id: str) -> bool:
        """
        Remove a task from the queue.

        Args:
            task_id: ID of task to remove

        Returns:
            True if task was removed, False if not found
        """
        with self._lock:
            if task_id not in self._tasks:
                return False

            task = self._tasks[task_id]
            # Remove from priority queue
            try:
                self._queues[task.priority].remove(task)
                del self._tasks[task_id]
                self._not_full.notify()
                return True
            except ValueError:
                # Task not in queue (shouldn't happen)
                del self._tasks[task_id]
                return False

    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by ID.

        Args:
            task_id: Task ID to look up

        Returns:
            Task if found, None otherwise
        """
        with self._lock:
            return self._tasks.get(task_id)

    def update_task(self, task: Task) -> bool:
        """
        Update a task in the queue.

        Args:
            task: Updated task

        Returns:
            True if task was updated, False if not found
        """
        with self._lock:
            if task.id not in self._tasks:
                return False
            self._tasks[task.id] = task
            return True

    def empty(self) -> bool:
        """Check if queue is empty."""
        with self._lock:
            return all(not q for q in self._queues.values())

    def full(self) -> bool:
        """Check if queue is full."""
        with self._lock:
            return len(self._tasks) >= self.max_size

    def qsize(self) -> int:
        """Get current queue size."""
        with self._lock:
            return len(self._tasks)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics.

        Returns:
            Dictionary with queue statistics
        """
        with self._lock:
            return {
                "size": len(self._tasks),
                "max_size": self.max_size,
                "urgent_count": len(self._queues[TaskPriority.URGENT]),
                "high_count": len(self._queues[TaskPriority.HIGH]),
                "normal_count": len(self._queues[TaskPriority.NORMAL]),
                "low_count": len(self._queues[TaskPriority.LOW]),
                "utilization_percent": (len(self._tasks) / self.max_size) * 100 if self.max_size > 0 else 0,
            }

    def cleanup_expired(self, max_age_seconds: int = 3600) -> int:
        """
        Remove tasks that have been in queue too long.

        Args:
            max_age_seconds: Maximum age of tasks to keep

        Returns:
            Number of tasks removed
        """
        with self._lock:
            cutoff_time = datetime.now() - timedelta(seconds=max_age_seconds)
            expired_tasks = []

            for task_id, task in self._tasks.items():
                if task.created_at < cutoff_time and task.state == TaskState.QUEUED:
                    expired_tasks.append(task_id)

            for task_id in expired_tasks:
                task = self._tasks[task_id]
                try:
                    self._queues[task.priority].remove(task)
                except ValueError:
                    pass  # Already removed
                del self._tasks[task_id]

            if expired_tasks:
                self._not_full.notify()

            return len(expired_tasks)

    def list_tasks(self, state: Optional[TaskState] = None, limit: Optional[int] = None) -> List[Task]:
        """
        List tasks in the queue.

        Args:
            state: Filter by task state (optional)
            limit: Maximum number of tasks to return (optional)

        Returns:
            List of tasks
        """
        with self._lock:
            tasks = list(self._tasks.values())

            if state is not None:
                tasks = [t for t in tasks if t.state == state]

            # Sort by priority (highest first) then by creation time (oldest first)
            tasks.sort(key=lambda t: (-t.priority.value, t.created_at))

            if limit is not None:
                tasks = tasks[:limit]

            return tasks