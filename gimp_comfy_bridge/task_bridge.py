"""
Task Engine Integration for GIMP-ComfyUI Bridge
Phase 2.0: Integration with Async Task Engine
"""

import asyncio
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor

from gimp_comfy_bridge.shared.config import Config
from gimp_comfy_bridge.shared.history import HistoryManager

# Import the async task engine
from task_engine.manager import TaskManager
from task_engine.progress import RetryPolicy
from task_engine.task import TaskPriority

logger = logging.getLogger(__name__)


class GIMPAsyncTaskBridge:
    """
    Bridge between GIMP plugin and the async task engine.
    Provides seamless integration with progress tracking, cancellation, and web UI.
    """

    def __init__(self, config: Config):
        """
        Initialize the GIMP task bridge.

        Args:
            config: Bridge configuration
        """
        self.config = config
        self.task_manager = None
        self.history_manager = HistoryManager()
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="GIMP-Task")

        # Task completion callbacks
        self._task_callbacks: Dict[str, Callable] = {}

        # Initialize task manager
        self._init_task_manager()

    def _init_task_manager(self):
        """Initialize the async task manager."""
        try:
            self.task_manager = TaskManager(
                storage_path=self.config.task_db_path,
                max_workers=4,
                max_processes=2,
                comfyui_host=self.config.comfyui_host,
                comfyui_port=self.config.comfyui_port,
                models_dir=str(self.config.workflows_dir.parent / "models"),
                temp_dir=str(self.config.temp_dir),
                enable_web_ui=True,
                web_ui_host=self.config.host,
                web_ui_port=self.config.port + 1  # Use port + 1 for web UI
            )

            # Start the task manager
            self.task_manager.start()
            logger.info("Async task manager initialized for GIMP integration")

        except Exception as e:
            logger.error(f"Failed to initialize task manager: {e}")
            raise

    def submit_gimp_task(self, operation: str, parameters: Dict[str, Any],
                        priority: TaskPriority = TaskPriority.NORMAL,
                        timeout_seconds: Optional[int] = None,
                        progress_callback: Optional[Callable] = None,
                        completion_callback: Optional[Callable] = None) -> str:
        """
        Submit a GIMP AI task to the async engine.

        Args:
            operation: GIMP operation type (upscale, inpaint, generate, etc.)
            parameters: Operation parameters
            priority: Task priority
            timeout_seconds: Task timeout
            progress_callback: Callback for progress updates
            completion_callback: Callback when task completes

        Returns:
            Task ID
        """
        # Create task parameters for the async engine
        task_params = self._prepare_task_parameters(operation, parameters)

        # Set up retry policy based on operation type
        retry_policy = self._get_retry_policy_for_operation(operation)

        # Submit to task manager
        task_id = self.task_manager.submit_task(
            task_type=f"gimp_{operation}",
            parameters=task_params,
            priority=priority,
            timeout_seconds=timeout_seconds,
            retry_policy=retry_policy,
            metadata={
                "gimp_operation": operation,
                "source": "gimp_plugin",
                "parameters": parameters
            }
        )

        # Register callbacks
        if progress_callback:
            self.task_manager.add_progress_callback(
                GIMPProgressCallback(task_id, progress_callback)
            )

        if completion_callback:
            self._task_callbacks[task_id] = completion_callback

        # Set up completion monitoring
        self._monitor_task_completion(task_id)

        logger.info(f"Submitted GIMP task {task_id} for operation: {operation}")
        return task_id

    def _prepare_task_parameters(self, operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare task parameters for the async engine.

        Args:
            operation: GIMP operation type
            parameters: Original parameters

        Returns:
            Prepared task parameters
        """
        # Base parameters
        task_params = {
            "operation": operation,
            "gimp_parameters": parameters,
            "output_dir": str(self.config.temp_dir),
            "comfyui_host": self.config.comfyui_host,
            "comfyui_port": self.config.comfyui_port
        }

        # Operation-specific parameters
        if operation == "upscale":
            task_params.update({
                "scale_factor": parameters.get("scale_factor", 2.0),
                "method": parameters.get("method", "4x-UltraSharp"),
                "input_image": parameters.get("input_image")
            })

        elif operation == "inpaint":
            task_params.update({
                "prompt": parameters.get("prompt", ""),
                "negative_prompt": parameters.get("negative_prompt", ""),
                "input_image": parameters.get("input_image"),
                "mask_image": parameters.get("mask_image")
            })

        elif operation == "generate":
            task_params.update({
                "prompt": parameters.get("prompt", ""),
                "negative_prompt": parameters.get("negative_prompt", ""),
                "width": parameters.get("width", 1024),
                "height": parameters.get("height", 1024)
            })

        elif operation == "img2img":
            task_params.update({
                "prompt": parameters.get("prompt", ""),
                "negative_prompt": parameters.get("negative_prompt", ""),
                "input_image": parameters.get("input_image"),
                "strength": parameters.get("strength", 0.8)
            })

        elif operation == "controlnet":
            task_params.update({
                "prompt": parameters.get("prompt", ""),
                "negative_prompt": parameters.get("negative_prompt", ""),
                "input_image": parameters.get("input_image"),
                "control_image": parameters.get("control_image"),
                "controlnet_model": parameters.get("controlnet_model", "control_v11p_sd15_canny")
            })

        return task_params

    def _get_retry_policy_for_operation(self, operation: str) -> RetryPolicy:
        """
        Get appropriate retry policy for operation type.

        Args:
            operation: Operation type

        Returns:
            Retry policy
        """
        # Different operations have different retry characteristics
        if operation in ["generate", "img2img"]:
            # Creative operations - more retries, longer delays
            return RetryPolicy(
                max_attempts=3,
                base_delay=5.0,
                max_delay=60.0,
                backoff_factor=2.0
            )
        elif operation in ["upscale", "inpaint"]:
            # Processing operations - fewer retries, shorter delays
            return RetryPolicy(
                max_attempts=2,
                base_delay=2.0,
                max_delay=30.0,
                backoff_factor=1.5
            )
        else:
            # Default policy
            return RetryPolicy(
                max_attempts=2,
                base_delay=3.0,
                max_delay=45.0,
                backoff_factor=1.8
            )

    def cancel_gimp_task(self, task_id: str) -> bool:
        """
        Cancel a GIMP task.

        Args:
            task_id: Task ID to cancel

        Returns:
            True if cancelled
        """
        logger.info(f"Cancelling GIMP task {task_id}")
        return self.task_manager.cancel_task(task_id)

    def get_task_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get progress information for a task.

        Args:
            task_id: Task ID

        Returns:
            Progress information
        """
        return self.task_manager.get_task_progress(task_id)

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status information for a task.

        Args:
            task_id: Task ID

        Returns:
            Task status information
        """
        task = self.task_manager.get_task(task_id)
        if task:
            return {
                "task_id": task.id,
                "state": task.state.value,
                "progress": self.get_task_progress(task_id),
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "error": str(task.error) if task.error else None
            }
        return None

    def _monitor_task_completion(self, task_id: str):
        """
        Monitor task completion and trigger callbacks.

        Args:
            task_id: Task ID to monitor
        """
        def monitor():
            while True:
                task = self.task_manager.get_task(task_id)
                if task and task.is_completed():
                    # Task completed, trigger callback
                    callback = self._task_callbacks.pop(task_id, None)
                    if callback:
                        try:
                            # Run callback in thread pool to avoid blocking
                            self._executor.submit(callback, task)
                        except Exception as e:
                            logger.error(f"Error in task completion callback: {e}")
                    break
                asyncio.sleep(0.5)  # Check every 500ms

        # Start monitoring in background thread
        threading.Thread(target=lambda: asyncio.run(monitor()), daemon=True).start()

    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get system statistics.

        Returns:
            System statistics
        """
        return self.task_manager.get_stats()

    def cleanup(self):
        """Clean up resources."""
        if self.task_manager:
            self.task_manager.stop()
        self._executor.shutdown(wait=True)
        logger.info("GIMP task bridge cleaned up")


class GIMPProgressCallback:
    """
    Progress callback adapter for GIMP operations.
    """

    def __init__(self, task_id: str, callback: Callable):
        """
        Initialize progress callback.

        Args:
            task_id: Task ID to monitor
            callback: GIMP progress callback
        """
        self.task_id = task_id
        self.callback = callback

    def on_progress_update(self, update):
        """
        Handle progress update.

        Args:
            update: Progress update
        """
        if update.task_id == self.task_id:
            try:
                self.callback({
                    "percentage": update.percentage,
                    "stage": update.stage,
                    "message": update.message,
                    "eta_seconds": update.eta_seconds,
                    "current_step": update.current_step,
                    "total_steps": update.total_steps
                })
            except Exception as e:
                logger.error(f"Error in GIMP progress callback: {e}")

    def on_task_started(self, task):
        """Handle task started."""
        if task.id == self.task_id:
            try:
                self.callback({
                    "percentage": 0,
                    "stage": "started",
                    "message": "Task started",
                    "eta_seconds": None,
                    "current_step": 0,
                    "total_steps": 0
                })
            except Exception as e:
                logger.error(f"Error in GIMP task started callback: {e}")

    def on_task_completed(self, task):
        """Handle task completed."""
        if task.id == self.task_id:
            try:
                self.callback({
                    "percentage": 100,
                    "stage": "completed",
                    "message": "Task completed" if task.state.value == "completed" else f"Task {task.state.value}",
                    "eta_seconds": 0,
                    "current_step": 1,
                    "total_steps": 1
                })
            except Exception as e:
                logger.error(f"Error in GIMP task completed callback: {e}")


# Global bridge instance
_gimp_bridge = None

def get_gimp_bridge(config: Optional[Config] = None) -> GIMPAsyncTaskBridge:
    """
    Get the global GIMP task bridge instance.

    Args:
        config: Bridge configuration

    Returns:
        GIMP task bridge instance
    """
    global _gimp_bridge
    if _gimp_bridge is None:
        if config is None:
            config = Config()
        _gimp_bridge = GIMPAsyncTaskBridge(config)
    return _gimp_bridge