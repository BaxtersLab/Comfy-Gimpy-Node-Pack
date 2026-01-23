"""
Task queue implementation for the async task engine.
"""

import heapq
import threading
import time
from typing import List, Dict, Set, Optional, Callable
from collections import defaultdict

from .task import Task, TaskState, TaskPriority


class TaskQueue:
    """
    Priority-based task queue with dependency management.

    Features:
    - Priority queuing (HIGH > NORMAL > LOW)
    - FIFO within same priority
    - Task dependency resolution
    - Thread-safe operations
    """

    def __init__(self):
        self._queue = []  # Priority queue: (priority, timestamp, task_id)
        self._tasks = {}  # task_id -> Task
        self._dependencies = defaultdict(set)  # task_id -> set of dependent task_ids
        self._reverse_dependencies = defaultdict(set)  # task_id -> set of tasks that depend on it
        self._lock = threading.RLock()
        self._next_timestamp = 0

    def add_task(self, task: Task) -> bool:
        """
        Add a task to the queue.

        Args:
            task: Task to add

        Returns:
            True if task was added, False if dependencies not satisfied
        """
        with self._lock:
            if task.id in self._tasks:
                return False  # Task already exists

            # Check if all dependencies are completed
            if not self._are_dependencies_satisfied(task):
                return False

            # Add task to storage
            self._tasks[task.id] = task

            # Register dependencies
            for dep_id in task.dependencies:
                self._reverse_dependencies[dep_id].add(task.id)

            # Add to priority queue
            # Use negative priority for max-heap behavior (higher priority = smaller number)
            priority_value = -task.priority.value
            timestamp = self._next_timestamp
            self._next_timestamp += 1

            heapq.heappush(self._queue, (priority_value, timestamp, task.id))

            return True

    def get_next_task(self) -> Optional[Task]:
        """
        Get the next task to execute.

        Returns:
            Next task to execute, or None if no tasks available
        """
        with self._lock:
            while self._queue:
                priority_value, timestamp, task_id = heapq.heappop(self._queue)

                if task_id not in self._tasks:
                    continue  # Task was removed

                task = self._tasks[task_id]

                # Double-check dependencies (in case they changed)
                if not self._are_dependencies_satisfied(task):
                    # Re-queue the task
                    heapq.heappush(self._queue, (priority_value, timestamp, task_id))
                    continue

                # Check if task is still in queued state
                if task.state != TaskState.QUEUED:
                    continue

                return task

            return None

    def remove_task(self, task_id: str) -> Optional[Task]:
        """
        Remove a task from the queue.

        Args:
            task_id: ID of task to remove

        Returns:
            Removed task, or None if not found
        """
        with self._lock:
            if task_id not in self._tasks:
                return None

            task = self._tasks[task_id]

            # Remove from dependencies
            for dep_id in task.dependencies:
                self._reverse_dependencies[dep_id].discard(task_id)

            # Remove from queue (by rebuilding without this task)
            self._rebuild_queue_without_task(task_id)

            del self._tasks[task_id]

            return task

    def update_task_state(self, task_id: str, new_state: TaskState):
        """
        Update task state and handle dependency notifications.

        Args:
            task_id: Task ID
            new_state: New task state
        """
        with self._lock:
            if task_id not in self._tasks:
                return

            task = self._tasks[task_id]
            old_state = task.state
            task.state = new_state

            # If task completed, notify dependent tasks
            if new_state == TaskState.COMPLETED and old_state != TaskState.COMPLETED:
                self._notify_dependents(task_id)

    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task if found, None otherwise
        """
        with self._lock:
            return self._tasks.get(task_id)

    def get_all_tasks(self) -> List[Task]:
        """
        Get all tasks in the queue.

        Returns:
            List of all tasks
        """
        with self._lock:
            return list(self._tasks.values())

    def get_queued_tasks(self) -> List[Task]:
        """
        Get all queued tasks.

        Returns:
            List of queued tasks
        """
        with self._lock:
            return [task for task in self._tasks.values() if task.state == TaskState.QUEUED]

    def get_running_tasks(self) -> List[Task]:
        """
        Get all running tasks.

        Returns:
            List of running tasks
        """
        with self._lock:
            return [task for task in self._tasks.values() if task.state == TaskState.RUNNING]

    def clear_completed_tasks(self) -> int:
        """
        Remove all completed tasks from the queue.

        Returns:
            Number of tasks removed
        """
        with self._lock:
            completed_tasks = [task_id for task_id, task in self._tasks.items()
                             if task.is_completed()]

            for task_id in completed_tasks:
                task = self._tasks[task_id]
                # Clean up dependencies
                for dep_id in task.dependencies:
                    self._reverse_dependencies[dep_id].discard(task_id)
                del self._tasks[task_id]

            return len(completed_tasks)

    def get_queue_size(self) -> int:
        """
        Get the number of tasks in the queue.

        Returns:
            Number of tasks
        """
        with self._lock:
            return len(self._tasks)

    def get_pending_count(self) -> int:
        """
        Get the number of pending (queued) tasks.

        Returns:
            Number of pending tasks
        """
        with self._lock:
            return len([task for task in self._tasks.values() if task.state == TaskState.QUEUED])

    def _are_dependencies_satisfied(self, task: Task) -> bool:
        """
        Check if all dependencies of a task are satisfied.

        Args:
            task: Task to check

        Returns:
            True if all dependencies are completed
        """
        for dep_id in task.dependencies:
            dep_task = self._tasks.get(dep_id)
            if not dep_task or not dep_task.is_completed():
                return False
        return True

    def _notify_dependents(self, task_id: str):
        """
        Notify dependent tasks that a dependency has been completed.

        Args:
            task_id: ID of completed task
        """
        dependent_ids = self._reverse_dependencies.get(task_id, set()).copy()

        for dep_task_id in dependent_ids:
            if dep_task_id in self._tasks:
                # Check if dependent task can now be queued
                dep_task = self._tasks[dep_task_id]
                if (dep_task.state == TaskState.QUEUED and
                    self._are_dependencies_satisfied(dep_task)):
                    # Re-queue the dependent task with high priority
                    self._requeue_task(dep_task_id, TaskPriority.HIGH)

    def _rebuild_queue_without_task(self, task_id: str):
        """
        Rebuild the priority queue without a specific task.

        Args:
            task_id: Task ID to exclude
        """
        # Filter out the task from the queue
        new_queue = []
        for item in self._queue:
            if item[2] != task_id:  # item[2] is task_id
                new_queue.append(item)

        # Rebuild heap
        heapq.heapify(new_queue)
        self._queue = new_queue

    def _requeue_task(self, task_id: str, priority: TaskPriority = None):
        """
        Re-queue a task with optional priority boost.

        Args:
            task_id: Task ID to re-queue
            priority: New priority (optional)
        """
        if task_id not in self._tasks:
            return

        task = self._tasks[task_id]
        if priority:
            task.priority = priority

        # Remove from current queue position
        self._rebuild_queue_without_task(task_id)

        # Re-add to queue
        priority_value = -task.priority.value
        timestamp = self._next_timestamp
        self._next_timestamp += 1

        heapq.heappush(self._queue, (priority_value, timestamp, task_id))