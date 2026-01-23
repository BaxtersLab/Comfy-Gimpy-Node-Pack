"""
Background worker implementation for the async task engine.
"""

import threading
import time
import logging
from typing import Callable, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime, timedelta

from .task import Task, TaskState
from .queue import TaskQueue
from .errors import TaskTimeoutError, TaskCancelledError, TaskExecutionError
from .state import TaskStateManager

logger = logging.getLogger(__name__)


class TaskWorker:
    """
    Background worker that processes tasks from a queue.

    Features:
    - Multi-threaded execution
    - Task timeout handling
    - Automatic retry logic
    - Progress callbacks
    - Graceful shutdown
    """

    def __init__(self,
                 task_queue: TaskQueue,
                 executor_factory: Callable[[Task], Callable[[], Any]],
                 max_workers: int = 4,
                 task_timeout_seconds: int = 300):
        """
        Initialize the task worker.

        Args:
            task_queue: Task queue to process
            executor_factory: Function that creates task executors
            max_workers: Maximum number of concurrent workers
            task_timeout_seconds: Default task timeout
        """
        self.task_queue = task_queue
        self.executor_factory = executor_factory
        self.max_workers = max_workers
        self.task_timeout_seconds = task_timeout_seconds

        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="TaskWorker")
        self._running = False
        self._shutdown_event = threading.Event()
        self._worker_thread = None
        self._active_tasks = {}  # task_id -> Future

    def start(self):
        """Start the worker thread."""
        if self._running:
            return

        self._running = True
        self._shutdown_event.clear()
        self._worker_thread = threading.Thread(target=self._worker_loop, name="TaskWorkerMain")
        self._worker_thread.daemon = True
        self._worker_thread.start()
        logger.info(f"Task worker started with {self.max_workers} workers")

    def stop(self, timeout: float = 30.0):
        """
        Stop the worker thread.

        Args:
            timeout: Maximum time to wait for graceful shutdown
        """
        if not self._running:
            return

        logger.info("Stopping task worker...")
        self._running = False
        self._shutdown_event.set()

        # Cancel all active tasks
        for task_id, future in self._active_tasks.items():
            if not future.done():
                future.cancel()
                logger.info(f"Cancelled active task {task_id}")

        # Wait for worker thread to finish
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout)

        # Shutdown executor
        self._executor.shutdown(wait=True)
        logger.info("Task worker stopped")

    def is_running(self) -> bool:
        """Check if worker is running."""
        return self._running

    def get_active_task_count(self) -> int:
        """Get number of currently active tasks."""
        return len([f for f in self._active_tasks.values() if not f.done()])

    def _worker_loop(self):
        """Main worker loop."""
        logger.info("Task worker loop started")

        while self._running and not self._shutdown_event.is_set():
            try:
                # Get next task from queue (with timeout to allow shutdown checks)
                task = self.task_queue.get(block=True, timeout=1.0)

                if task is None:
                    continue

                # Skip if task was cancelled while waiting
                if task.state == TaskState.CANCELLED:
                    logger.info(f"Skipping cancelled task {task.id}")
                    continue

                # Submit task for execution
                future = self._executor.submit(self._execute_task, task)
                self._active_tasks[task.id] = future

                # Clean up completed tasks
                self._cleanup_completed_tasks()

            except Exception as e:
                logger.error(f"Error in worker loop: {e}")

        logger.info("Task worker loop ended")

    def _execute_task(self, task: Task):
        """
        Execute a single task with timeout and retry logic.

        Args:
            task: Task to execute
        """
        try:
            # Mark task as started
            task.mark_started()
            self.task_queue.update_task(task)

            # Determine timeout
            timeout_seconds = task.timeout_seconds or self.task_timeout_seconds

            # Create executor
            executor = self.executor_factory(task)

            # Execute with timeout
            start_time = time.time()

            try:
                result = self._execute_with_timeout(executor, timeout_seconds)
                execution_time = time.time() - start_time

                # Mark as completed
                from .state import TaskResult
                task_result = TaskResult(
                    success=True,
                    data=result,
                    execution_time_seconds=execution_time
                )
                task.mark_completed(task_result)

                logger.info(f"Task {task.id} completed successfully in {execution_time:.2f}s")

            except TaskTimeoutError:
                task.mark_timeout()
                logger.warning(f"Task {task.id} timed out after {timeout_seconds}s")

            except TaskCancelledError:
                task.mark_cancelled()
                logger.info(f"Task {task.id} was cancelled")

            except Exception as e:
                # Check if we can retry
                if task.can_retry:
                    logger.warning(f"Task {task.id} failed, retrying ({task.retry_count + 1}/{task.max_retries}): {e}")
                    task.increment_retry()
                    # Re-queue the task
                    self.task_queue.put(task)
                else:
                    task.mark_failed(str(e), {"exception_type": type(e).__name__})
                    logger.error(f"Task {task.id} failed permanently: {e}")

        except Exception as e:
            logger.error(f"Unexpected error executing task {task.id}: {e}")
            task.mark_failed(f"Unexpected error: {e}", {"unexpected_error": True})

        finally:
            # Update task in queue
            self.task_queue.update_task(task)

            # Remove from active tasks
            self._active_tasks.pop(task.id, None)

    def _execute_with_timeout(self, executor: Callable[[], Any], timeout_seconds: int) -> Any:
        """
        Execute a function with timeout.

        Args:
            executor: Function to execute
            timeout_seconds: Timeout in seconds

        Returns:
            Execution result

        Raises:
            TaskTimeoutError: If execution times out
        """
        result = [None]
        exception = [None]

        def target():
            try:
                result[0] = executor()
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout_seconds)

        if thread.is_alive():
            # Timeout occurred
            raise TaskTimeoutError("task_timeout", timeout_seconds)

        if exception[0]:
            raise exception[0]

        return result[0]

    def _cleanup_completed_tasks(self):
        """Clean up completed tasks from active tasks dict."""
        completed = [task_id for task_id, future in self._active_tasks.items() if future.done()]
        for task_id in completed:
            del self._active_tasks[task_id]

    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.

        Args:
            task_id: ID of task to cancel

        Returns:
            True if task was cancelled, False otherwise
        """
        task = self.task_queue.get_task(task_id)
        if not task:
            return False

        if not TaskStateManager.can_cancel(task.state):
            return False

        # Mark task as cancelled
        task.mark_cancelled()
        self.task_queue.update_task(task)

        # Cancel the future if it's running
        future = self._active_tasks.get(task_id)
        if future and not future.done():
            future.cancel()

        logger.info(f"Cancelled task {task_id}")
        return True