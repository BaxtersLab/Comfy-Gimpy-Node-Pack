"""
Task definitions for the async task engine.
"""

import uuid
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable, List
from pathlib import Path

from .state import TaskState, TaskPriority, TaskProgress, TaskResult


@dataclass
class Task:
    """
    Represents an asynchronous task.

    Attributes:
        id: Unique task identifier
        operation: Operation type (e.g., 'upscale', 'generate', 'inpaint')
        parameters: Operation parameters
        state: Current task state
        priority: Task priority level
        created_at: Task creation timestamp
        started_at: Task start timestamp (when moved to RUNNING)
        completed_at: Task completion timestamp
        timeout_seconds: Maximum execution time
        retry_count: Number of retries attempted
        max_retries: Maximum number of retries allowed
        progress: Current progress information
        result: Task execution result (when completed)
        callback_url: Optional webhook URL for completion notifications
        metadata: Additional task metadata
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operation: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    state: TaskState = TaskState.QUEUED
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeout_seconds: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3
    progress: TaskProgress = field(default_factory=TaskProgress)
    result: Optional[TaskResult] = None
    callback_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate task after initialization."""
        if not self.operation:
            raise ValueError("Task operation cannot be empty")

    @property
    def is_completed(self) -> bool:
        """Check if task is in a terminal state."""
        return self.state in {TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED, TaskState.TIMEOUT}

    @property
    def is_running(self) -> bool:
        """Check if task is currently running."""
        return self.state == TaskState.RUNNING

    @property
    def execution_time_seconds(self) -> Optional[float]:
        """Get total execution time in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.now() - self.started_at).total_seconds()
        return None

    @property
    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return (
            self.retry_count < self.max_retries
            and self.state in {TaskState.FAILED, TaskState.TIMEOUT}
        )

    def update_progress(self, percentage: float, stage: str = "", message: str = "",
                       eta_seconds: Optional[int] = None):
        """
        Update task progress.

        Args:
            percentage: Progress percentage (0-100)
            stage: Current execution stage
            message: Progress message
            eta_seconds: Estimated time remaining in seconds
        """
        self.progress.percentage = max(0.0, min(100.0, percentage))
        self.progress.stage = stage
        self.progress.message = message
        if eta_seconds is not None:
            self.progress.eta_seconds = eta_seconds

    def mark_started(self):
        """Mark task as started."""
        self.state = TaskState.RUNNING
        self.started_at = datetime.now()

    def mark_completed(self, result: TaskResult):
        """Mark task as completed with result."""
        self.state = TaskState.COMPLETED
        self.completed_at = datetime.now()
        self.result = result

    def mark_failed(self, error_message: str, error_details: Dict[str, Any] = None):
        """Mark task as failed."""
        self.state = TaskState.FAILED
        self.completed_at = datetime.now()
        self.result = TaskResult(
            success=False,
            error_message=error_message,
            error_details=error_details or {},
            execution_time_seconds=self.execution_time_seconds or 0.0
        )

    def mark_cancelled(self, reason: str = "Task was cancelled"):
        """Mark task as cancelled."""
        self.state = TaskState.CANCELLED
        self.completed_at = datetime.now()
        self.result = TaskResult(
            success=False,
            error_message=reason,
            error_details={"cancelled": True},
            execution_time_seconds=self.execution_time_seconds or 0.0
        )

    def mark_timeout(self):
        """Mark task as timed out."""
        self.state = TaskState.TIMEOUT
        self.completed_at = datetime.now()
        self.result = TaskResult(
            success=False,
            error_message=f"Task timed out after {self.timeout_seconds} seconds",
            error_details={"timeout": True, "timeout_seconds": self.timeout_seconds},
            execution_time_seconds=self.execution_time_seconds or 0.0
        )

    def increment_retry(self):
        """Increment retry count."""
        self.retry_count += 1
        self.state = TaskState.QUEUED  # Reset to queued for retry
        self.started_at = None
        self.completed_at = None
        self.result = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary representation."""
        return {
            "id": self.id,
            "operation": self.operation,
            "parameters": self.parameters,
            "state": self.state.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "progress": {
                "percentage": self.progress.percentage,
                "stage": self.progress.stage,
                "message": self.progress.message,
                "eta_seconds": self.progress.eta_seconds,
            },
            "result": self.result.__dict__ if self.result else None,
            "callback_url": self.callback_url,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create task from dictionary representation."""
        # Convert string timestamps back to datetime
        created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now()
        started_at = datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None
        completed_at = datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None

        # Reconstruct progress
        progress_data = data.get("progress", {})
        progress = TaskProgress(
            percentage=progress_data.get("percentage", 0.0),
            stage=progress_data.get("stage", ""),
            message=progress_data.get("message", ""),
            eta_seconds=progress_data.get("eta_seconds"),
        )

        # Reconstruct result if present
        result = None
        if data.get("result"):
            result_data = data["result"]
            result = TaskResult(
                success=result_data.get("success", False),
                data=result_data.get("data"),
                error_message=result_data.get("error_message", ""),
                error_details=result_data.get("error_details", {}),
                execution_time_seconds=result_data.get("execution_time_seconds", 0.0),
            )

        return cls(
            id=data["id"],
            operation=data["operation"],
            parameters=data.get("parameters", {}),
            state=TaskState(data["state"]),
            priority=TaskPriority(data.get("priority", 2)),
            created_at=created_at,
            started_at=started_at,
            completed_at=completed_at,
            timeout_seconds=data.get("timeout_seconds"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            progress=progress,
            result=result,
            callback_url=data.get("callback_url"),
            metadata=data.get("metadata", {}),
        )