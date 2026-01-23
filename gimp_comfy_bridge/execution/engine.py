"""
ComfyUI Execution Engine - Phase 9
Real ComfyUI workflow execution integration for end-to-end creative pipelines.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from enum import Enum

import aiohttp
import websockets

from shared.config import get_config
from shared.types import ExecutionResult, ExecutionStatus, WorkflowData
from gimp_comfy_bridge.workflow_auto.builder import WorkflowBuilder
from gimp_comfy_bridge.fusion.engine import FusionResult

logger = logging.getLogger(__name__)


class ExecutionState(Enum):
    """Execution state enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExecutionOptions:
    """Options for workflow execution."""
    timeout: int = 300  # 5 minutes default timeout
    max_retries: int = 3
    retry_delay: float = 1.0
    enable_progress_tracking: bool = True
    save_intermediate_results: bool = False
    output_format: str = "png"
    quality: int = 95
    enable_websocket_monitoring: bool = True


@dataclass
class ExecutionJob:
    """Represents a single execution job."""
    job_id: str
    workflow_data: WorkflowData
    options: ExecutionOptions
    fusion_result: Optional[FusionResult] = None
    status: ExecutionState = ExecutionState.PENDING
    progress: float = 0.0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    result: Optional[ExecutionResult] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    websocket_client_id: Optional[str] = None


class ComfyUIClient:
    """Client for communicating with ComfyUI server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8188):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.ws_url = f"ws://{host}:{port}/ws"
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get_system_stats(self) -> Dict[str, Any]:
        """Get ComfyUI system statistics."""
        try:
            async with self.session.get(f"{self.base_url}/system_stats") as response:
                return await response.json()
        except Exception as e:
            logger.error(f"Failed to get system stats: {e}")
            return {}

    async def get_history(self, prompt_id: Optional[str] = None) -> Dict[str, Any]:
        """Get execution history."""
        try:
            url = f"{self.base_url}/history"
            if prompt_id:
                url += f"/{prompt_id}"
            async with self.session.get(url) as response:
                return await response.json()
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return {}

    async def queue_prompt(self, workflow: Dict[str, Any]) -> str:
        """Queue a workflow prompt for execution."""
        try:
            payload = {"prompt": workflow}
            async with self.session.post(f"{self.base_url}/prompt", json=payload) as response:
                result = await response.json()
                return result.get("prompt_id")
        except Exception as e:
            logger.error(f"Failed to queue prompt: {e}")
            raise

    async def interrupt_execution(self) -> bool:
        """Interrupt current execution."""
        try:
            async with self.session.post(f"{self.base_url}/interrupt") as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Failed to interrupt execution: {e}")
            return False

    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        try:
            async with self.session.get(f"{self.base_url}/queue") as response:
                return await response.json()
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            return {}


class WebSocketMonitor:
    """WebSocket monitor for real-time execution progress."""

    def __init__(self, client: ComfyUIClient):
        self.client = client
        self.websocket = None
        self.monitoring_jobs: Dict[str, ExecutionJob] = {}

    async def connect(self) -> bool:
        """Connect to ComfyUI WebSocket."""
        try:
            self.websocket = await websockets.connect(self.client.ws_url)
            logger.info("Connected to ComfyUI WebSocket")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            return False

    async def disconnect(self):
        """Disconnect from WebSocket."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None

    async def monitor_job(self, job: ExecutionJob):
        """Monitor a specific job's progress."""
        if not self.websocket:
            return

        self.monitoring_jobs[job.job_id] = job

        try:
            async for message in self.websocket:
                data = json.loads(message)

                # Update job progress based on WebSocket messages
                if "type" in data:
                    if data["type"] == "execution_start":
                        job.status = ExecutionState.RUNNING
                        job.start_time = time.time()
                        logger.info(f"Execution started for job {job.job_id}")

                    elif data["type"] == "execution_cached":
                        job.progress = 1.0
                        logger.info(f"Execution cached for job {job.job_id}")

                    elif data["type"] == "executing":
                        # Update progress based on node execution
                        if "data" in data and "node" in data["data"]:
                            # Estimate progress (this is approximate)
                            job.progress = min(0.9, job.progress + 0.1)

                    elif data["type"] == "progress":
                        if "data" in data and "value" in data["data"]:
                            job.progress = data["data"]["value"] / 100.0

                    elif data["type"] == "execution_success":
                        job.status = ExecutionState.COMPLETED
                        job.progress = 1.0
                        job.end_time = time.time()
                        logger.info(f"Execution completed for job {job.job_id}")
                        break

                    elif data["type"] == "execution_error":
                        job.status = ExecutionState.FAILED
                        job.error_message = data.get("data", {}).get("message", "Unknown error")
                        job.end_time = time.time()
                        logger.error(f"Execution failed for job {job.job_id}: {job.error_message}")
                        break

        except Exception as e:
            logger.error(f"WebSocket monitoring error for job {job.job_id}: {e}")
            job.status = ExecutionState.FAILED
            job.error_message = str(e)
            job.end_time = time.time()

        finally:
            self.monitoring_jobs.pop(job.job_id, None)


class ExecutionEngine:
    """Main execution engine for ComfyUI workflows."""

    def __init__(self):
        self.config = get_config()
        self.comfy_client = ComfyUIClient(
            host=self.config.get("comfyui_host", "127.0.0.1"),
            port=self.config.get("comfyui_port", 8188)
        )
        self.websocket_monitor = WebSocketMonitor(self.comfy_client)
        self.workflow_builder = WorkflowBuilder()
        self.active_jobs: Dict[str, ExecutionJob] = {}
        self.job_queue: asyncio.Queue = asyncio.Queue()
        self.executor_task: Optional[asyncio.Task] = None
        self.is_running = False

    async def start(self):
        """Start the execution engine."""
        if self.is_running:
            return

        self.is_running = True
        logger.info("Starting ComfyUI Execution Engine")

        # Connect WebSocket monitor
        await self.websocket_monitor.connect()

        # Start job executor
        self.executor_task = asyncio.create_task(self._job_executor())

        logger.info("ComfyUI Execution Engine started")

    async def stop(self):
        """Stop the execution engine."""
        if not self.is_running:
            return

        self.is_running = False
        logger.info("Stopping ComfyUI Execution Engine")

        # Cancel executor task
        if self.executor_task:
            self.executor_task.cancel()
            try:
                await self.executor_task
            except asyncio.CancelledError:
                pass

        # Disconnect WebSocket monitor
        await self.websocket_monitor.disconnect()

        # Cancel all active jobs
        for job in self.active_jobs.values():
            if job.status == ExecutionState.RUNNING:
                job.status = ExecutionState.CANCELLED

        self.active_jobs.clear()
        logger.info("ComfyUI Execution Engine stopped")

    async def execute_workflow(
        self,
        workflow_data: Union[WorkflowData, Dict[str, Any]],
        options: Optional[ExecutionOptions] = None,
        fusion_result: Optional[FusionResult] = None
    ) -> ExecutionJob:
        """Execute a workflow with optional fusion result integration."""

        # Convert dict to WorkflowData if needed
        if isinstance(workflow_data, dict):
            workflow_data = WorkflowData(**workflow_data)

        # Create execution job
        job_id = f"exec_{int(time.time() * 1000)}_{hash(str(workflow_data)) % 10000}"
        job = ExecutionJob(
            job_id=job_id,
            workflow_data=workflow_data,
            options=options or ExecutionOptions(),
            fusion_result=fusion_result
        )

        # Add to active jobs and queue
        self.active_jobs[job_id] = job
        await self.job_queue.put(job)

        logger.info(f"Queued execution job {job_id}")
        return job

    async def execute_fusion_result(
        self,
        fusion_result: FusionResult,
        template_id: str,
        style_id: str,
        options: Optional[ExecutionOptions] = None
    ) -> List[ExecutionJob]:
        """Execute all variants from a fusion result."""

        jobs = []

        for variant in fusion_result.variants:
            # Build workflow for this variant
            workflow_result = await self.workflow_builder.build_workflow(
                template_id=template_id,
                style_id=style_id,
                options={
                    "variant_data": variant.dict(),
                    "fusion_metadata": fusion_result.metadata
                }
            )

            if workflow_result and workflow_result.success:
                job = await self.execute_workflow(
                    workflow_result.workflow,
                    options or ExecutionOptions(),
                    fusion_result
                )
                jobs.append(job)
            else:
                logger.error(f"Failed to build workflow for variant: {variant.id}")

        return jobs

    async def get_job_status(self, job_id: str) -> Optional[ExecutionJob]:
        """Get the status of a job."""
        return self.active_jobs.get(job_id)

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        job = self.active_jobs.get(job_id)
        if job and job.status == ExecutionState.RUNNING:
            # Interrupt ComfyUI execution
            success = await self.comfy_client.interrupt_execution()
            if success:
                job.status = ExecutionState.CANCELLED
                job.end_time = time.time()
                logger.info(f"Cancelled job {job_id}")
                return True

        return False

    async def get_system_status(self) -> Dict[str, Any]:
        """Get ComfyUI system status."""
        try:
            stats = await self.comfy_client.get_system_stats()
            queue_status = await self.comfy_client.get_queue_status()

            return {
                "comfyui_connected": True,
                "system_stats": stats,
                "queue_status": queue_status,
                "active_jobs": len([j for j in self.active_jobs.values()
                                  if j.status == ExecutionState.RUNNING]),
                "pending_jobs": self.job_queue.qsize()
            }
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {
                "comfyui_connected": False,
                "error": str(e),
                "active_jobs": len([j for j in self.active_jobs.values()
                                  if j.status == ExecutionState.RUNNING]),
                "pending_jobs": self.job_queue.qsize()
            }

    async def _job_executor(self):
        """Main job execution loop."""
        while self.is_running:
            try:
                # Get next job from queue
                job = await self.job_queue.get()

                # Execute the job
                await self._execute_job(job)

                # Mark queue task as done
                self.job_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Job executor error: {e}")
                await asyncio.sleep(1)

    async def _execute_job(self, job: ExecutionJob):
        """Execute a single job."""
        try:
            job.status = ExecutionState.RUNNING
            job.start_time = time.time()
            logger.info(f"Starting execution of job {job.job_id}")

            # Convert workflow data to ComfyUI format
            comfy_workflow = self._convert_to_comfy_format(job.workflow_data)

            # Apply fusion result modifications if present
            if job.fusion_result:
                comfy_workflow = self._apply_fusion_modifications(
                    comfy_workflow, job.fusion_result
                )

            # Queue the prompt
            prompt_id = await self.comfy_client.queue_prompt(comfy_workflow)
            job.websocket_client_id = prompt_id

            # Monitor execution if enabled
            if job.options.enable_websocket_monitoring:
                await self.websocket_monitor.monitor_job(job)
            else:
                # Simple polling-based monitoring
                await self._poll_job_completion(job, prompt_id)

            # Process results
            if job.status == ExecutionState.COMPLETED:
                await self._process_execution_results(job, prompt_id)

        except Exception as e:
            logger.error(f"Job execution failed for {job.job_id}: {e}")
            job.status = ExecutionState.FAILED
            job.error_message = str(e)
            job.end_time = time.time()

        finally:
            # Clean up completed/failed jobs after some time
            if job.status in [ExecutionState.COMPLETED, ExecutionState.FAILED]:
                asyncio.create_task(self._cleanup_job_later(job.job_id, 300))  # 5 minutes

    async def _poll_job_completion(self, job: ExecutionJob, prompt_id: str):
        """Poll for job completion (fallback when WebSocket unavailable)."""
        max_attempts = 300  # 5 minutes with 1 second intervals
        attempt = 0

        while attempt < max_attempts and job.status == ExecutionState.RUNNING:
            try:
                history = await self.comfy_client.get_history(prompt_id)
                if prompt_id in history:
                    execution_data = history[prompt_id]
                    if "status" in execution_data:
                        status = execution_data["status"]
                        if status.get("completed", False):
                            job.status = ExecutionState.COMPLETED
                            job.progress = 1.0
                            job.end_time = time.time()
                            break
                        elif status.get("error"):
                            job.status = ExecutionState.FAILED
                            job.error_message = status["error"]
                            job.end_time = time.time()
                            break

                    # Update progress
                    progress = status.get("progress", {}).get("value", 0)
                    job.progress = progress / 100.0

                await asyncio.sleep(1)
                attempt += 1

            except Exception as e:
                logger.error(f"Polling error for job {job.job_id}: {e}")
                await asyncio.sleep(1)
                attempt += 1

        if job.status == ExecutionState.RUNNING:
            # Timeout
            job.status = ExecutionState.FAILED
            job.error_message = "Execution timeout"
            job.end_time = time.time()

    async def _process_execution_results(self, job: ExecutionJob, prompt_id: str):
        """Process execution results and create ExecutionResult."""
        try:
            history = await self.comfy_client.get_history(prompt_id)
            if prompt_id in history:
                execution_data = history[prompt_id]
                outputs = execution_data.get("outputs", {})

                # Convert ComfyUI outputs to ExecutionResult format
                result_outputs = {}
                for node_id, node_outputs in outputs.items():
                    for output_key, output_data in node_outputs.items():
                        if isinstance(output_data, list) and len(output_data) > 0:
                            # Handle image outputs
                            result_outputs[f"{node_id}_{output_key}"] = output_data

                job.result = ExecutionResult(
                    success=True,
                    outputs=result_outputs,
                    execution_time=job.end_time - job.start_time if job.end_time and job.start_time else 0,
                    metadata={
                        "prompt_id": prompt_id,
                        "comfyui_history": execution_data
                    }
                )

        except Exception as e:
            logger.error(f"Failed to process results for job {job.job_id}: {e}")
            job.result = ExecutionResult(
                success=False,
                error=str(e),
                execution_time=job.end_time - job.start_time if job.end_time and job.start_time else 0
            )

    def _convert_to_comfy_format(self, workflow_data: WorkflowData) -> Dict[str, Any]:
        """Convert WorkflowData to ComfyUI workflow format."""
        # This is a simplified conversion - in practice, this would need
        # to handle the specific ComfyUI workflow JSON structure
        return workflow_data.workflow_json

    def _apply_fusion_modifications(
        self,
        workflow: Dict[str, Any],
        fusion_result: FusionResult
    ) -> Dict[str, Any]:
        """Apply fusion result modifications to workflow."""
        # Apply LoRA weights, style modifications, etc.
        # This would modify the workflow JSON based on fusion parameters
        modified_workflow = workflow.copy()

        # Example: Apply LoRA weights to relevant nodes
        if fusion_result.lora_weights:
            for node_id, node_data in modified_workflow.items():
                if node_data.get("class_type") == "LoraLoader":
                    # Apply LoRA weights
                    pass

        return modified_workflow

    async def _cleanup_job_later(self, job_id: str, delay: int):
        """Clean up a completed job after a delay."""
        await asyncio.sleep(delay)
        self.active_jobs.pop(job_id, None)
        logger.debug(f"Cleaned up job {job_id}")


# Global execution engine instance
_execution_engine: Optional[ExecutionEngine] = None


async def get_execution_engine() -> ExecutionEngine:
    """Get the global execution engine instance."""
    global _execution_engine
    if _execution_engine is None:
        _execution_engine = ExecutionEngine()
        await _execution_engine.start()
    return _execution_engine


async def initialize_execution_engine() -> ExecutionEngine:
    """Initialize the execution engine."""
    return await get_execution_engine()


async def execute_workflow(
    workflow_data: Union[WorkflowData, Dict[str, Any]],
    options: Optional[ExecutionOptions] = None,
    fusion_result: Optional[FusionResult] = None
) -> ExecutionJob:
    """Execute a workflow (convenience function)."""
    engine = await get_execution_engine()
    return await engine.execute_workflow(workflow_data, options, fusion_result)


async def execute_fusion_result(
    fusion_result: FusionResult,
    template_id: str,
    style_id: str,
    options: Optional[ExecutionOptions] = None
) -> List[ExecutionJob]:
    """Execute all variants from a fusion result (convenience function)."""
    engine = await get_execution_engine()
    return await engine.execute_fusion_result(fusion_result, template_id, style_id, options)