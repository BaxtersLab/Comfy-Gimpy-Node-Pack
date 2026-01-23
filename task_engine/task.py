"""
Task definitions for the async task engine.
"""

import uuid
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List
from pathlib import Path


class TaskState(Enum):
    """Task execution states."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class TaskProgress:
    """Task progress information."""
    percentage: float = 0.0
    stage: str = ""
    message: str = ""
    eta_seconds: Optional[int] = None
    current_step: int = 0
    total_steps: int = 0


@dataclass
class TaskResult:
    """Task execution result."""
    success: bool
    data: Any = None
    error_message: str = ""
    error_details: Dict[str, Any] = field(default_factory=dict)
    output_files: List[Path] = field(default_factory=list)
    execution_time_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            'success': self.success,
            'data': self.data,
            'error_message': self.error_message,
            'error_details': self.error_details,
            'output_files': [str(p) for p in self.output_files],
            'execution_time_seconds': self.execution_time_seconds
        }


@dataclass
class Task:
    """
    Represents an asynchronous task in the system.

    Attributes:
        id: Unique task identifier
        type: Task type (e.g., 'comfyui_workflow', 'model_download', 'image_generation')
        priority: Task priority level
        state: Current task state
        parameters: Task-specific parameters
        progress: Current progress information
        result: Task execution result (when completed)
        created_at: Task creation timestamp
        started_at: Task start timestamp
        completed_at: Task completion timestamp
        timeout_seconds: Maximum execution time
        retry_count: Number of retries attempted
        max_retries: Maximum number of retries allowed
        dependencies: List of task IDs this task depends on
        metadata: Additional task metadata
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""
    priority: TaskPriority = TaskPriority.NORMAL
    state: TaskState = TaskState.QUEUED
    parameters: Dict[str, Any] = field(default_factory=dict)
    progress: TaskProgress = field(default_factory=TaskProgress)
    result: Optional[TaskResult] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeout_seconds: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate task after initialization."""
        if not self.type:
            raise ValueError("Task type cannot be empty")

    def is_completed(self) -> bool:
        """Check if task is in a terminal state."""
        return self.state in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED, TaskState.TIMEOUT]

    def is_running(self) -> bool:
        """Check if task is currently running."""
        return self.state == TaskState.RUNNING

    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return (self.state == TaskState.FAILED and
                self.retry_count < self.max_retries and
                not self.is_completed())

    def update_progress(self, percentage: float, stage: str = "", message: str = "",
                       eta_seconds: Optional[int] = None, current_step: int = 0,
                       total_steps: int = 0):
        """Update task progress."""
        self.progress.percentage = max(0.0, min(100.0, percentage))
        self.progress.stage = stage
        self.progress.message = message
        self.progress.eta_seconds = eta_seconds
        self.progress.current_step = current_step
        self.progress.total_steps = total_steps

    def mark_started(self):
        """Mark task as started."""
        self.state = TaskState.RUNNING
        self.started_at = datetime.now()

    def mark_completed(self, result: TaskResult):
        """Mark task as completed."""
        self.state = TaskState.COMPLETED
        self.result = result
        self.completed_at = datetime.now()

    def mark_failed(self, error_message: str, error_details: Dict[str, Any] = None):
        """Mark task as failed."""
        self.state = TaskState.FAILED
        self.result = TaskResult(
            success=False,
            error_message=error_message,
            error_details=error_details or {}
        )
        self.completed_at = datetime.now()

    def mark_cancelled(self):
        """Mark task as cancelled."""
        self.state = TaskState.CANCELLED
        self.completed_at = datetime.now()

    def mark_timeout(self):
        """Mark task as timed out."""
        self.state = TaskState.TIMEOUT
        self.completed_at = datetime.now()

    def increment_retry(self):
        """Increment retry count."""
        self.retry_count += 1

    def get_execution_time(self) -> Optional[float]:
        """Get total execution time in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for serialization."""
        return {
            'id': self.id,
            'type': self.type,
            'priority': self.priority.value,
            'state': self.state.value,
            'parameters': self.parameters,
            'progress': {
                'percentage': self.progress.percentage,
                'stage': self.progress.stage,
                'message': self.progress.message,
                'eta_seconds': self.progress.eta_seconds,
                'current_step': self.progress.current_step,
                'total_steps': self.progress.total_steps
            },
            'result': self.result.to_dict() if self.result else None,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'timeout_seconds': self.timeout_seconds,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'dependencies': self.dependencies,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create task from dictionary."""
        # Convert progress
        progress_data = data.get('progress', {})
        progress = TaskProgress(
            percentage=progress_data.get('percentage', 0.0),
            stage=progress_data.get('stage', ''),
            message=progress_data.get('message', ''),
            eta_seconds=progress_data.get('eta_seconds'),
            current_step=progress_data.get('current_step', 0),
            total_steps=progress_data.get('total_steps', 0)
        )

        # Convert result if present
        result = None
        if data.get('result'):
            result_data = data['result']
            result = TaskResult(
                success=result_data.get('success', False),
                data=result_data.get('data'),
                error_message=result_data.get('error_message', ''),
                error_details=result_data.get('error_details', {}),
                output_files=[Path(p) for p in result_data.get('output_files', [])],
                execution_time_seconds=result_data.get('execution_time_seconds', 0.0)
            )

        # Parse timestamps
        created_at = datetime.fromisoformat(data['created_at'])
        started_at = datetime.fromisoformat(data['started_at']) if data.get('started_at') else None
        completed_at = datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None

        return cls(
            id=data['id'],
            type=data['type'],
            priority=TaskPriority(data['priority']),
            state=TaskState(data['state']),
            parameters=data.get('parameters', {}),
            progress=progress,
            result=result,
            created_at=created_at,
            started_at=started_at,
            completed_at=completed_at,
            timeout_seconds=data.get('timeout_seconds'),
            retry_count=data.get('retry_count', 0),
            max_retries=data.get('max_retries', 3),
            dependencies=data.get('dependencies', []),
            metadata=data.get('metadata', {})
        )