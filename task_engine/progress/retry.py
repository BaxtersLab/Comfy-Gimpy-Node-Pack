"""
Retry mechanism implementation for the async task engine.
"""

import asyncio
import logging
import time
from typing import Callable, Any, Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime

from . import RetryPolicy, TaskController, ProgressTracker
from ..task import Task, TaskState

logger = logging.getLogger(__name__)


@dataclass
class RetryAttempt:
    """Represents a single retry attempt."""
    attempt_number: int
    timestamp: datetime
    exception: Exception
    delay_used: float


class RetryManager:
    """
    Manages retry logic for failed tasks.
    """

    def __init__(self, task_controller: TaskController, progress_tracker: ProgressTracker):
        """
        Initialize retry manager.

        Args:
            task_controller: Task controller instance
            progress_tracker: Progress tracker instance
        """
        self.task_controller = task_controller
        self.progress_tracker = progress_tracker
        self._retry_attempts: Dict[str, List[RetryAttempt]] = {}
        self._lock = asyncio.Lock()

    async def execute_with_retry(self, task: Task, operation: Callable[[Task], Any],
                                retry_policy: Optional[RetryPolicy] = None) -> Any:
        """
        Execute an operation with retry logic.

        Args:
            task: Task being executed
            operation: Operation to execute (should be async)
            retry_policy: Retry policy to use

        Returns:
            Operation result

        Raises:
            Exception: Last exception if all retries exhausted
        """
        if not retry_policy:
            retry_policy = RetryPolicy()

        attempt = 0
        last_exception = None

        while attempt <= retry_policy.max_attempts:
            try:
                # Check for cancellation before each attempt
                if self.task_controller.is_cancelled(task.id):
                    raise asyncio.CancelledError("Task was cancelled")

                # Execute operation
                result = await operation(task)

                # Success - clear retry history
                async with self._lock:
                    self._retry_attempts.pop(task.id, None)

                return result

            except Exception as e:
                last_exception = e
                attempt += 1

                # Record retry attempt
                retry_attempt = RetryAttempt(
                    attempt_number=attempt,
                    timestamp=datetime.now(),
                    exception=e,
                    delay_used=0.0
                )

                async with self._lock:
                    if task.id not in self._retry_attempts:
                        self._retry_attempts[task.id] = []
                    self._retry_attempts[task.id].append(retry_attempt)

                # Check if we should retry
                if attempt > retry_policy.max_attempts or not retry_policy.should_retry(attempt - 1, e):
                    logger.error(f"Task {task.id} failed after {attempt} attempts: {e}")
                    break

                # Calculate delay
                delay = retry_policy.get_retry_delay(attempt - 1)
                retry_attempt.delay_used = delay

                # Update progress
                self.progress_tracker.update_progress(
                    task=task,
                    percentage=max(0, task.progress.percentage - 10),  # Slight rollback
                    stage=f"Retrying (attempt {attempt}/{retry_policy.max_attempts + 1})",
                    message=f"Failed: {str(e)}. Retrying in {delay:.1f}s...",
                    metadata={"retry_attempt": attempt, "last_error": str(e)}
                )

                logger.warning(f"Task {task.id} failed (attempt {attempt}), retrying in {delay}s: {e}")

                # Wait before retry
                await asyncio.sleep(delay)

        # All retries exhausted
        async with self._lock:
            attempts = self._retry_attempts.get(task.id, [])
            task.retry_history = attempts

        raise last_exception

    def get_retry_history(self, task_id: str) -> List[RetryAttempt]:
        """
        Get retry history for a task.

        Args:
            task_id: Task ID

        Returns:
            List of retry attempts
        """
        async with self._lock:
            return self._retry_attempts.get(task_id, []).copy()

    def clear_retry_history(self, task_id: str):
        """
        Clear retry history for a task.

        Args:
            task_id: Task ID
        """
        async with self._lock:
            self._retry_attempts.pop(task_id, None)


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for fault tolerance.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0,
                 expected_exception: Exception = Exception):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before trying to close circuit
            expected_exception: Type of exception to count as failure
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._failure_count = 0
        self._last_failure_time = None
        self._state = "closed"  # closed, open, half_open
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs):
        """
        Execute function through circuit breaker.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpen: If circuit is open
            Exception: Original exception from function
        """
        async with self._lock:
            if self._state == "open":
                if self._should_attempt_reset():
                    self._state = "half_open"
                else:
                    raise CircuitBreakerOpen("Circuit breaker is open")

            try:
                result = await func(*args, **kwargs)
                await self._on_success()
                return result
            except self.expected_exception as e:
                await self._on_failure()
                raise e

    async def _on_success(self):
        """Handle successful execution."""
        if self._state == "half_open":
            self._state = "closed"
            self._failure_count = 0
            self._last_failure_time = None

    async def _on_failure(self):
        """Handle failed execution."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.failure_threshold:
            self._state = "open"

    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit."""
        if self._last_failure_time is None:
            return True

        return (time.time() - self._last_failure_time) >= self.recovery_timeout

    @property
    def state(self) -> str:
        """Get current circuit breaker state."""
        return self._state

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class ExponentialBackoff:
    """
    Exponential backoff utility for retry delays.
    """

    @staticmethod
    def calculate_delay(attempt: int, base_delay: float = 1.0,
                       max_delay: float = 300.0, backoff_factor: float = 2.0,
                       jitter: bool = True) -> float:
        """
        Calculate exponential backoff delay.

        Args:
            attempt: Attempt number (0-based)
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            backoff_factor: Backoff multiplier
            jitter: Whether to add random jitter

        Returns:
            Delay in seconds
        """
        delay = base_delay * (backoff_factor ** attempt)

        if jitter:
            import random
            # Add up to 25% jitter
            jitter_amount = delay * 0.25 * random.random()
            delay += jitter_amount

        return min(delay, max_delay)

    @staticmethod
    def calculate_jittered_delay(attempt: int, base_delay: float = 1.0,
                                max_delay: float = 300.0, backoff_factor: float = 2.0) -> float:
        """
        Calculate delay with jitter (convenience method).

        Args:
            attempt: Attempt number (0-based)
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            backoff_factor: Backoff multiplier

        Returns:
            Delay in seconds with jitter
        """
        return ExponentialBackoff.calculate_delay(
            attempt, base_delay, max_delay, backoff_factor, jitter=True
        )