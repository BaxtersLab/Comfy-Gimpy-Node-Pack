"""
Task executor for running tasks asynchronously.
"""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Dict, Any, Callable, Optional, Awaitable, List
from contextlib import asynccontextmanager

from .task import Task, TaskState, TaskResult
from .queue import TaskQueue
from .storage import TaskStorage
from .executors import (
    TaskExecutorInterface,
    ResourceMonitor,
    ComfyUIWorkflowExecutor,
    ModelDownloadExecutor,
    ImageProcessingExecutor
)

# GIMP-specific executors
from .executors.gimp_executors import (
    GIMPUpscaleExecutor,
    GIMPInpaintExecutor,
    GIMPGenerateExecutor,
    GIMPImg2ImgExecutor,
    GIMPControlNetExecutor
)

# Progress and control systems
from .progress import ProgressTracker, TaskController, RetryPolicy
from .progress.retry import RetryManager


class TaskExecutor:
    """
    Asynchronous task executor with thread/process pool support.

    Handles task execution, cancellation, and resource management.
    """

    def __init__(self, queue: TaskQueue, storage: TaskStorage,
                 max_workers: int = 4, max_processes: int = 2,
                 comfyui_host: str = "localhost", comfyui_port: int = 8188,
                 models_dir: Optional[str] = None, temp_dir: Optional[str] = None,
                 progress_tracker: Optional[ProgressTracker] = None,
                 task_controller: Optional[TaskController] = None,
                 gimp_config: Optional[Any] = None):
        """
        Initialize task executor.

        Args:
            queue: Task queue
            storage: Task storage
            max_workers: Maximum thread pool workers
            max_processes: Maximum process pool workers
            comfyui_host: ComfyUI server host
            comfyui_port: ComfyUI server port
            models_dir: Directory for model storage
            temp_dir: Temporary directory for processing
            progress_tracker: Progress tracker instance
            task_controller: Task controller instance
            gimp_config: GIMP bridge configuration
        """
        self.queue = queue
        self.storage = storage
        self.max_workers = max_workers
        self.max_processes = max_processes
        self.progress_tracker = progress_tracker
        self.task_controller = task_controller
        self.gimp_config = gimp_config

        # Thread pools
        self.thread_executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="TaskExecutor")
        self.process_executor = ProcessPoolExecutor(max_processes=max_processes)

        # Resource monitoring
        self.resource_monitor = ResourceMonitor()

        # Specialized executors
        from pathlib import Path
        models_path = Path(models_dir) if models_dir else Path("./models")
        temp_path = Path(temp_dir) if temp_dir else Path("./temp")

        self.specialized_executors: List[TaskExecutorInterface] = [
            ComfyUIWorkflowExecutor(comfyui_host, comfyui_port),
            ModelDownloadExecutor(models_path),
            ImageProcessingExecutor(temp_path)
        ]

        # Add GIMP executors if config provided
        if gimp_config:
            from .executors.gimp_executors import (
                GIMPUpscaleExecutor,
                GIMPInpaintExecutor,
                GIMPGenerateExecutor,
                GIMPImg2ImgExecutor,
                GIMPControlNetExecutor
            )
            self.specialized_executors.extend([
                GIMPUpscaleExecutor(gimp_config),
                GIMPInpaintExecutor(gimp_config),
                GIMPGenerateExecutor(gimp_config),
                GIMPImg2ImgExecutor(gimp_config),
                GIMPControlNetExecutor(gimp_config)
            ])

        # Execution tracking
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._cancel_tokens: Dict[str, threading.Event] = {}

        # Event loop management
        self._loop = None
        self._loop_thread = None
        self._shutdown_event = threading.Event()

    def start(self):
        """Start the task executor."""
        if self._loop_thread and self._loop_thread.is_alive():
            return  # Already running

        self._shutdown_event.clear()
        self._loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._loop_thread.start()

        # Wait for loop to be ready
        while not self._loop or not self._loop.is_running():
            time.sleep(0.01)

    def stop(self):
        """Stop the task executor."""
        if not self._loop_thread:
            return

        self._shutdown_event.set()

        # Cancel all running tasks
        for task_id in list(self._running_tasks.keys()):
            self.cancel_task(task_id)

        # Shutdown executors
        self.thread_executor.shutdown(wait=True)
        self.process_executor.shutdown(wait=True)

        # Stop event loop
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

        self._loop_thread.join(timeout=5.0)

    def submit_task(self, task: Task):
        """
        Submit a task for execution using appropriate specialized executor.

        Args:
            task: Task to execute
        """
        if not self._loop or not self._loop.is_running():
            raise RuntimeError("Task executor is not running")

        # Find appropriate executor
        executor = self._get_executor_for_task(task)
        if not executor:
            raise ValueError(f"No suitable executor found for task type: {task.type}")

        # Check resource requirements
        requirements = executor.get_resource_requirements()
        if not self.resource_monitor.has_sufficient_resources(requirements):
            raise RuntimeError(f"Insufficient system resources for task {task.id}")

        # Create cancel token
        cancel_token = threading.Event()
        self._cancel_tokens[task.id] = cancel_token

        # Submit task to event loop
        asyncio_task = self._loop.create_task(
            self._execute_task_with_executor(task, executor, cancel_token)
        )
        self._running_tasks[task.id] = asyncio_task

    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.

        Args:
            task_id: Task ID to cancel

        Returns:
            True if task was cancelled, False if not found or already completed
        """
        if task_id not in self._running_tasks:
            return False

        # Set cancel token
        if task_id in self._cancel_tokens:
            self._cancel_tokens[task_id].set()

        # Cancel asyncio task
        asyncio_task = self._running_tasks[task_id]
        asyncio_task.cancel()

        return True

    def is_task_running(self, task_id: str) -> bool:
        """
        Check if a task is currently running.

        Args:
            task_id: Task ID

        Returns:
            True if task is running
        """
        return task_id in self._running_tasks

    def get_running_task_count(self) -> int:
        """
        Get the number of currently running tasks.

        Returns:
            Number of running tasks
        """
        return len(self._running_tasks)

    def _get_executor_for_task(self, task: Task) -> Optional[TaskExecutorInterface]:
        """
        Get the appropriate executor for a task.

        Args:
            task: Task to find executor for

        Returns:
            Appropriate executor, or None if not found
        """
        for executor in self.specialized_executors:
            if executor.can_execute(task):
                return executor
        return None

    async def _execute_task_with_executor(self, task: Task,
                                        executor: TaskExecutorInterface,
                                        cancel_token: threading.Event):
        """
        Execute a task with a specialized executor.

        Args:
            task: Task to execute
            executor: Specialized executor to use
            cancel_token: Cancellation token
        """
        cancel_token_controller = None

        try:
            # Mark task as started
            task.mark_started()
            self.queue.update_task_state(task.id, TaskState.RUNNING)
            self.storage.save_task(task)

            # Set up progress tracking and control
            if self.task_controller:
                cancel_token_controller = self.task_controller.start_task(task)
                # Combine cancellation tokens
                def combined_cancel_check():
                    if cancel_token.is_set() or (cancel_token_controller and cancel_token_controller.is_cancelled()):
                        raise asyncio.CancelledError("Task was cancelled")

                cancel_token = combined_cancel_check  # Override with combined check

            # Execute with timeout if specified
            if task.timeout_seconds:
                result = await asyncio.wait_for(
                    self._execute_with_cancellation(task, executor, cancel_token),
                    timeout=task.timeout_seconds
                )
            else:
                result = await self._execute_with_cancellation(task, executor, cancel_token)

            # Mark as completed
            task.mark_completed(result)
            self.queue.update_task_state(task.id, TaskState.COMPLETED)

        except asyncio.TimeoutError:
            # Task timed out
            task.mark_timeout()
            self.queue.update_task_state(task.id, TaskState.TIMEOUT)
            result = TaskResult(
                success=False,
                error_message="Task execution timed out",
                execution_time_seconds=task.timeout_seconds or 0
            )
            task.result = result

        except asyncio.CancelledError:
            # Task was cancelled
            task.mark_cancelled()
            self.queue.update_task_state(task.id, TaskState.CANCELLED)
            result = TaskResult(
                success=False,
                error_message="Task was cancelled",
                execution_time_seconds=task.get_execution_time() or 0
            )
            task.result = result

        except Exception as e:
            # Task failed
            error_message = f"Task execution failed: {str(e)}"
            task.mark_failed(error_message, {"exception": str(e), "type": type(e).__name__})
            self.queue.update_task_state(task.id, TaskState.FAILED)

        finally:
            # Clean up
            self._running_tasks.pop(task.id, None)
            self._cancel_tokens.pop(task.id, None)

            # Complete task in controller
            if self.task_controller and cancel_token_controller:
                self.task_controller.complete_task(task)

            # Save final state
            self.storage.save_task(task)

    async def _execute_with_cancellation(self, task: Task,
                                        executor: TaskExecutorInterface,
                                        cancel_token) -> TaskResult:
        """
        Execute task with cancellation support.

        Args:
            task: Task to execute
            executor: Specialized executor
            cancel_token: Cancellation token (Event or callable)

        Returns:
            Task result
        """
        # Create a future for cancellation checking
        def check_cancelled():
            if callable(cancel_token):
                cancel_token()  # Call the combined check function
            elif hasattr(cancel_token, 'is_set') and cancel_token.is_set():
                raise asyncio.CancelledError("Task was cancelled by user")

        # Execute task
        result = await executor.execute(task)

        # Final cancellation check
        check_cancelled()

        return result

    def _run_event_loop(self):
        """Run the asyncio event loop in a separate thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            self._loop.run_forever()
        except Exception as e:
            print(f"Event loop error: {e}")
        finally:
            try:
                self._loop.close()
            except Exception:
                pass

    @asynccontextmanager
    async def run_in_thread_pool(self, func: Callable, *args, **kwargs):
        """
        Run a function in the thread pool.

        Args:
            func: Function to run
            *args: Function arguments
            **kwargs: Function keyword arguments

        Yields:
            Function result
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(self.thread_executor, func, *args, **kwargs)
        yield result

    @asynccontextmanager
    async def run_in_process_pool(self, func: Callable, *args, **kwargs):
        """
        Run a function in the process pool.

        Args:
            func: Function to run
            *args: Function arguments
            **kwargs: Function keyword arguments

        Yields:
            Function result
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(self.process_executor, func, *args, **kwargs)
        yield result