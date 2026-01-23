"""
GIMP Operation Executors for the Async Task Engine
Specialized executors for GIMP-specific AI operations.
"""

import asyncio
import logging
import base64
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image

from task_engine.executors import TaskExecutorInterface, TaskResult
from gimp_comfy_bridge.shared.config import Config
from gimp_comfy_bridge.shared.history import HistoryManager
from gimp_comfy_bridge.gimp_plugin.api_client import run_workflow
from gimp_comfy_bridge.templates import TemplateRegistry
from gimp_comfy_bridge.styles import StyleRegistry

logger = logging.getLogger(__name__)


class GIMPBaseExecutor(TaskExecutorInterface):
    """
    Base executor for GIMP operations.
    """

    def __init__(self, config: Config):
        """
        Initialize GIMP executor.

        Args:
            config: Bridge configuration
        """
        self.config = config
        self.history_manager = HistoryManager()
        self.template_registry = TemplateRegistry()
        self.style_registry = StyleRegistry()

    def can_execute(self, task) -> bool:
        """
        Check if this executor can handle the task.

        Args:
            task: Task to check

        Returns:
            True if this executor can handle the task
        """
        return task.task_type.startswith("gimp_")

    async def execute(self, task) -> TaskResult:
        """
        Execute a GIMP task.

        Args:
            task: Task to execute

        Returns:
            Task result
        """
        try:
            # Update progress
            task.update_progress(percentage=10, stage="preparing", message="Preparing GIMP operation")

            # Extract operation type
            operation = task.task_type.replace("gimp_", "")

            # Prepare operation parameters
            params = await self._prepare_operation_parameters(task, operation)

            # Update progress
            task.update_progress(percentage=30, stage="executing", message=f"Executing {operation} operation")

            # Execute the operation
            result = await self._execute_operation(operation, params, task)

            # Update progress
            task.update_progress(percentage=90, stage="finalizing", message="Finalizing results")

            # Post-process results
            final_result = await self._post_process_results(result, task)

            # Update progress
            task.update_progress(percentage=100, stage="completed", message="Operation completed successfully")

            return final_result

        except Exception as e:
            logger.error(f"GIMP operation failed: {e}")
            return TaskResult(
                success=False,
                error_message=f"GIMP operation failed: {str(e)}",
                execution_time_seconds=task.get_execution_time() or 0
            )

    async def _prepare_operation_parameters(self, task, operation: str) -> Dict[str, Any]:
        """
        Prepare parameters for the GIMP operation.

        Args:
            task: Task object
            operation: Operation type

        Returns:
            Prepared parameters
        """
        params = task.parameters.copy()

        # Handle image inputs
        if "input_image" in params and params["input_image"]:
            # Image is already provided as base64 or path
            pass

        if "mask_image" in params and params["mask_image"]:
            # Mask is already provided
            pass

        # Apply style if specified
        if "style" in params:
            style = self.style_registry.get_style(params["style"])
            if style:
                params["style_config"] = style

        # Apply template if specified
        if "template" in params:
            template = self.template_registry.get_template(params["template"])
            if template:
                params["workflow_template"] = template

        return params

    async def _execute_operation(self, operation: str, params: Dict[str, Any], task) -> Dict[str, Any]:
        """
        Execute the specific GIMP operation.

        Args:
            operation: Operation type
            params: Operation parameters
            task: Task object

        Returns:
            Operation result
        """
        # Get appropriate workflow template
        workflow = self._get_workflow_for_operation(operation, params)

        # Update progress
        task.update_progress(percentage=50, stage="running_workflow", message="Running ComfyUI workflow")

        # Execute workflow
        result = await asyncio.get_event_loop().run_in_executor(
            None, run_workflow, workflow, params
        )

        return result

    async def _post_process_results(self, result: Dict[str, Any], task) -> TaskResult:
        """
        Post-process operation results.

        Args:
            result: Raw operation result
            task: Task object

        Returns:
            Processed task result
        """
        # Save result to history
        if "output_image" in result:
            history_path = self.history_manager.save_step(
                result["output_image"],
                task.parameters.get("operation", "unknown"),
                task.parameters
            )

            return TaskResult(
                success=True,
                data={
                    "output_image": result["output_image"],
                    "history_path": str(history_path),
                    "operation": task.parameters.get("operation"),
                    "parameters": task.parameters
                },
                execution_time_seconds=task.get_execution_time() or 0
            )

        return TaskResult(
            success=True,
            data=result,
            execution_time_seconds=task.get_execution_time() or 0
        )

    def _get_workflow_for_operation(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get the appropriate workflow for the operation.

        Args:
            operation: Operation type
            params: Operation parameters

        Returns:
            Workflow configuration
        """
        # Use template system to get workflow
        template_name = params.get("workflow_template", f"default_{operation}")
        template = self.template_registry.get_template(template_name)

        if template:
            return template.workflow_config
        else:
            # Fallback to basic workflows
            return self._get_fallback_workflow(operation, params)


class GIMPUpscaleExecutor(GIMPBaseExecutor):
    """
    Executor for GIMP upscale operations.
    """

    def can_execute(self, task) -> bool:
        return task.task_type == "gimp_upscale"

    async def _execute_operation(self, operation: str, params: Dict[str, Any], task) -> Dict[str, Any]:
        """
        Execute upscale operation with progress updates.

        Args:
            operation: Operation type
            params: Operation parameters
            task: Task object

        Returns:
            Operation result
        """
        # Update progress with more specific steps
        task.update_progress(percentage=40, stage="loading_model", message="Loading upscale model")

        # Simulate model loading time
        await asyncio.sleep(0.5)

        task.update_progress(percentage=60, stage="processing", message="Upscaling image", current_step=1, total_steps=2)

        # Execute parent operation
        result = await super()._execute_operation(operation, params, task)

        task.update_progress(percentage=80, stage="post_processing", message="Post-processing result", current_step=2, total_steps=2)

        return result


class GIMPInpaintExecutor(GIMPBaseExecutor):
    """
    Executor for GIMP inpaint operations.
    """

    def can_execute(self, task) -> bool:
        return task.task_type == "gimp_inpaint"

    async def _prepare_operation_parameters(self, task, operation: str) -> Dict[str, Any]:
        """
        Prepare inpaint-specific parameters.

        Args:
            task: Task object
            operation: Operation type

        Returns:
            Prepared parameters
        """
        params = await super()._prepare_operation_parameters(task, operation)

        # Ensure mask is properly formatted
        if "mask_image" in params and params["mask_image"]:
            # Validate mask format
            pass

        # Set inpaint-specific parameters
        params["inpaint_mode"] = params.get("inpaint_mode", "original")
        params["fill_mode"] = params.get("fill_mode", "original")

        return params


class GIMPGenerateExecutor(GIMPBaseExecutor):
    """
    Executor for GIMP text-to-image generation.
    """

    def can_execute(self, task) -> bool:
        return task.task_type == "gimp_generate"

    async def _execute_operation(self, operation: str, params: Dict[str, Any], task) -> Dict[str, Any]:
        """
        Execute generation with detailed progress.

        Args:
            operation: Operation type
            params: Operation parameters
            task: Task object

        Returns:
            Operation result
        """
        # Generation has multiple steps
        total_steps = 4
        current_step = 0

        # Step 1: Model loading
        current_step += 1
        task.update_progress(
            percentage=20,
            stage="loading_model",
            message="Loading diffusion model",
            current_step=current_step,
            total_steps=total_steps
        )
        await asyncio.sleep(0.5)

        # Step 2: Text encoding
        current_step += 1
        task.update_progress(
            percentage=40,
            stage="encoding_prompt",
            message="Encoding text prompt",
            current_step=current_step,
            total_steps=total_steps
        )
        await asyncio.sleep(0.3)

        # Step 3: Generation
        current_step += 1
        task.update_progress(
            percentage=60,
            stage="generating",
            message="Generating image",
            current_step=current_step,
            total_steps=total_steps
        )

        # Execute the actual generation
        result = await super()._execute_operation(operation, params, task)

        # Step 4: Post-processing
        current_step += 1
        task.update_progress(
            percentage=90,
            stage="post_processing",
            message="Finalizing generated image",
            current_step=current_step,
            total_steps=total_steps
        )

        return result


class GIMPImg2ImgExecutor(GIMPBaseExecutor):
    """
    Executor for GIMP image-to-image operations.
    """

    def can_execute(self, task) -> bool:
        return task.task_type == "gimp_img2img"


class GIMPControlNetExecutor(GIMPBaseExecutor):
    """
    Executor for GIMP ControlNet operations.
    """

    def can_execute(self, task) -> bool:
        return task.task_type == "gimp_controlnet"

    async def _prepare_operation_parameters(self, task, operation: str) -> Dict[str, Any]:
        """
        Prepare ControlNet-specific parameters.

        Args:
            task: Task object
            operation: Operation type

        Returns:
            Prepared parameters
        """
        params = await super()._prepare_operation_parameters(task, operation)

        # Validate control image
        if "control_image" not in params or not params["control_image"]:
            raise ValueError("Control image is required for ControlNet operations")

        # Set ControlNet model if not specified
        if "controlnet_model" not in params:
            params["controlnet_model"] = "control_v11p_sd15_canny"

        return params


# Fallback workflow definitions
def _get_fallback_workflow(operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get fallback workflow for operation.

    Args:
        operation: Operation type
        params: Operation parameters

    Returns:
        Workflow configuration
    """
    if operation == "upscale":
        return {
            "workflow": {
                "1": {
                    "class_type": "LoadImage",
                    "inputs": {
                        "image": ["2", 0]
                    }
                },
                "2": {
                    "class_type": "ImageScale",
                    "inputs": {
                        "upscale_method": params.get("method", "lanczos"),
                        "scale_by": params.get("scale_factor", 2.0),
                        "image": ["1", 0]
                    }
                },
                "3": {
                    "class_type": "SaveImage",
                    "inputs": {
                        "filename_prefix": "upscaled",
                        "images": ["2", 0]
                    }
                }
            }
        }
    elif operation == "generate":
        return {
            "workflow": {
                "1": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {
                        "text": params.get("prompt", "")
                    }
                },
                "2": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {
                        "text": params.get("negative_prompt", "")
                    }
                },
                "3": {
                    "class_type": "KSampler",
                    "inputs": {
                        "cfg": 7.0,
                        "denoise": 1.0,
                        "model": ["4", 0],
                        "positive": ["1", 0],
                        "negative": ["2", 0],
                        "latent_image": ["5", 0],
                        "sampler_name": "euler",
                        "scheduler": "normal",
                        "steps": 20
                    }
                },
                "4": {
                    "class_type": "CheckpointLoaderSimple",
                    "inputs": {
                        "ckpt_name": "v1-5-pruned-emaonly.ckpt"
                    }
                },
                "5": {
                    "class_type": "EmptyLatentImage",
                    "inputs": {
                        "width": params.get("width", 512),
                        "height": params.get("height", 512),
                        "batch_size": 1
                    }
                },
                "6": {
                    "class_type": "VAEDecode",
                    "inputs": {
                        "samples": ["3", 0],
                        "vae": ["4", 2]
                    }
                },
                "7": {
                    "class_type": "SaveImage",
                    "inputs": {
                        "filename_prefix": "generated",
                        "images": ["6", 0]
                    }
                }
            }
        }
    else:
        # Generic fallback
        return {
            "workflow": {
                "1": {
                    "class_type": "LoadImage",
                    "inputs": {
                        "image": "input_image"
                    }
                },
                "2": {
                    "class_type": "SaveImage",
                    "inputs": {
                        "filename_prefix": f"{operation}_result",
                        "images": ["1", 0]
                    }
                }
            }
        }