"""
Custom exceptions for the async task engine.
"""


class TaskError(Exception):
    """Base exception for task-related errors."""

    def __init__(self, message: str, task_id: str = None, details: dict = None):
        super().__init__(message)
        self.task_id = task_id
        self.details = details or {}


class TaskTimeoutError(TaskError):
    """Raised when a task exceeds its timeout limit."""

    def __init__(self, task_id: str, timeout_seconds: int):
        message = f"Task {task_id} timed out after {timeout_seconds} seconds"
        super().__init__(message, task_id, {"timeout_seconds": timeout_seconds})


class TaskCancelledError(TaskError):
    """Raised when a task is cancelled."""

    def __init__(self, task_id: str, reason: str = "Task was cancelled"):
        super().__init__(reason, task_id, {"cancelled": True})


class TaskQueueFullError(TaskError):
    """Raised when the task queue is full."""

    def __init__(self, max_size: int):
        message = f"Task queue is full (max size: {max_size})"
        super().__init__(message, details={"max_size": max_size})


class TaskNotFoundError(TaskError):
    """Raised when a requested task is not found."""

    def __init__(self, task_id: str):
        message = f"Task {task_id} not found"
        super().__init__(message, task_id)


class TaskDependencyError(TaskError):
    """Raised when task dependencies cannot be satisfied."""

    def __init__(self, task_id: str, missing_dependencies: list):
        message = f"Task {task_id} has unsatisfied dependencies: {missing_dependencies}"
        super().__init__(message, task_id, {"missing_dependencies": missing_dependencies})


class TaskExecutionError(TaskError):
    """Raised when task execution fails."""

    def __init__(self, task_id: str, original_error: Exception):
        message = f"Task {task_id} execution failed: {str(original_error)}"
        super().__init__(message, task_id, {
            "original_error": str(original_error),
            "error_type": type(original_error).__name__
        })
        self.original_error = original_error