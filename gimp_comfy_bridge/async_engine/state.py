"""
Task state management for the async task engine.
"""

from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


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
    error_details: Dict[str, Any] = None
    execution_time_seconds: float = 0.0

    def __post_init__(self):
        if self.error_details is None:
            self.error_details = {}


class TaskStateManager:
    """
    Manages task state transitions and validation.
    """

    # Valid state transitions
    VALID_TRANSITIONS = {
        TaskState.QUEUED: {TaskState.RUNNING, TaskState.CANCELLED},
        TaskState.RUNNING: {TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED, TaskState.TIMEOUT},
        TaskState.COMPLETED: set(),  # Terminal state
        TaskState.FAILED: set(),     # Terminal state
        TaskState.CANCELLED: set(),  # Terminal state
        TaskState.TIMEOUT: set(),    # Terminal state
    }

    @staticmethod
    def is_valid_transition(from_state: TaskState, to_state: TaskState) -> bool:
        """
        Check if a state transition is valid.

        Args:
            from_state: Current task state
            to_state: Target task state

        Returns:
            True if transition is valid
        """
        return to_state in TaskStateManager.VALID_TRANSITIONS.get(from_state, set())

    @staticmethod
    def is_terminal_state(state: TaskState) -> bool:
        """
        Check if a state is terminal (no further transitions allowed).

        Args:
            state: Task state to check

        Returns:
            True if state is terminal
        """
        return len(TaskStateManager.VALID_TRANSITIONS.get(state, set())) == 0

    @staticmethod
    def can_cancel(state: TaskState) -> bool:
        """
        Check if a task in the given state can be cancelled.

        Args:
            state: Current task state

        Returns:
            True if task can be cancelled
        """
        return state in {TaskState.QUEUED, TaskState.RUNNING}