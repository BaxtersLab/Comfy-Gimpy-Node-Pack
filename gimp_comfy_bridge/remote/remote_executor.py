"""
Remote ComfyUI Node Task Executor.

Integrates remote node execution with the async task engine,
providing a unified interface for local and remote task execution.
"""

import logging
import asyncio
import time
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from datetime import datetime

from ..shared.types import RemoteTask, TaskStatus, TaskResult, ExecutionMode
from ..async_engine.api import AsyncTaskEngine
from .node_client import RemoteNodeClient
from .load_balancer import get_load_balancer, LoadBalancingResult
from .capabilities import validate_node_compatibility

logger = logging.getLogger(__name__)


@dataclass
class RemoteExecutionOptions:
    """Options for remote task execution."""
    execution_mode: ExecutionMode = ExecutionMode.AUTO
    required_capabilities: Optional[Dict[str, Any]] = None
    preferred_node: Optional[str] = None
    timeout: Optional[float] = None
    enable_failover: bool = True
    max_retries: int = 3


class RemoteTaskExecutor:
    """
    Executor for running tasks on remote ComfyUI nodes.

    Integrates with the async task engine to provide unified local/remote execution.
    """

    def __init__(self, async_engine: AsyncTaskEngine):
        """
        Initialize the remote task executor.

        Args:
            async_engine: Async task engine instance
        """
        self.async_engine = async_engine
        self.load_balancer = get_load_balancer()
        self._active_tasks: Dict[str, asyncio.Task] = {}

    async def execute_workflow(self,
                             workflow: Dict[str, Any],
                             inputs: Optional[Dict[str, Any]] = None,
                             options: Optional[RemoteExecutionOptions] = None) -> str:
        """
        Execute a workflow, potentially on a remote node.

        Args:
            workflow: ComfyUI workflow definition
            inputs: Optional workflow inputs
            options: Execution options

        Returns:
            Task ID for tracking execution
        """
        if options is None:
            options = RemoteExecutionOptions()

        # Decide execution mode
        execution_mode = self._determine_execution_mode(workflow, options)

        if execution_mode == ExecutionMode.REMOTE:
            # Execute on remote node
            return await self._execute_remote_workflow(workflow, inputs, options)
        else:
            # Execute locally
            return await self._execute_local_workflow(workflow, inputs, options)

    def _determine_execution_mode(self,
                                workflow: Dict[str, Any],
                                options: RemoteExecutionOptions) -> ExecutionMode:
        """
        Determine whether to execute locally or remotely.

        Args:
            workflow: Workflow definition
            options: Execution options

        Returns:
            Execution mode decision
        """
        # Check explicit mode preference
        if options.execution_mode == ExecutionMode.LOCAL:
            return ExecutionMode.LOCAL
        elif options.execution_mode == ExecutionMode.REMOTE:
            return ExecutionMode.REMOTE

        # Auto mode: check if remote nodes are available and suitable
        if options.execution_mode == ExecutionMode.AUTO:
            balancing_result = self.load_balancer.select_node(
                required_capabilities=options.required_capabilities,
                preferred_node=options.preferred_node
            )

            if balancing_result:
                logger.debug(f"Auto-selected remote execution on node {balancing_result.node_id}")
                return ExecutionMode.REMOTE

        # Default to local execution
        return ExecutionMode.LOCAL

    async def _execute_remote_workflow(self,
                                     workflow: Dict[str, Any],
                                     inputs: Optional[Dict[str, Any]] = None,
                                     options: Optional[RemoteExecutionOptions] = None) -> str:
        """
        Execute workflow on a remote node.

        Args:
            workflow: ComfyUI workflow
            inputs: Workflow inputs
            options: Execution options

        Returns:
            Remote task ID
        """
        if options is None:
            options = RemoteExecutionOptions()

        # Select remote node
        balancing_result = self.load_balancer.select_node_with_failover(
            required_capabilities=options.required_capabilities,
            preferred_node=options.preferred_node
        )

        if not balancing_result:
            raise RuntimeError("No suitable remote node available for execution")

        # Create remote task
        remote_task = RemoteTask(
            id=f"remote_{int(time.time() * 1000)}",
            workflow=workflow,
            inputs=inputs or {},
            node_id=balancing_result.node_id,
            node_url=balancing_result.node_url,
            status=TaskStatus.PENDING,
            submitted_at=datetime.now(),
            options=options
        )

        # Submit to async engine for tracking
        task_id = await self.async_engine.submit_remote_task(remote_task)

        # Start background execution
        execution_task = asyncio.create_task(
            self._execute_remote_task_async(remote_task, task_id)
        )
        self._active_tasks[task_id] = execution_task

        logger.info(f"Submitted remote workflow execution: {task_id} on node {balancing_result.node_id}")
        return task_id

    async def _execute_remote_task_async(self, remote_task: RemoteTask, task_id: str):
        """
        Execute remote task asynchronously.

        Args:
            remote_task: Remote task definition
            task_id: Async engine task ID
        """
        try:
            # Update status to running
            await self.async_engine.update_task_status(task_id, TaskStatus.RUNNING)

            # Execute on remote node
            async with RemoteNodeClient(remote_task.node_url, "token") as client:  # TODO: Get token from node manager
                # Submit workflow
                remote_task_id = await client.submit_workflow(
                    remote_task.workflow,
                    remote_task.inputs
                )

                # Wait for completion
                timeout = remote_task.options.timeout if remote_task.options else None
                final_status = await client.wait_for_completion(remote_task_id, timeout=timeout)

                if final_status == TaskStatus.COMPLETED:
                    # Fetch result
                    result = await client.fetch_result(remote_task_id)

                    # Update async engine with result
                    await self.async_engine.complete_task(task_id, result)

                    logger.info(f"Remote task completed successfully: {task_id}")

                elif final_status == TaskStatus.FAILED:
                    # Mark as failed
                    await self.async_engine.fail_task(task_id, "Remote execution failed")

                    logger.error(f"Remote task failed: {task_id}")

                elif final_status == TaskStatus.CANCELLED:
                    # Mark as cancelled
                    await self.async_engine.cancel_task(task_id)

                    logger.info(f"Remote task cancelled: {task_id}")

        except Exception as e:
            logger.error(f"Error in remote task execution {task_id}: {e}")
            await self.async_engine.fail_task(task_id, str(e))

        finally:
            # Clean up
            if task_id in self._active_tasks:
                del self._active_tasks[task_id]

    async def _execute_local_workflow(self,
                                    workflow: Dict[str, Any],
                                    inputs: Optional[Dict[str, Any]] = None,
                                    options: Optional[RemoteExecutionOptions] = None) -> str:
        """
        Execute workflow locally using the async engine.

        Args:
            workflow: ComfyUI workflow
            inputs: Workflow inputs
            options: Execution options (ignored for local execution)

        Returns:
            Local task ID
        """
        # Submit to local async engine
        task_id = await self.async_engine.submit_workflow(workflow, inputs)

        logger.info(f"Submitted local workflow execution: {task_id}")
        return task_id

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.

        Args:
            task_id: Task ID

        Returns:
            True if cancelled successfully
        """
        # Check if it's a remote task
        task_info = await self.async_engine.get_task(task_id)
        if not task_info:
            return False

        if hasattr(task_info, 'node_id') and task_info.node_id:
            # Remote task - cancel on remote node
            try:
                async with RemoteNodeClient(task_info.node_url, "token") as client:  # TODO: Get token
                    success = await client.cancel_task(task_info.remote_task_id)
                    if success:
                        await self.async_engine.cancel_task(task_id)
                        return True
            except Exception as e:
                logger.error(f"Failed to cancel remote task {task_id}: {e}")
                return False
        else:
            # Local task - cancel locally
            return await self.async_engine.cancel_task(task_id)

    async def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        Get the status of a task.

        Args:
            task_id: Task ID

        Returns:
            Task status or None if not found
        """
        return await self.async_engine.get_task_status(task_id)

    async def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """
        Get the result of a completed task.

        Args:
            task_id: Task ID

        Returns:
            Task result or None if not available
        """
        return await self.async_engine.get_task_result(task_id)

    async def list_tasks(self,
                        status_filter: Optional[List[TaskStatus]] = None,
                        execution_mode: Optional[ExecutionMode] = None) -> List[Dict[str, Any]]:
        """
        List tasks with optional filtering.

        Args:
            status_filter: Filter by task status
            execution_mode: Filter by execution mode

        Returns:
            List of task information
        """
        tasks = await self.async_engine.list_tasks(status_filter)

        # Filter by execution mode if specified
        if execution_mode:
            filtered_tasks = []
            for task in tasks:
                task_mode = getattr(task, 'execution_mode', ExecutionMode.LOCAL)
                if task_mode == execution_mode:
                    filtered_tasks.append(task)
            tasks = filtered_tasks

        return tasks

    def get_execution_stats(self) -> Dict[str, Any]:
        """
        Get execution statistics.

        Returns:
            Execution statistics
        """
        # Get stats from async engine
        local_stats = self.async_engine.get_stats()

        # Get remote node stats
        load_distribution = self.load_balancer.get_load_distribution()

        return {
            'local_tasks': local_stats,
            'remote_nodes': load_distribution,
            'active_remote_tasks': len(self._active_tasks)
        }

    async def validate_workflow_for_remote(self,
                                         workflow: Dict[str, Any],
                                         node_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate if a workflow can run on a remote node.

        Args:
            workflow: Workflow to validate
            node_id: Specific node ID, or None to check all available nodes

        Returns:
            Validation results
        """
        # Extract workflow requirements
        requirements = self._extract_workflow_requirements(workflow)

        if node_id:
            # Validate against specific node
            from .node_manager import get_node_manager
            node_manager = get_node_manager()
            node = node_manager.get_node(node_id)

            if not node or not node.capabilities:
                return {
                    'valid': False,
                    'reason': f'Node {node_id} not found or has no capabilities',
                    'requirements': requirements
                }

            compatibility = await validate_node_compatibility(
                node.url, "token", requirements  # TODO: Get token properly
            )

            return {
                'valid': compatibility['compatible'],
                'node_id': node_id,
                'score': compatibility['score'],
                'missing_features': compatibility['missing_features'],
                'warnings': compatibility['warnings'],
                'requirements': requirements
            }
        else:
            # Check all available nodes
            balancing_result = self.load_balancer.select_node(requirements)

            if balancing_result:
                return {
                    'valid': True,
                    'recommended_node': balancing_result.node_id,
                    'reason': balancing_result.reason,
                    'requirements': requirements
                }
            else:
                return {
                    'valid': False,
                    'reason': 'No compatible remote nodes available',
                    'requirements': requirements
                }

    def _extract_workflow_requirements(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract resource requirements from workflow.

        Args:
            workflow: ComfyUI workflow

        Returns:
            Resource requirements
        """
        # This is a simplified extraction - in practice, this would analyze
        # the workflow nodes to determine requirements

        requirements = {
            'min_vram_gb': 4,  # Default minimum
            'required_models': [],
            'required_workflow': None
        }

        # Look for model loading nodes
        for node_id, node_data in workflow.items():
            if isinstance(node_data, dict):
                node_class = node_data.get('class_type', '')

                # Check for model loaders
                if 'Loader' in node_class or 'Checkpoint' in node_class:
                    # Assume SD1.5 models need at least 4GB VRAM
                    requirements['min_vram_gb'] = max(requirements['min_vram_gb'], 4)

                elif 'SDXL' in node_class:
                    # SDXL models need more VRAM
                    requirements['min_vram_gb'] = max(requirements['min_vram_gb'], 8)

                # Add other requirement checks as needed

        return requirements

    async def cleanup_completed_tasks(self):
        """Clean up completed remote tasks."""
        # This would clean up old task data
        # For now, just log active tasks
        logger.debug(f"Active remote tasks: {len(self._active_tasks)}")


# Global remote executor instance
_remote_executor: Optional[RemoteTaskExecutor] = None


def initialize_remote_executor(async_engine: AsyncTaskEngine) -> RemoteTaskExecutor:
    """Initialize the global remote task executor."""
    global _remote_executor
    if _remote_executor is None:
        _remote_executor = RemoteTaskExecutor(async_engine)
    return _remote_executor


def get_remote_executor() -> RemoteTaskExecutor:
    """Get the global remote task executor instance."""
    if _remote_executor is None:
        raise RuntimeError("Remote executor not initialized")
    return _remote_executor