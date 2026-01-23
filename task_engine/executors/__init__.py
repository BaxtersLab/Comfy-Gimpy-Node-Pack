"""
Base executor interface and specialized executors for different task types.
"""

import asyncio
import logging
import psutil
import threading
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path

from ..task import Task, TaskResult

logger = logging.getLogger(__name__)


class TaskExecutorInterface(ABC):
    """
    Abstract base class for task executors.
    """

    @abstractmethod
    async def execute(self, task: Task) -> TaskResult:
        """
        Execute a task.

        Args:
            task: Task to execute

        Returns:
            Task result
        """
        pass

    @abstractmethod
    def get_resource_requirements(self) -> Dict[str, Any]:
        """
        Get resource requirements for this executor.

        Returns:
            Dictionary with resource requirements
        """
        pass

    @abstractmethod
    def can_execute(self, task: Task) -> bool:
        """
        Check if this executor can handle the given task.

        Args:
            task: Task to check

        Returns:
            True if this executor can handle the task
        """
        pass


class ResourceMonitor:
    """
    System resource monitoring for task execution.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._cpu_percent = 0.0
        self._memory_percent = 0.0
        self._last_update = 0.0
        self._update_interval = 1.0  # Update every second

    def update_stats(self):
        """Update system resource statistics."""
        current_time = asyncio.get_event_loop().time()
        if current_time - self._last_update >= self._update_interval:
            with self._lock:
                self._cpu_percent = psutil.cpu_percent(interval=None)
                self._memory_percent = psutil.virtual_memory().percent
                self._last_update = current_time

    def get_cpu_percent(self) -> float:
        """Get current CPU usage percentage."""
        self.update_stats()
        with self._lock:
            return self._cpu_percent

    def get_memory_percent(self) -> float:
        """Get current memory usage percentage."""
        self.update_stats()
        with self._lock:
            return self._memory_percent

    def get_available_resources(self) -> Dict[str, float]:
        """
        Get available system resources.

        Returns:
            Dictionary with available CPU and memory percentages
        """
        return {
            'cpu_available': 100.0 - self.get_cpu_percent(),
            'memory_available': 100.0 - self.get_memory_percent()
        }

    def has_sufficient_resources(self, requirements: Dict[str, Any]) -> bool:
        """
        Check if system has sufficient resources for requirements.

        Args:
            requirements: Resource requirements dictionary

        Returns:
            True if sufficient resources available
        """
        available = self.get_available_resources()

        cpu_required = requirements.get('cpu_percent', 0)
        memory_required = requirements.get('memory_percent', 0)

        return (available['cpu_available'] >= cpu_required and
                available['memory_available'] >= memory_required)


class ComfyUIWorkflowExecutor(TaskExecutorInterface):
    """
    Executor for ComfyUI workflow tasks.
    """

    def __init__(self, comfyui_host: str = "localhost", comfyui_port: int = 8188):
        self.comfyui_host = comfyui_host
        self.comfyui_port = comfyui_port
        self.base_url = f"http://{comfyui_host}:{comfyui_port}"

    def get_resource_requirements(self) -> Dict[str, Any]:
        """Get resource requirements for ComfyUI workflow execution."""
        return {
            'cpu_percent': 20.0,  # Estimated CPU usage
            'memory_percent': 15.0,  # Estimated memory usage
            'gpu_required': True,  # Most ComfyUI workflows need GPU
            'isolation_level': 'process'  # Run in separate process for stability
        }

    def can_execute(self, task: Task) -> bool:
        """Check if this executor can handle ComfyUI workflow tasks."""
        return task.type in ['comfyui_workflow', 'image_generation', 'style_application']

    async def execute(self, task: Task) -> TaskResult:
        """
        Execute a ComfyUI workflow task.

        Args:
            task: Task containing workflow parameters

        Returns:
            Task result with generated outputs
        """
        try:
            # Update progress
            task.update_progress(10.0, "Preparing workflow")

            # Extract workflow parameters
            workflow_data = task.parameters.get('workflow', {})
            prompt_data = task.parameters.get('prompt', {})

            if not workflow_data:
                raise ValueError("No workflow data provided")

            # Update progress
            task.update_progress(20.0, "Connecting to ComfyUI")

            # Import aiohttp for HTTP requests
            try:
                from aiohttp import ClientSession, ClientTimeout
            except ImportError:
                raise RuntimeError("aiohttp not available for ComfyUI communication")

            timeout = ClientTimeout(total=300)  # 5 minute timeout

            async with ClientSession(timeout=timeout) as session:
                # Queue the prompt
                task.update_progress(30.0, "Queueing workflow")

                queue_url = f"{self.base_url}/prompt"
                async with session.post(queue_url, json={"prompt": workflow_data}) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise RuntimeError(f"Failed to queue workflow: {error_text}")

                    queue_result = await response.json()
                    prompt_id = queue_result.get('prompt_id')

                # Poll for completion
                task.update_progress(40.0, "Executing workflow")

                max_polls = 300  # 5 minutes max
                poll_count = 0

                while poll_count < max_polls:
                    # Check execution status
                    history_url = f"{self.base_url}/history/{prompt_id}"
                    async with session.get(history_url) as response:
                        if response.status == 200:
                            history = await response.json()
                            if prompt_id in history:
                                execution_data = history[prompt_id]
                                status = execution_data.get('status', {})

                                if status.get('completed'):
                                    # Workflow completed successfully
                                    task.update_progress(90.0, "Processing results")

                                    # Extract outputs
                                    outputs = execution_data.get('outputs', {})
                                    output_files = []

                                    # Save outputs to temporary files
                                    for node_id, node_outputs in outputs.items():
                                        for output_key, output_data in node_outputs.items():
                                            if isinstance(output_data, list):
                                                for item in output_data:
                                                    if isinstance(item, dict) and 'filename' in item:
                                                        # This is likely an image output
                                                        output_files.append(Path(item['filename']))

                                    task.update_progress(100.0, "Workflow completed")

                                    return TaskResult(
                                        success=True,
                                        data={
                                            'prompt_id': prompt_id,
                                            'outputs': outputs,
                                            'execution_data': execution_data
                                        },
                                        output_files=output_files
                                    )
                                elif status.get('exception'):
                                    # Workflow failed
                                    raise RuntimeError(f"Workflow execution failed: {status['exception']}")

                    # Update progress based on poll count
                    progress = 40.0 + (poll_count / max_polls) * 50.0
                    task.update_progress(progress, f"Executing workflow ({poll_count}s)")

                    await asyncio.sleep(1)
                    poll_count += 1

                # Timeout
                raise TimeoutError("Workflow execution timed out")

        except Exception as e:
            logger.error(f"ComfyUI workflow execution failed: {e}")
            return TaskResult(
                success=False,
                error_message=str(e),
                error_details={'exception': str(e), 'task_type': task.type}
            )


class ModelDownloadExecutor(TaskExecutorInterface):
    """
    Executor for model download and management tasks.
    """

    def __init__(self, models_dir: Path):
        self.models_dir = models_dir
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def get_resource_requirements(self) -> Dict[str, Any]:
        """Get resource requirements for model download."""
        return {
            'cpu_percent': 5.0,  # Light CPU usage
            'memory_percent': 5.0,  # Light memory usage
            'network_required': True,  # Requires internet access
            'disk_space_mb': 1000,  # Estimated space for models
            'isolation_level': 'thread'  # Can run in thread
        }

    def can_execute(self, task: Task) -> bool:
        """Check if this executor can handle model download tasks."""
        return task.type in ['model_download', 'model_install']

    async def execute(self, task: Task) -> TaskResult:
        """
        Execute a model download task.

        Args:
            task: Task containing download parameters

        Returns:
            Task result with download status
        """
        try:
            # Extract download parameters
            model_url = task.parameters.get('url')
            model_name = task.parameters.get('name')
            model_type = task.parameters.get('type', 'checkpoint')

            if not model_url:
                raise ValueError("Model URL not provided")

            if not model_name:
                raise ValueError("Model name not provided")

            task.update_progress(10.0, "Preparing download")

            # Create model subdirectory
            model_dir = self.models_dir / model_type
            model_dir.mkdir(exist_ok=True)

            model_path = model_dir / f"{model_name}.safetensors"

            # Check if model already exists
            if model_path.exists():
                task.update_progress(100.0, "Model already exists")
                return TaskResult(
                    success=True,
                    data={'status': 'already_exists', 'path': str(model_path)},
                    output_files=[model_path]
                )

            task.update_progress(20.0, "Downloading model")

            # Import aiohttp for download
            try:
                from aiohttp import ClientSession, ClientTimeout
            except ImportError:
                raise RuntimeError("aiohttp not available for model download")

            timeout = ClientTimeout(total=3600)  # 1 hour timeout for large downloads

            downloaded_bytes = 0
            total_bytes = 0

            async with ClientSession(timeout=timeout) as session:
                async with session.get(model_url) as response:
                    if response.status != 200:
                        raise RuntimeError(f"Download failed with status {response.status}")

                    total_bytes = int(response.headers.get('Content-Length', 0))

                    with open(model_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                            downloaded_bytes += len(chunk)

                            # Update progress
                            if total_bytes > 0:
                                progress = 20.0 + (downloaded_bytes / total_bytes) * 70.0
                                task.update_progress(progress, f"Downloading... {downloaded_bytes}/{total_bytes} bytes")

            task.update_progress(90.0, "Validating download")

            # Basic validation - check file size
            if model_path.stat().st_size == 0:
                model_path.unlink()  # Remove empty file
                raise RuntimeError("Downloaded file is empty")

            task.update_progress(100.0, "Download completed")

            return TaskResult(
                success=True,
                data={
                    'status': 'downloaded',
                    'path': str(model_path),
                    'size_bytes': downloaded_bytes,
                    'model_type': model_type
                },
                output_files=[model_path]
            )

        except Exception as e:
            logger.error(f"Model download failed: {e}")
            return TaskResult(
                success=False,
                error_message=str(e),
                error_details={'exception': str(e), 'task_type': task.type}
            )


class ImageProcessingExecutor(TaskExecutorInterface):
    """
    Executor for image processing and manipulation tasks.
    """

    def __init__(self, temp_dir: Path):
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def get_resource_requirements(self) -> Dict[str, Any]:
        """Get resource requirements for image processing."""
        return {
            'cpu_percent': 10.0,  # Moderate CPU usage
            'memory_percent': 8.0,  # Moderate memory usage
            'isolation_level': 'thread'  # Can run in thread
        }

    def can_execute(self, task: Task) -> bool:
        """Check if this executor can handle image processing tasks."""
        return task.type in ['image_process', 'image_resize', 'image_convert']

    async def execute(self, task: Task) -> TaskResult:
        """
        Execute an image processing task.

        Args:
            task: Task containing image processing parameters

        Returns:
            Task result with processed images
        """
        try:
            # Extract processing parameters
            input_path = task.parameters.get('input_path')
            output_path = task.parameters.get('output_path')
            operation = task.parameters.get('operation', 'resize')
            params = task.parameters.get('params', {})

            if not input_path:
                raise ValueError("Input path not provided")

            input_file = Path(input_path)
            if not input_file.exists():
                raise FileNotFoundError(f"Input file not found: {input_file}")

            task.update_progress(20.0, "Loading image")

            # Import PIL for image processing
            try:
                from PIL import Image
            except ImportError:
                raise RuntimeError("PIL not available for image processing")

            # Load image
            with Image.open(input_file) as img:
                task.update_progress(40.0, f"Processing image ({operation})")

                # Perform requested operation
                if operation == 'resize':
                    width = params.get('width')
                    height = params.get('height')
                    if width and height:
                        img = img.resize((width, height), Image.Resampling.LANCZOS)

                elif operation == 'convert':
                    format = params.get('format', 'PNG')
                    # Convert format will be handled during save

                elif operation == 'crop':
                    left = params.get('left', 0)
                    top = params.get('top', 0)
                    right = params.get('right', img.width)
                    bottom = params.get('bottom', img.height)
                    img = img.crop((left, top, right, bottom))

                else:
                    raise ValueError(f"Unsupported operation: {operation}")

                task.update_progress(80.0, "Saving result")

                # Determine output path
                if not output_path:
                    output_file = self.temp_dir / f"processed_{input_file.name}"
                else:
                    output_file = Path(output_path)

                # Ensure output directory exists
                output_file.parent.mkdir(parents=True, exist_ok=True)

                # Save image
                format = params.get('format', input_file.suffix[1:].upper() if input_file.suffix else 'PNG')
                if format.upper() == 'JPG':
                    format = 'JPEG'

                save_kwargs = {}
                if format.upper() in ['JPEG', 'JPG']:
                    save_kwargs['quality'] = params.get('quality', 85)

                img.save(output_file, format, **save_kwargs)

            task.update_progress(100.0, "Processing completed")

            return TaskResult(
                success=True,
                data={
                    'operation': operation,
                    'input_path': str(input_file),
                    'output_path': str(output_file),
                    'format': format
                },
                output_files=[output_file]
            )

        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            return TaskResult(
                success=False,
                error_message=str(e),
                error_details={'exception': str(e), 'task_type': task.type}
            )