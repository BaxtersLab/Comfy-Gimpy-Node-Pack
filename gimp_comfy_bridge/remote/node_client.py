"""
Remote ComfyUI Node Client for distributed execution.

Handles communication with remote ComfyUI instances including workflow submission,
status polling, result fetching, and error handling.
"""

import logging
import asyncio
import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import aiohttp

from ..shared.types import RemoteTask, TaskStatus, TaskResult

logger = logging.getLogger(__name__)


@dataclass
class NodeResponse:
    """Response from a remote node."""
    status_code: int
    data: Any
    error: Optional[str] = None


class RemoteNodeClient:
    """
    Client for communicating with remote ComfyUI nodes.

    Handles workflow submission, status polling, result fetching,
    and error handling for remote execution.
    """

    def __init__(self, url: str, token: str, timeout: int = 300):
        """
        Initialize the node client.

        Args:
            url: Node URL
            token: Authentication token
            timeout: Request timeout in seconds
        """
        self.url = url.rstrip('/')
        self.token = token
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self):
        """Establish connection to the remote node."""
        if self._session is None:
            self._session = aiohttp.ClientSession(
                headers={'Authorization': f'Bearer {self.token}'},
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        logger.debug(f"Connected to remote node at {self.url}")

    async def disconnect(self):
        """Close connection to the remote node."""
        if self._session:
            await self._session.close()
            self._session = None
        logger.debug(f"Disconnected from remote node at {self.url}")

    async def submit_workflow(self,
                            workflow: Dict[str, Any],
                            inputs: Optional[Dict[str, Any]] = None) -> str:
        """
        Submit a workflow for execution on the remote node.

        Args:
            workflow: ComfyUI workflow definition
            inputs: Optional input overrides

        Returns:
            Remote task ID

        Raises:
            Exception: If submission fails
        """
        if not self._session:
            await self.connect()

        # Prepare request data
        request_data = {
            'workflow': workflow,
            'delete_queue': True  # Clear any existing queue
        }

        if inputs:
            request_data['inputs'] = inputs

        try:
            async with self._session.post(
                f"{self.url}/workflow",
                json=request_data
            ) as response:

                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Workflow submission failed: HTTP {response.status} - {error_text}")

                result = await response.json()

                if 'task_id' not in result:
                    raise Exception(f"Invalid response format: {result}")

                task_id = result['task_id']
                logger.info(f"Submitted workflow to remote node, task ID: {task_id}")
                return task_id

        except aiohttp.ClientError as e:
            raise Exception(f"Network error during workflow submission: {e}")
        except asyncio.TimeoutError:
            raise Exception("Timeout during workflow submission")

    async def poll_task_status(self, task_id: str) -> TaskStatus:
        """
        Poll the status of a remote task.

        Args:
            task_id: Remote task ID

        Returns:
            Current task status

        Raises:
            Exception: If status check fails
        """
        if not self._session:
            await self.connect()

        try:
            async with self._session.get(
                f"{self.url}/task/{task_id}/status"
            ) as response:

                if response.status == 404:
                    return TaskStatus.NOT_FOUND
                elif response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Status check failed: HTTP {response.status} - {error_text}")

                result = await response.json()

                if 'status' not in result:
                    raise Exception(f"Invalid status response format: {result}")

                status_str = result['status'].upper()
                try:
                    return TaskStatus[status_str]
                except KeyError:
                    logger.warning(f"Unknown task status: {status_str}")
                    return TaskStatus.UNKNOWN

        except aiohttp.ClientError as e:
            raise Exception(f"Network error during status check: {e}")
        except asyncio.TimeoutError:
            raise Exception("Timeout during status check")

    async def wait_for_completion(self,
                                task_id: str,
                                poll_interval: float = 2.0,
                                timeout: Optional[float] = None) -> TaskStatus:
        """
        Wait for a task to complete.

        Args:
            task_id: Remote task ID
            poll_interval: How often to poll status (seconds)
            timeout: Maximum time to wait (seconds)

        Returns:
            Final task status

        Raises:
            Exception: If waiting fails or times out
        """
        start_time = time.time()

        while True:
            status = await self.poll_task_status(task_id)

            if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return status

            if timeout and (time.time() - start_time) > timeout:
                raise Exception(f"Task {task_id} timed out after {timeout} seconds")

            await asyncio.sleep(poll_interval)

    async def fetch_result(self, task_id: str) -> TaskResult:
        """
        Fetch the result of a completed task.

        Args:
            task_id: Remote task ID

        Returns:
            Task result

        Raises:
            Exception: If result fetch fails
        """
        if not self._session:
            await self.connect()

        try:
            async with self._session.get(
                f"{self.url}/task/{task_id}/result"
            ) as response:

                if response.status == 404:
                    raise Exception(f"Task {task_id} not found")
                elif response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Result fetch failed: HTTP {response.status} - {error_text}")

                result_data = await response.json()

                # Parse result
                result = TaskResult(
                    task_id=task_id,
                    status=TaskStatus.COMPLETED,
                    outputs=result_data.get('outputs', {}),
                    images=result_data.get('images', []),
                    metadata=result_data.get('metadata', {}),
                    completed_at=datetime.now()
                )

                logger.info(f"Fetched result for task {task_id}")
                return result

        except aiohttp.ClientError as e:
            raise Exception(f"Network error during result fetch: {e}")
        except asyncio.TimeoutError:
            raise Exception("Timeout during result fetch")

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.

        Args:
            task_id: Remote task ID

        Returns:
            True if cancelled successfully

        Raises:
            Exception: If cancellation fails
        """
        if not self._session:
            await self.connect()

        try:
            async with self._session.delete(
                f"{self.url}/task/{task_id}"
            ) as response:

                if response.status == 404:
                    return False  # Task not found
                elif response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Task cancellation failed: HTTP {response.status} - {error_text}")

                result = await response.json()
                success = result.get('cancelled', False)

                if success:
                    logger.info(f"Cancelled remote task {task_id}")
                else:
                    logger.warning(f"Failed to cancel remote task {task_id}")

                return success

        except aiohttp.ClientError as e:
            raise Exception(f"Network error during task cancellation: {e}")
        except asyncio.TimeoutError:
            raise Exception("Timeout during task cancellation")

    async def get_system_stats(self) -> Dict[str, Any]:
        """
        Get system statistics from the remote node.

        Returns:
            System statistics

        Raises:
            Exception: If stats fetch fails
        """
        if not self._session:
            await self.connect()

        try:
            async with self._session.get(
                f"{self.url}/system_stats"
            ) as response:

                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"System stats fetch failed: HTTP {response.status} - {error_text}")

                stats = await response.json()
                return stats

        except aiohttp.ClientError as e:
            raise Exception(f"Network error during system stats fetch: {e}")
        except asyncio.TimeoutError:
            raise Exception("Timeout during system stats fetch")

    async def list_tasks(self,
                        status_filter: Optional[List[TaskStatus]] = None) -> List[Dict[str, Any]]:
        """
        List tasks on the remote node.

        Args:
            status_filter: Optional list of statuses to filter by

        Returns:
            List of task information

        Raises:
            Exception: If task listing fails
        """
        if not self._session:
            await self.connect()

        params = {}
        if status_filter:
            params['status'] = ','.join(s.value for s in status_filter)

        try:
            async with self._session.get(
                f"{self.url}/tasks",
                params=params
            ) as response:

                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Task listing failed: HTTP {response.status} - {error_text}")

                tasks = await response.json()
                return tasks.get('tasks', [])

        except aiohttp.ClientError as e:
            raise Exception(f"Network error during task listing: {e}")
        except asyncio.TimeoutError:
            raise Exception("Timeout during task listing")

    async def upload_file(self,
                         file_path: str,
                         remote_path: Optional[str] = None) -> str:
        """
        Upload a file to the remote node.

        Args:
            file_path: Local file path
            remote_path: Optional remote path

        Returns:
            Remote file reference

        Raises:
            Exception: If upload fails
        """
        if not self._session:
            await self.connect()

        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()

            filename = remote_path or file_path.split('/')[-1]

            data = aiohttp.FormData()
            data.add_field('file', file_data, filename=filename)

            async with self._session.post(
                f"{self.url}/upload",
                data=data
            ) as response:

                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"File upload failed: HTTP {response.status} - {error_text}")

                result = await response.json()
                file_ref = result.get('file_ref')

                if not file_ref:
                    raise Exception(f"Invalid upload response: {result}")

                logger.info(f"Uploaded file {file_path} to remote node")
                return file_ref

        except (IOError, OSError) as e:
            raise Exception(f"File read error: {e}")
        except aiohttp.ClientError as e:
            raise Exception(f"Network error during file upload: {e}")
        except asyncio.TimeoutError:
            raise Exception("Timeout during file upload")