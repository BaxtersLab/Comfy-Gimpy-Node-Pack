"""
Workflow execution engine for ComfyUI integration.
"""

import asyncio
import json
import logging
import uuid
import time
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
import websockets
import requests
from shared.config import load_config
from shared.protocol import WorkflowRequest, WorkflowResponse
from shared.history import HistoryManager

logger = logging.getLogger(__name__)

class WorkflowStatus(Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class WorkflowExecution:
    """Represents a workflow execution instance."""
    task_id: str
    request: WorkflowRequest
    status: WorkflowStatus = WorkflowStatus.PENDING
    progress: float = 0.0
    current_node: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    callbacks: List[Callable] = field(default_factory=list)

class WorkflowExecutionEngine:
    """Engine for executing ComfyUI workflows."""

    def __init__(self):
        self.config = load_config()
        self.history_manager = HistoryManager()
        self.active_executions: Dict[str, WorkflowExecution] = {}
        self.execution_queue: List[WorkflowExecution] = []
        self.result_cache: Dict[str, Dict[str, Any]] = {}
        self._running = False

    def start(self):
        """Start the execution engine."""
        self._running = True
        logger.info("Workflow execution engine started")

    def stop(self):
        """Stop the execution engine."""
        self._running = False
        # Cancel all active executions
        for execution in self.active_executions.values():
            if execution.status == WorkflowStatus.RUNNING:
                execution.status = WorkflowStatus.CANCELLED
                execution.error_message = "Engine stopped"
        logger.info("Workflow execution engine stopped")

    def submit_workflow(self, request: WorkflowRequest, callback: Optional[Callable] = None) -> str:
        """
        Submit a workflow for execution.

        Args:
            request: Workflow request
            callback: Optional callback for progress updates

        Returns:
            Task ID for the execution
        """
        task_id = str(uuid.uuid4())
        execution = WorkflowExecution(
            task_id=task_id,
            request=request,
            callbacks=[callback] if callback else []
        )

        self.execution_queue.append(execution)
        logger.info(f"Workflow submitted: {task_id}")
        return task_id

    def get_execution_status(self, task_id: str) -> Optional[WorkflowExecution]:
        """Get execution status by task ID."""
        # Check active executions first
        execution = self.active_executions.get(task_id)
        if execution:
            return execution

        # Check queued executions
        for queued_execution in self.execution_queue:
            if queued_execution.task_id == task_id:
                return queued_execution

        return None

    def cancel_execution(self, task_id: str) -> bool:
        """Cancel a running execution."""
        execution = self.active_executions.get(task_id)
        if execution and execution.status == WorkflowStatus.RUNNING:
            execution.status = WorkflowStatus.CANCELLED
            execution.error_message = "Cancelled by user"
            logger.info(f"Workflow cancelled: {task_id}")
            return True
        return False

    async def _execute_workflow_async(self, execution: WorkflowExecution) -> None:
        """Execute a workflow asynchronously."""
        try:
            execution.status = WorkflowStatus.RUNNING
            execution.start_time = time.time()

            # Check cache first
            cache_key = self._generate_cache_key(execution.request)
            if cache_key in self.result_cache:
                logger.info(f"Using cached result for {execution.task_id}")
                execution.result = self.result_cache[cache_key]
                execution.status = WorkflowStatus.COMPLETED
                return

            # Load workflow template
            workflow_data = self._load_workflow_template(execution.request.workflow_name)
            if not workflow_data:
                raise ValueError(f"Workflow template not found: {execution.request.workflow_name}")

            # Prepare workflow with parameters
            prepared_workflow = self._prepare_workflow(workflow_data, execution.request)

            # Execute via ComfyUI
            result = await self._execute_via_comfyui(prepared_workflow, execution)

            # Cache result
            if result:
                self.result_cache[cache_key] = result

            # Save to history
            self._save_to_history(execution, result)

            execution.status = WorkflowStatus.COMPLETED
            execution.result = result

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            execution.status = WorkflowStatus.FAILED
            execution.error_message = str(e)
        finally:
            execution.end_time = time.time()
            # Notify callbacks
            for callback in execution.callbacks:
                try:
                    callback(execution)
                except Exception as e:
                    logger.error(f"Callback failed: {e}")

    def _load_workflow_template(self, name: str) -> Optional[Dict[str, Any]]:
        """Load workflow template."""
        try:
            from comfy_extension.workflow_loader import load_workflow_template
            return load_workflow_template(name)
        except Exception as e:
            logger.error(f"Failed to load workflow template {name}: {e}")
            return None

    def _prepare_workflow(self, workflow_data: Dict[str, Any], request: WorkflowRequest) -> Dict[str, Any]:
        """Prepare workflow with request parameters."""
        prepared = json.loads(json.dumps(workflow_data))  # Deep copy

        # Apply parameters based on workflow type and request
        if request.mode == "generate":
            self._prepare_generation_workflow(prepared, request)
        elif request.mode == "inpaint":
            self._prepare_inpainting_workflow(prepared, request)
        elif request.mode == "upscale":
            self._prepare_upscale_workflow(prepared, request)

        # Apply common parameters
        self._apply_common_parameters(prepared, request.params)

        return prepared

    def _prepare_generation_workflow(self, workflow: Dict[str, Any], request: WorkflowRequest):
        """Prepare a text-to-image generation workflow."""
        # Find and update text prompts
        for node_id, node in workflow.items():
            if node.get("class_type") == "CLIPTextEncode":
                if "Prompt" in node.get("_meta", {}).get("title", ""):
                    if request.params and "prompt" in request.params:
                        node["inputs"]["text"] = request.params["prompt"]
                elif "Negative" in node.get("_meta", {}).get("title", ""):
                    if request.params and "negative_prompt" in request.params:
                        node["inputs"]["text"] = request.params["negative_prompt"]

            # Update latent image dimensions
            elif node.get("class_type") == "EmptyLatentImage":
                if request.params:
                    if "width" in request.params:
                        node["inputs"]["width"] = request.params["width"]
                    if "height" in request.params:
                        node["inputs"]["height"] = request.params["height"]

            # Update sampler settings
            elif node.get("class_type") == "KSampler":
                if request.params:
                    if "steps" in request.params:
                        node["inputs"]["steps"] = request.params["steps"]
                    if "cfg" in request.params:
                        node["inputs"]["cfg"] = request.params["cfg"]
                    if "seed" in request.params:
                        node["inputs"]["seed"] = request.params["seed"]
                    if "sampler" in request.params:
                        node["inputs"]["sampler_name"] = request.params["sampler"]
                    if "scheduler" in request.params:
                        node["inputs"]["scheduler"] = request.params["scheduler"]

    def _prepare_inpainting_workflow(self, workflow: Dict[str, Any], request: WorkflowRequest):
        """Prepare an inpainting workflow."""
        # Similar to generation but with image/mask inputs
        self._prepare_generation_workflow(workflow, request)

        # Handle input images
        if request.image:
            # Save image to temp and update LoadImage node
            image_path = self._save_temp_image(request.image, "input_image.png")
            for node_id, node in workflow.items():
                if node.get("class_type") == "LoadImage":
                    node["inputs"]["image"] = image_path.name

        if request.mask:
            # Save mask to temp and update LoadImage node for mask
            mask_path = self._save_temp_image(request.mask, "mask.png")
            for node_id, node in workflow.items():
                if node.get("class_type") == "LoadImage" and "mask" in node.get("_meta", {}).get("title", "").lower():
                    node["inputs"]["image"] = mask_path.name

    def _prepare_upscale_workflow(self, workflow: Dict[str, Any], request: WorkflowRequest):
        """Prepare an upscaling workflow."""
        # Implementation for upscaling workflows
        pass

    def _apply_common_parameters(self, workflow: Dict[str, Any], params: Dict[str, Any]):
        """Apply common parameters to workflow."""
        if not params:
            return

        # Apply model selection if specified
        if "model" in params:
            for node_id, node in workflow.items():
                if node.get("class_type") == "CheckpointLoaderSimple":
                    node["inputs"]["ckpt_name"] = params["model"]

    def _save_temp_image(self, image_data: bytes, filename: str) -> Path:
        """Save image data to temp directory."""
        temp_path = self.config.temp_dir / filename
        with open(temp_path, 'wb') as f:
            f.write(image_data)
        return temp_path

    async def _execute_via_comfyui(self, workflow: Dict[str, Any], execution: WorkflowExecution) -> Dict[str, Any]:
        """Execute workflow via ComfyUI REST and WebSocket APIs."""
        try:
            # Submit workflow via REST API
            prompt_id = str(uuid.uuid4())
            submit_url = f"http://{self.config.comfyui_host}:{self.config.comfyui_port}/prompt"

            payload = {
                "prompt": workflow,
                "client_id": str(uuid.uuid4())  # ComfyUI client ID
            }

            response = requests.post(submit_url, json=payload)
            if response.status_code != 200:
                raise Exception(f"Failed to submit workflow: {response.text}")

            submit_result = response.json()
            prompt_id = submit_result.get("prompt_id", prompt_id)

            # Monitor via WebSocket
            uri = f"ws://{self.config.comfyui_host}:{self.config.comfyui_port}/ws?clientId={payload['client_id']}"
            async with websockets.connect(uri) as websocket:
                result = await self._monitor_execution(websocket, prompt_id, execution)
                return result

        except Exception as e:
            logger.error(f"ComfyUI execution failed: {e}")
            raise

    async def _monitor_execution(self, websocket, prompt_id: str, execution: WorkflowExecution) -> Dict[str, Any]:
        """Monitor workflow execution progress via WebSocket."""
        result = {}

        try:
            async for message in websocket:
                data = json.loads(message)

                message_type = data.get("type")

                if message_type == "execution_start":
                    execution.progress = 0.0
                    execution.current_node = data.get("data", {}).get("node", "")

                elif message_type == "execution_cached":
                    # Node was cached, update progress
                    progress_data = data.get("data", {})
                    if "nodes" in progress_data:
                        completed = progress_data.get("nodes", [])
                        execution.progress = len(completed) / max(1, progress_data.get("total", 1))

                elif message_type == "execution_success":
                    execution.progress = 1.0
                    # Get results from history endpoint
                    result = await self._get_execution_results(prompt_id)
                    break

                elif message_type == "execution_error":
                    error_data = data.get("data", {})
                    error_msg = error_data.get("message", "Unknown execution error")
                    raise Exception(f"Execution error: {error_msg}")

                elif message_type == "progress":
                    # General progress update
                    progress_data = data.get("data", {})
                    if "value" in progress_data and "max" in progress_data:
                        execution.progress = progress_data["value"] / progress_data["max"]
                        execution.current_node = progress_data.get("node", execution.current_node)

                # Check if execution was cancelled
                if execution.status == WorkflowStatus.CANCELLED:
                    # Try to interrupt the execution
                    await self._interrupt_execution(prompt_id)
                    break

        except Exception as e:
            logger.error(f"Monitoring failed: {e}")
            raise

        return result

    async def _interrupt_execution(self, prompt_id: str):
        """Interrupt a running execution."""
        try:
            interrupt_url = f"http://{self.config.comfyui_host}:{self.config.comfyui_port}/interrupt"
            response = requests.post(interrupt_url)
            if response.status_code == 200:
                logger.info(f"Interrupted execution: {prompt_id}")
            else:
                logger.warning(f"Failed to interrupt execution: {prompt_id}")
        except Exception as e:
            logger.error(f"Interrupt request failed: {e}")

    async def _get_execution_results(self, prompt_id: str) -> Dict[str, Any]:
        """Get execution results from ComfyUI."""
        try:
            # Query ComfyUI history for results
            history_url = f"http://{self.config.comfyui_host}:{self.config.comfyui_port}/history/{prompt_id}"

            # Wait a bit for results to be available
            await asyncio.sleep(0.5)

            response = requests.get(history_url)
            if response.status_code == 200:
                history = response.json()
                if prompt_id in history and "outputs" in history[prompt_id]:
                    return history[prompt_id]["outputs"]
            return {}
        except Exception as e:
            logger.error(f"Failed to get execution results: {e}")
            return {}

    def _generate_cache_key(self, request: WorkflowRequest) -> str:
        """Generate cache key for request."""
        # Create a deterministic key based on request content
        key_data = {
            "workflow_name": request.workflow_name,
            "mode": request.mode,
            "params": request.params,
            "image_hash": hash(request.image) if request.image else None,
            "mask_hash": hash(request.mask) if request.mask else None
        }
        return str(hash(json.dumps(key_data, sort_keys=True)))

    def _save_to_history(self, execution: WorkflowExecution, result: Dict[str, Any]):
        """Save execution to history."""
        try:
            # This would need to be implemented based on the HistoryManager interface
            pass
        except Exception as e:
            logger.error(f"Failed to save to history: {e}")

    async def process_queue(self):
        """Process the execution queue."""
        while self._running:
            if self.execution_queue:
                execution = self.execution_queue.pop(0)
                self.active_executions[execution.task_id] = execution
                await self._execute_workflow_async(execution)
                # Clean up completed executions after some time
                # For now, keep them for status queries
            else:
                await asyncio.sleep(0.1)  # Small delay when queue is empty