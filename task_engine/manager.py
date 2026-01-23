"""
Task manager - main interface for the async task engine.
"""

import asyncio
import logging
import threading
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Awaitable

from .task import Task, TaskState, TaskPriority, TaskResult
from .queue import TaskQueue
from .storage import TaskStorage
from .executor import TaskExecutor

# Progress and control systems
from .progress import ProgressTracker, TaskController, RetryPolicy
from .progress.retry import RetryManager
from .progress.web_ui import ProgressWebAPI

logger = logging.getLogger(__name__)


class TaskManager:
    """
    Main task management interface.

    Coordinates queue, storage, and execution of tasks.
    """

    def __init__(self, storage_path: Path, max_workers: int = 4, max_processes: int = 2,
                 comfyui_host: str = "localhost", comfyui_port: int = 8188,
                 models_dir: Optional[str] = None, temp_dir: Optional[str] = None,
                 enable_web_ui: bool = True, web_ui_host: str = "localhost", web_ui_port: int = 8080,
                 gimp_config: Optional[Any] = None):
        """
        Initialize task manager.

        Args:
            storage_path: Path for task storage database
            max_workers: Maximum thread pool workers
            max_processes: Maximum process pool workers
            comfyui_host: ComfyUI server host
            comfyui_port: ComfyUI server port
            models_dir: Directory for model storage
            temp_dir: Temporary directory for processing
            enable_web_ui: Whether to enable web UI for progress tracking
            web_ui_host: Host for web UI
            web_ui_port: Port for web UI
            gimp_config: GIMP bridge configuration for GIMP operations
        """
        self.storage_path = storage_path
        self.max_workers = max_workers
        self.max_processes = max_processes
        self.comfyui_host = comfyui_host
        self.comfyui_port = comfyui_port
        self.models_dir = models_dir
        self.temp_dir = temp_dir
        self.enable_web_ui = enable_web_ui
        self.web_ui_host = web_ui_host
        self.web_ui_port = web_ui_port
        self.gimp_config = gimp_config

        # Core components
        self.storage = TaskStorage(storage_path)
        self.queue = TaskQueue()
        self.executor = TaskExecutor(
            self.queue, self.storage, max_workers, max_processes,
            comfyui_host, comfyui_port, models_dir, temp_dir,
            self.progress_tracker, self.task_controller, gimp_config
        )

        # Progress and control systems
        self.progress_tracker = ProgressTracker()
        self.task_controller = TaskController(self.progress_tracker)
        self.retry_manager = RetryManager(self.task_controller, self.progress_tracker)

        # Web UI
        self.web_api = None
        if enable_web_ui:
            self.web_api = ProgressWebAPI(
                self.progress_tracker, self.task_controller,
                web_ui_host, web_ui_port
            )

        # Management
        self._running = False
        self._management_thread = None
        self._shutdown_event = threading.Event()

        # Load existing tasks on startup
        self._load_existing_tasks()

    def start(self):
        """Start the task manager."""
        if self._running:
            return

        logger.info("Starting task manager")
        self._running = True
        self._shutdown_event.clear()

        # Start executor
        self.executor.start()

        # Start web UI if enabled
        if self.web_api:
            asyncio.create_task(self.web_api.start())

        # Start management thread
        self._management_thread = threading.Thread(target=self._management_loop, daemon=True)
        self._management_thread.start()

        logger.info("Task manager started")

    async def stop_async(self):
        """Stop the task manager asynchronously."""
        if not self._running:
            return

        logger.info("Stopping task manager")
        self._running = False
        self._shutdown_event.set()

        # Stop web UI
        if self.web_api:
            await self.web_api.stop()

        # Stop executor
        self.executor.stop()

        # Wait for management thread
        if self._management_thread:
            self._management_thread.join(timeout=5.0)

        logger.info("Task manager stopped")

    def stop(self):
        """Stop the task manager (synchronous wrapper)."""
        # Create event loop if needed
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, we need to run the async stop in a thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.stop_async())
                    future.result(timeout=10.0)
            else:
                loop.run_until_complete(self.stop_async())
        except RuntimeError:
            # No event loop, create one
            asyncio.run(self.stop_async())

    def submit_task(self, task_type: str, parameters: Dict[str, Any],
                   priority: TaskPriority = TaskPriority.NORMAL,
                   timeout_seconds: Optional[int] = None,
                   dependencies: List[str] = None,
                   metadata: Dict[str, Any] = None,
                   retry_policy: Optional[RetryPolicy] = None) -> str:
        """
        Submit a new task for execution.

        Args:
            task_type: Type of task to execute
            parameters: Task parameters
            priority: Task priority
            timeout_seconds: Task timeout in seconds
            dependencies: List of task IDs this task depends on
            metadata: Additional task metadata
            retry_policy: Retry policy for the task

        Returns:
            Task ID

        Raises:
            ValueError: If task type is not supported
        """
        # Check if we have an executor for this task type
        from .executors import ComfyUIWorkflowExecutor, ModelDownloadExecutor, ImageProcessingExecutor

        supported_types = []
        for executor_class in [ComfyUIWorkflowExecutor, ModelDownloadExecutor, ImageProcessingExecutor]:
            # Create a dummy executor to check capabilities
            dummy_executor = executor_class()
            # We can't easily check without parameters, so we'll validate at execution time
            supported_types.extend(['comfyui_workflow', 'image_generation', 'style_application',
                                  'model_download', 'model_install',
                                  'image_process', 'image_resize', 'image_convert'])

        if task_type not in supported_types:
            raise ValueError(f"Task type '{task_type}' is not supported")

        # Create task
        task = Task(
            type=task_type,
            priority=priority,
            parameters=parameters,
            timeout_seconds=timeout_seconds,
            dependencies=dependencies or [],
            metadata=metadata or {}
        )

        # Store retry policy in task metadata
        if retry_policy:
            task.metadata['retry_policy'] = retry_policy

        # Add to queue
        if self.queue.add_task(task):
            # Save to storage
            self.storage.save_task(task)
            logger.info(f"Submitted task {task.id} of type {task_type}")
            return task.id
        else:
            raise ValueError("Failed to add task to queue (dependencies not satisfied)")

    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task.

        Args:
            task_id: Task ID to cancel

        Returns:
            True if task was cancelled
        """
        logger.info(f"Cancelling task {task_id}")

        # Try task controller first (for running tasks)
        if self.task_controller.cancel_task(task_id):
            return True

        # Try to cancel in executor
        if self.executor.cancel_task(task_id):
            return True

        # If not running, update state directly
        task = self.queue.get_task(task_id)
        if task and not task.is_completed():
            task.mark_cancelled()
            self.queue.update_task_state(task_id, TaskState.CANCELLED)
            self.storage.save_task(task)
            return True

        return False

    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task if found
        """
        return self.queue.get_task(task_id) or self.storage.load_task(task_id)

    def get_all_tasks(self, include_completed: bool = True) -> List[Task]:
        """
        Get all tasks.

        Args:
            include_completed: Whether to include completed tasks

        Returns:
            List of tasks
        """
        tasks = self.queue.get_all_tasks()

        if include_completed:
            # Load additional completed tasks from storage
            stored_tasks = self.storage.load_all_tasks()
            stored_ids = {t.id for t in tasks}

            for task in stored_tasks:
                if task.id not in stored_ids:
                    tasks.append(task)

        return tasks

    def get_tasks_by_state(self, state: TaskState) -> List[Task]:
        """
        Get tasks by state.

        Args:
            state: Task state

        Returns:
            List of tasks in the specified state
        """
        # Check queue first
        queue_tasks = [t for t in self.queue.get_all_tasks() if t.state == state]

        # Also check storage for completed tasks
        if state in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED, TaskState.TIMEOUT]:
            stored_tasks = self.storage.load_tasks_by_state(state.value)
            # Avoid duplicates
            queue_ids = {t.id for t in queue_tasks}
            stored_tasks = [t for t in stored_tasks if t.id not in queue_ids]
            queue_tasks.extend(stored_tasks)

        return queue_tasks

    def get_tasks_by_type(self, task_type: str) -> List[Task]:
        """
        Get tasks by type.

        Args:
            task_type: Task type

        Returns:
            List of tasks of the specified type
        """
        return self.storage.load_tasks_by_type(task_type)

    def get_task_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get progress information for a task.

        Args:
            task_id: Task ID

        Returns:
            Progress information, or None if not found
        """
        progress = self.progress_tracker.get_progress(task_id)
        if progress:
            return {
                "task_id": task_id,
                "percentage": progress.percentage,
                "stage": progress.stage,
                "message": progress.message,
                "eta_seconds": progress.eta_seconds,
                "current_step": progress.current_step,
                "total_steps": progress.total_steps
            }
        return None

    def retry_task_with_policy(self, task_id: str, retry_policy: Optional[RetryPolicy] = None) -> bool:
        """
        Retry a failed task with a specific retry policy.

        Args:
            task_id: Task ID to retry
            retry_policy: Retry policy to use

        Returns:
            True if task was queued for retry
        """
        task = self.get_task(task_id)
        if not task or not task.can_retry():
            return False

        # Use provided policy or get from task metadata
        policy = retry_policy or task.metadata.get('retry_policy', RetryPolicy())

        # Reset task state
        task.state = TaskState.QUEUED
        task.started_at = None
        task.completed_at = None
        task.result = None
        task.increment_retry()

        # Store retry policy
        task.metadata['retry_policy'] = policy

        # Re-queue
        if self.queue.add_task(task):
            self.storage.save_task(task)
            logger.info(f"Retrying task {task_id} (attempt {task.retry_count})")
            return True

        return False

    def get_retry_history(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Get retry history for a task.

        Args:
            task_id: Task ID

        Returns:
            List of retry attempts
        """
        from .progress.retry import RetryAttempt
        attempts = self.retry_manager.get_retry_history(task_id)
        return [{
            "attempt_number": a.attempt_number,
            "timestamp": a.timestamp.isoformat(),
            "exception": str(a.exception),
            "delay_used": a.delay_used
        } for a in attempts]

    def add_progress_callback(self, callback):
        """
        Add a progress callback.

        Args:
            callback: Progress callback to add
        """
        self.progress_tracker.add_callback(callback)

    def remove_progress_callback(self, callback):
        """
        Remove a progress callback.

        Args:
            callback: Progress callback to remove
        """
        self.progress_tracker.remove_callback(callback)

    def cleanup_completed_tasks(self, older_than_days: int = 30) -> int:
        """
        Clean up old completed tasks.

        Args:
            older_than_days: Remove tasks older than this many days

        Returns:
            Number of tasks removed
        """
        removed_from_storage = self.storage.delete_completed_tasks(older_than_days)
        removed_from_queue = self.queue.clear_completed_tasks()

        logger.info(f"Cleaned up {removed_from_storage + removed_from_queue} completed tasks")
        return removed_from_storage + removed_from_queue

    def get_stats(self) -> Dict[str, Any]:
        """
        Get task manager statistics.

        Returns:
            Dictionary with statistics
        """
        storage_stats = self.storage.get_task_stats()

        return {
            'queue_size': self.queue.get_queue_size(),
            'pending_count': self.queue.get_pending_count(),
            'running_count': self.executor.get_running_task_count(),
            'storage_stats': storage_stats,
            'supported_task_types': [
                'comfyui_workflow', 'image_generation', 'style_application',
                'model_download', 'model_install',
                'image_process', 'image_resize', 'image_convert'
            ],
            'is_running': self._running,
            'resource_usage': self.executor.resource_monitor.get_available_resources()
        }

    def _load_existing_tasks(self):
        """Load existing tasks from storage on startup."""
        try:
            tasks = self.storage.load_all_tasks()
            logger.info(f"Loaded {len(tasks)} existing tasks from storage")

            for task in tasks:
                # Only add incomplete tasks back to queue
                if not task.is_completed():
                    self.queue.add_task(task)
                    logger.debug(f"Restored task {task.id} to queue")

        except Exception as e:
            logger.error(f"Failed to load existing tasks: {e}")

    def _management_loop(self):
        """Main management loop - processes queued tasks."""
        logger.info("Task management loop started")

        while not self._shutdown_event.is_set():
            try:
                # Get next task to execute
                task = self.queue.get_next_task()

                if task:
                    # Check if executor can handle this task
                    executor = self.executor._get_executor_for_task(task)
                    if executor:
                        logger.info(f"Executing task {task.id} of type {task.type}")
                        try:
                            self.executor.submit_task(task)
                        except RuntimeError as e:
                            if "Insufficient system resources" in str(e):
                                logger.warning(f"Insufficient resources for task {task.id}, re-queuing")
                                # Re-queue the task for later
                                task.state = TaskState.QUEUED
                                self.queue.add_task(task)
                                self.storage.save_task(task)
                            else:
                                raise
                    else:
                        logger.error(f"No executor available for task type: {task.type}")
                        task.mark_failed(f"No executor for task type: {task.type}")
                        self.queue.update_task_state(task.id, TaskState.FAILED)
                        self.storage.save_task(task)

                # Small delay to prevent busy waiting
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Error in management loop: {e}")
                time.sleep(1.0)

        logger.info("Task management loop stopped")