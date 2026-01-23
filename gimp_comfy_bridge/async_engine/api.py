"""
API functions for the async task engine.
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

from .task import Task, TaskState, TaskPriority
from .queue import TaskQueue
from .worker import TaskWorker
from .errors import TaskNotFoundError, TaskQueueFullError
from .state import TaskStateManager

# Import remote execution components
try:
    from ..remote import RemoteNodeManager, RemoteTaskExecutor
    _remote_manager: Optional[RemoteNodeManager] = None
    _remote_executor: Optional[RemoteTaskExecutor] = None
    _REMOTE_AVAILABLE = True
except ImportError:
    _remote_manager = None
    _remote_executor = None
    _REMOTE_AVAILABLE = False
    logger.warning("Remote execution components not available")

logger = logging.getLogger(__name__)

# Global instances (would be managed by a proper DI container in production)
_task_queue: Optional[TaskQueue] = None
_task_worker: Optional[TaskWorker] = None
_executor_factory: Optional[Callable[[Task], Callable[[], Any]]] = None


def initialize(queue_max_size: int = 1000,
               max_workers: int = 4,
               task_timeout_seconds: int = 300,
               executor_factory: Optional[Callable[[Task], Callable[[], Any]]] = None,
               enable_remote: bool = True):
    """
    Initialize the async task engine.

    Args:
        queue_max_size: Maximum queue size
        max_workers: Maximum number of worker threads
        task_timeout_seconds: Default task timeout
        executor_factory: Factory function for task executors
        enable_remote: Whether to enable remote execution
    """
    global _task_queue, _task_worker, _executor_factory, _remote_manager, _remote_executor

    _executor_factory = executor_factory or _default_executor_factory
    _task_queue = TaskQueue(max_size=queue_max_size)
    _task_worker = TaskWorker(
        task_queue=_task_queue,
        executor_factory=_executor_factory,
        max_workers=max_workers,
        task_timeout_seconds=task_timeout_seconds
    )

    _task_worker.start()

    # Initialize remote components if available and enabled
    if enable_remote and _REMOTE_AVAILABLE:
        try:
            from ..shared.config import ConfigManager
            config_manager = ConfigManager()

            _remote_manager = RemoteNodeManager(config_manager)
            _remote_executor = RemoteTaskExecutor(_remote_manager, _task_queue)

            logger.info("Remote execution components initialized")
        except Exception as e:
            logger.error(f"Failed to initialize remote components: {e}")
            _remote_manager = None
            _remote_executor = None

    logger.info("Async task engine initialized")


def shutdown(timeout: float = 30.0):
    """
    Shutdown the async task engine.

    Args:
        timeout: Shutdown timeout in seconds
    """
    global _task_queue, _task_worker, _remote_manager, _remote_executor

    if _task_worker:
        _task_worker.stop(timeout)

    # Shutdown remote components
    if _remote_executor:
        _remote_executor.stop()
    if _remote_manager:
        _remote_manager.stop()

    _task_queue = None
    _task_worker = None
    _remote_manager = None
    _remote_executor = None
    logger.info("Async task engine shutdown")


def submit_task(operation: str,
                parameters: Dict[str, Any],
                priority: TaskPriority = TaskPriority.NORMAL,
                timeout_seconds: Optional[int] = None,
                callback_url: Optional[str] = None,
                metadata: Optional[Dict[str, Any]] = None,
                force_local: bool = False) -> str:
    """
    Submit a task for execution.

    Args:
        operation: Operation type (e.g., 'upscale', 'generate')
        parameters: Operation parameters
        priority: Task priority
        timeout_seconds: Task timeout (overrides default)
        callback_url: Webhook URL for completion notifications
        metadata: Additional task metadata
        force_local: Force local execution even if remote nodes are available

    Returns:
        Task ID

    Raises:
        TaskQueueFullError: If queue is full
    """
    if not _task_queue:
        raise RuntimeError("Task engine not initialized")

    task = Task(
        operation=operation,
        parameters=parameters,
        priority=priority,
        timeout_seconds=timeout_seconds,
        callback_url=callback_url,
        metadata=metadata or {}
    )

    # Check if remote execution is available and not forced local
    if not force_local and _remote_executor and _remote_executor.can_execute_remotely(task):
        try:
            remote_task_id = _remote_executor.submit_remote_task(task)
            logger.info(f"Submitted task {task.id} to remote execution")
            return remote_task_id
        except Exception as e:
            logger.warning(f"Remote execution failed, falling back to local: {e}")

    # Local execution
    _task_queue.put(task)
    logger.info(f"Submitted task {task.id} for local execution")
    return task.id


def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the status of a task.

    Args:
        task_id: Task ID

    Returns:
        Task status dictionary, or None if not found
    """
    if not _task_queue:
        raise RuntimeError("Task engine not initialized")

    task = _task_queue.get_task(task_id)
    if not task:
        return None

    return {
        "id": task.id,
        "operation": task.operation,
        "state": task.state.value,
        "priority": task.priority.value,
        "created_at": task.created_at.isoformat(),
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "progress": {
            "percentage": task.progress.percentage,
            "stage": task.progress.stage,
            "message": task.progress.message,
            "eta_seconds": task.progress.eta_seconds,
        },
        "result": task.result.__dict__ if task.result else None,
        "retry_count": task.retry_count,
        "max_retries": task.max_retries,
        "execution_time_seconds": task.execution_time_seconds,
    }


def cancel_task(task_id: str) -> bool:
    """
    Cancel a task.

    Args:
        task_id: Task ID to cancel

    Returns:
        True if task was cancelled, False otherwise
    """
    if not _task_queue or not _task_worker:
        raise RuntimeError("Task engine not initialized")

    task = _task_queue.get_task(task_id)
    if not task:
        return False

    if not TaskStateManager.can_cancel(task.state):
        return False

    # Try to cancel via worker first (for running tasks)
    if _task_worker.cancel_task(task_id):
        return True

    # If not running, just mark as cancelled in queue
    task.mark_cancelled()
    _task_queue.update_task(task)
    logger.info(f"Cancelled task {task_id}")
    return True


def list_tasks(state: Optional[TaskState] = None,
               limit: Optional[int] = None,
               offset: int = 0) -> Dict[str, Any]:
    """
    List tasks in the queue.

    Args:
        state: Filter by task state (optional)
        limit: Maximum number of tasks to return
        offset: Number of tasks to skip

    Returns:
        Dictionary with tasks and metadata
    """
    if not _task_queue:
        raise RuntimeError("Task engine not initialized")

    all_tasks = _task_queue.list_tasks(state=state)

    # Apply pagination
    total_count = len(all_tasks)
    tasks = all_tasks[offset:offset + limit] if limit else all_tasks[offset:]

    return {
        "tasks": [get_task_status(task.id) for task in tasks],
        "total_count": total_count,
        "returned_count": len(tasks),
        "offset": offset,
        "limit": limit,
    }


def get_queue_stats() -> Dict[str, Any]:
    """
    Get queue statistics.

    Returns:
        Dictionary with queue statistics
    """
    if not _task_queue or not _task_worker:
        raise RuntimeError("Task engine not initialized")

    queue_stats = _task_queue.get_stats()
    worker_stats = {
        "active_tasks": _task_worker.get_active_task_count(),
        "max_workers": _task_worker.max_workers,
        "is_running": _task_worker.is_running(),
    }

    return {
        **queue_stats,
        **worker_stats,
        "timestamp": datetime.now().isoformat(),
    }


def cleanup_expired_tasks(max_age_seconds: int = 3600) -> int:
    """
    Clean up expired tasks from the queue.

    Args:
        max_age_seconds: Maximum age of tasks to keep

    Returns:
        Number of tasks removed
    """
    if not _task_queue:
        raise RuntimeError("Task engine not initialized")

    removed_count = _task_queue.cleanup_expired(max_age_seconds)
    if removed_count > 0:
        logger.info(f"Cleaned up {removed_count} expired tasks")
    return removed_count


def submit_remote_task(operation: str,
                       parameters: Dict[str, Any],
                       node_id: Optional[str] = None,
                       priority: TaskPriority = TaskPriority.NORMAL,
                       timeout_seconds: Optional[int] = None,
                       callback_url: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Submit a task for remote execution on a specific node.

    Args:
        operation: Operation type
        parameters: Operation parameters
        node_id: Specific remote node ID (optional, auto-selected if not provided)
        priority: Task priority
        timeout_seconds: Task timeout
        callback_url: Webhook URL for completion notifications
        metadata: Additional task metadata

    Returns:
        Task ID

    Raises:
        RuntimeError: If remote execution is not available
    """
    if not _remote_executor:
        raise RuntimeError("Remote execution not available")

    task = Task(
        operation=operation,
        parameters=parameters,
        priority=priority,
        timeout_seconds=timeout_seconds,
        callback_url=callback_url,
        metadata=metadata or {}
    )

    remote_task_id = _remote_executor.submit_remote_task(task, node_id)
    logger.info(f"Submitted remote task {remote_task_id} for operation '{operation}'")
    return remote_task_id


def get_remote_nodes() -> List[Dict[str, Any]]:
    """
    Get information about available remote nodes.

    Returns:
        List of remote node information
    """
    if not _remote_manager:
        return []

    nodes = []
    for node_id, node in _remote_manager.nodes.items():
        nodes.append({
            'id': node_id,
            'url': node.url,
            'status': node.status.value,
            'capabilities': node.capabilities.__dict__ if node.capabilities else None,
            'last_seen': node.last_seen.isoformat() if node.last_seen else None,
            'response_time': node.response_time,
            'error_count': node.error_count,
        })

    return nodes


def get_remote_node_status(node_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed status of a specific remote node.

    Args:
        node_id: Remote node ID

    Returns:
        Node status information or None if not found
    """
    if not _remote_manager:
        return None

    node = _remote_manager.nodes.get(node_id)
    if not node:
        return None

    return {
        'id': node.id,
        'url': node.url,
        'status': node.status.value,
        'capabilities': node.capabilities.__dict__ if node.capabilities else None,
        'last_seen': node.last_seen.isoformat() if node.last_seen else None,
        'response_time': node.response_time,
        'error_count': node.error_count,
        'uptime': node.uptime,
        'total_requests': node.total_requests,
        'active_tasks': len(node.active_tasks),
    }


def refresh_remote_nodes():
    """
    Refresh the status of all remote nodes.
    """
    if _remote_manager:
        _remote_manager.refresh_all_nodes()


def is_remote_available() -> bool:
    """
    Check if remote execution is available.

    Returns:
        True if remote execution components are initialized
    """
    return _remote_executor is not None and _remote_manager is not None