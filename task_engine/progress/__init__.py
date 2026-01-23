"""
Progress tracking and control systems for the async task engine.
"""

import asyncio
import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..task import Task, TaskState, TaskProgress

logger = logging.getLogger(__name__)


@dataclass
class ProgressUpdate:
    """Represents a progress update event."""
    task_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    percentage: float = 0.0
    stage: str = ""
    message: str = ""
    eta_seconds: Optional[int] = None
    current_step: int = 0
    total_steps: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProgressCallback(ABC):
    """Abstract base class for progress callbacks."""

    @abstractmethod
    def on_progress_update(self, update: ProgressUpdate):
        """
        Called when task progress is updated.

        Args:
            update: Progress update information
        """
        pass

    @abstractmethod
    def on_task_started(self, task: Task):
        """
        Called when a task starts execution.

        Args:
            task: Task that started
        """
        pass

    @abstractmethod
    def on_task_completed(self, task: Task):
        """
        Called when a task completes (success or failure).

        Args:
            task: Task that completed
        """
        pass


class ProgressTracker:
    """
    Tracks progress for tasks and manages callbacks.
    """

    def __init__(self):
        self._callbacks: List[ProgressCallback] = []
        self._task_progress: Dict[str, TaskProgress] = {}
        self._lock = threading.RLock()

    def add_callback(self, callback: ProgressCallback):
        """
        Add a progress callback.

        Args:
            callback: Callback to add
        """
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

    def remove_callback(self, callback: ProgressCallback):
        """
        Remove a progress callback.

        Args:
            callback: Callback to remove
        """
        with self._lock:
            self._callbacks.remove(callback)

    def update_progress(self, task: Task, percentage: float, stage: str = "",
                       message: str = "", eta_seconds: Optional[int] = None,
                       current_step: int = 0, total_steps: int = 0,
                       metadata: Optional[Dict[str, Any]] = None):
        """
        Update task progress and notify callbacks.

        Args:
            task: Task being updated
            percentage: Progress percentage (0-100)
            stage: Current execution stage
            message: Progress message
            eta_seconds: Estimated time remaining in seconds
            current_step: Current step number
            total_steps: Total number of steps
            metadata: Additional progress metadata
        """
        # Update task progress
        task.update_progress(
            percentage=percentage,
            stage=stage,
            message=message,
            eta_seconds=eta_seconds,
            current_step=current_step,
            total_steps=total_steps
        )

        # Store progress snapshot
        with self._lock:
            self._task_progress[task.id] = TaskProgress(
                percentage=percentage,
                stage=stage,
                message=message,
                eta_seconds=eta_seconds,
                current_step=current_step,
                total_steps=total_steps
            )

        # Create progress update
        update = ProgressUpdate(
            task_id=task.id,
            percentage=percentage,
            stage=stage,
            message=message,
            eta_seconds=eta_seconds,
            current_step=current_step,
            total_steps=total_steps,
            metadata=metadata or {}
        )

        # Notify callbacks
        self._notify_progress_update(update)

    def get_progress(self, task_id: str) -> Optional[TaskProgress]:
        """
        Get current progress for a task.

        Args:
            task_id: Task ID

        Returns:
            Current progress, or None if not found
        """
        with self._lock:
            return self._task_progress.get(task_id)

    def notify_task_started(self, task: Task):
        """
        Notify callbacks that a task has started.

        Args:
            task: Task that started
        """
        with self._lock:
            for callback in self._callbacks:
                try:
                    callback.on_task_started(task)
                except Exception as e:
                    logger.error(f"Error in task started callback: {e}")

    def notify_task_completed(self, task: Task):
        """
        Notify callbacks that a task has completed.

        Args:
            task: Task that completed
        """
        with self._lock:
            # Clean up progress tracking
            self._task_progress.pop(task.id, None)

            for callback in self._callbacks:
                try:
                    callback.on_task_completed(task)
                except Exception as e:
                    logger.error(f"Error in task completed callback: {e}")

    def _notify_progress_update(self, update: ProgressUpdate):
        """
        Notify all callbacks of a progress update.

        Args:
            update: Progress update
        """
        with self._lock:
            for callback in self._callbacks:
                try:
                    callback.on_progress_update(update)
                except Exception as e:
                    logger.error(f"Error in progress callback: {e}")


class CancellationToken:
    """
    Token for cancelling operations.
    """

    def __init__(self):
        self._cancelled = False
        self._lock = threading.RLock()
        self._callbacks: List[Callable[[], None]] = []

    def cancel(self):
        """
        Cancel the operation.
        """
        with self._lock:
            if not self._cancelled:
                self._cancelled = True
                # Execute cleanup callbacks
                for callback in self._callbacks:
                    try:
                        callback()
                    except Exception as e:
                        logger.error(f"Error in cancellation callback: {e}")

    def is_cancelled(self) -> bool:
        """
        Check if operation is cancelled.

        Returns:
            True if cancelled
        """
        with self._lock:
            return self._cancelled

    def add_cleanup_callback(self, callback: Callable[[], None]):
        """
        Add a cleanup callback to execute when cancelled.

        Args:
            callback: Function to call on cancellation
        """
        with self._lock:
            self._callbacks.append(callback)

    async def wait_for_cancel(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for cancellation.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if cancelled, False if timeout
        """
        start_time = time.time()
        while not self.is_cancelled():
            if timeout and (time.time() - start_time) >= timeout:
                return False
            await asyncio.sleep(0.1)
        return True


class TimeoutManager:
    """
    Manages timeouts for operations.
    """

    def __init__(self):
        self._timeouts: Dict[str, asyncio.Task] = {}
        self._lock = threading.RLock()

    def set_timeout(self, operation_id: str, timeout_seconds: int,
                   callback: Callable[[], None]):
        """
        Set a timeout for an operation.

        Args:
            operation_id: Unique operation identifier
            timeout_seconds: Timeout duration in seconds
            callback: Function to call on timeout
        """
        async def timeout_task():
            try:
                await asyncio.sleep(timeout_seconds)
                with self._lock:
                    if operation_id in self._timeouts:
                        callback()
            except asyncio.CancelledError:
                pass  # Timeout was cancelled

        with self._lock:
            # Cancel existing timeout if any
            self.cancel_timeout(operation_id)

            # Create new timeout task
            task = asyncio.create_task(timeout_task())
            self._timeouts[operation_id] = task

    def cancel_timeout(self, operation_id: str):
        """
        Cancel a timeout for an operation.

        Args:
            operation_id: Operation identifier
        """
        with self._lock:
            if operation_id in self._timeouts:
                self._timeouts[operation_id].cancel()
                del self._timeouts[operation_id]

    def cancel_all(self):
        """
        Cancel all timeouts.
        """
        with self._lock:
            for task in self._timeouts.values():
                task.cancel()
            self._timeouts.clear()


class RetryPolicy:
    """
    Defines retry behavior for failed operations.
    """

    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0,
                 max_delay: float = 60.0, backoff_factor: float = 2.0):
        """
        Initialize retry policy.

        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            backoff_factor: Exponential backoff factor
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor

    def get_retry_delay(self, attempt: int) -> float:
        """
        Calculate delay for a retry attempt.

        Args:
            attempt: Retry attempt number (0-based)

        Returns:
            Delay in seconds
        """
        delay = self.base_delay * (self.backoff_factor ** attempt)
        return min(delay, self.max_delay)

    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """
        Determine if an operation should be retried.

        Args:
            attempt: Current retry attempt (0-based)
            exception: Exception that caused the failure

        Returns:
            True if should retry
        """
        if attempt >= self.max_attempts:
            return False

        # Don't retry certain types of errors
        if isinstance(exception, (KeyboardInterrupt, SystemExit)):
            return False

        # Retry network and temporary errors
        if isinstance(exception, (ConnectionError, TimeoutError, OSError)):
            return True

        # Retry on specific HTTP status codes (would need to check in calling code)
        return True  # Default to retry


class TaskController:
    """
    Controls task execution with cancellation, timeout, and retry support.
    """

    def __init__(self, progress_tracker: ProgressTracker):
        self.progress_tracker = progress_tracker
        self.timeout_manager = TimeoutManager()
        self._cancellation_tokens: Dict[str, CancellationToken] = {}
        self._lock = threading.RLock()

    def start_task(self, task: Task, retry_policy: Optional[RetryPolicy] = None) -> CancellationToken:
        """
        Start controlling a task execution.

        Args:
            task: Task to control
            retry_policy: Retry policy for the task

        Returns:
            Cancellation token for the task
        """
        with self._lock:
            # Create cancellation token
            cancel_token = CancellationToken()
            self._cancellation_tokens[task.id] = cancel_token

            # Set up timeout if specified
            if task.timeout_seconds:
                def on_timeout():
                    logger.warning(f"Task {task.id} timed out")
                    cancel_token.cancel()

                self.timeout_manager.set_timeout(task.id, task.timeout_seconds, on_timeout)

            # Set up cleanup callback
            def cleanup():
                self.timeout_manager.cancel_timeout(task.id)
                with self._lock:
                    self._cancellation_tokens.pop(task.id, None)

            cancel_token.add_cleanup_callback(cleanup)

            # Notify progress tracker
            self.progress_tracker.notify_task_started(task)

            return cancel_token

    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task.

        Args:
            task_id: Task ID to cancel

        Returns:
            True if task was cancelled
        """
        with self._lock:
            cancel_token = self._cancellation_tokens.get(task_id)
            if cancel_token:
                cancel_token.cancel()
                return True
            return False

    def complete_task(self, task: Task):
        """
        Mark a task as completed and clean up resources.

        Args:
            task: Completed task
        """
        with self._lock:
            # Clean up resources
            self.timeout_manager.cancel_timeout(task.id)
            self._cancellation_tokens.pop(task.id, None)

            # Notify progress tracker
            self.progress_tracker.notify_task_completed(task)

    def get_cancellation_token(self, task_id: str) -> Optional[CancellationToken]:
        """
        Get the cancellation token for a task.

        Args:
            task_id: Task ID

        Returns:
            Cancellation token, or None if not found
        """
        with self._lock:
            return self._cancellation_tokens.get(task_id)

    def is_cancelled(self, task_id: str) -> bool:
        """
        Check if a task is cancelled.

        Args:
            task_id: Task ID

        Returns:
            True if cancelled
        """
        with self._lock:
            cancel_token = self._cancellation_tokens.get(task_id)
            return cancel_token.is_cancelled() if cancel_token else False