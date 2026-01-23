"""
HTTP-based Remote Storage Provider.

Provides sync operations using HTTP/HTTPS endpoints for cloud storage.
"""

import logging
import aiohttp
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, BinaryIO, Union
from datetime import datetime
import asyncio
from urllib.parse import urljoin, urlparse

from .provider import SyncProvider, SyncItem, SyncResult

logger = logging.getLogger(__name__)


class HttpSyncProvider(SyncProvider):
    """
    HTTP/HTTPS-based sync provider.

    Uses HTTP REST API endpoints for cloud storage operations.
    Supports authentication via API keys or tokens.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the HTTP sync provider.

        Args:
            config: Configuration containing:
                - base_url: Base URL for the HTTP API
                - api_key: Optional API key for authentication
                - auth_token: Optional auth token for authentication
                - timeout: Request timeout in seconds (default: 30)
                - retries: Number of retries for failed requests (default: 3)
                - headers: Additional HTTP headers
        """
        super().__init__(config)
        self.base_url = config.get('base_url', '').rstrip('/')
        self.api_key = config.get('api_key')
        self.auth_token = config.get('auth_token')
        self.timeout = config.get('timeout', 30)
        self.retries = config.get('retries', 3)
        self.custom_headers = config.get('headers', {})

        self._session: Optional[aiohttp.ClientSession] = None
        self._auth_headers = self._build_auth_headers()

    def _build_auth_headers(self) -> Dict[str, str]:
        """Build authentication headers."""
        headers = dict(self.custom_headers)

        if self.api_key:
            headers['X-API-Key'] = self.api_key
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'

        return headers

    async def connect(self) -> bool:
        """Establish HTTP connection."""
        try:
            if not self.base_url:
                logger.error("Base URL not configured")
                return False

            # Validate URL
            parsed = urlparse(self.base_url)
            if not parsed.scheme or not parsed.netloc:
                logger.error(f"Invalid base URL: {self.base_url}")
                return False

            # Create session
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers=self._auth_headers
            )

            # Test connection with a simple ping
            test_url = urljoin(self.base_url, '/ping')
            async with self._session.get(test_url) as response:
                if response.status not in [200, 404]:  # 404 is ok if ping endpoint doesn't exist
                    logger.error(f"Connection test failed with status {response.status}")
                    return False

            self._connected = True
            logger.info(f"Connected to HTTP sync provider: {self.base_url}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to HTTP provider: {e}")
            return False

    async def disconnect(self):
        """Close HTTP connection."""
        if self._session:
            await self._session.close()
            self._session = None
        self._connected = False
        logger.info("Disconnected from HTTP sync provider")

    async def is_connected(self) -> bool:
        """Check if connected to HTTP provider."""
        return self._connected and self._session is not None

    async def _make_request(self,
                           method: str,
                           endpoint: str,
                           **kwargs) -> Optional[aiohttp.ClientResponse]:
        """
        Make an HTTP request with retry logic.

        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request parameters

        Returns:
            Response object or None if failed
        """
        if not self._session:
            logger.error("Not connected to HTTP provider")
            return None

        url = urljoin(self.base_url, endpoint)

        for attempt in range(self.retries + 1):
            try:
                async with self._session.request(method, url, **kwargs) as response:
                    if response.status < 500:  # Don't retry client errors
                        return response
                    elif attempt < self.retries:
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {wait_time}s")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"Request failed after {self.retries + 1} attempts")
                        return response
            except Exception as e:
                if attempt < self.retries:
                    wait_time = 2 ** attempt
                    logger.warning(f"Request error (attempt {attempt + 1}): {e}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Request failed after {self.retries + 1} attempts: {e}")
                    return None

        return None

    async def upload_file(self,
                         local_path: Union[str, Path],
                         remote_path: str,
                         metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Upload a file via HTTP.

        Args:
            local_path: Local file path
            remote_path: Remote storage path
            metadata: Optional metadata

        Returns:
            True if upload successful
        """
        try:
            local_file = Path(local_path)
            if not local_file.exists():
                logger.error(f"Local file does not exist: {local_file}")
                return False

            # Prepare multipart data
            data = aiohttp.FormData()
            data.add_field('file',
                          open(local_file, 'rb'),
                          filename=local_file.name,
                          content_type='application/octet-stream')

            if metadata:
                data.add_field('metadata', json.dumps(metadata))

            response = await self._make_request('POST', f'/files/{remote_path}', data=data)

            if response and response.status in [200, 201]:
                logger.debug(f"Uploaded file: {local_file} -> {remote_path}")
                return True
            else:
                status = response.status if response else 'unknown'
                logger.error(f"Upload failed with status {status}")
                return False

        except Exception as e:
            logger.error(f"Failed to upload file {local_path}: {e}")
            return False

    async def download_file(self,
                           remote_path: str,
                           local_path: Union[str, Path]) -> bool:
        """
        Download a file via HTTP.

        Args:
            remote_path: Remote storage path
            local_path: Local file path

        Returns:
            True if download successful
        """
        try:
            response = await self._make_request('GET', f'/files/{remote_path}')

            if not response or response.status != 200:
                status = response.status if response else 'unknown'
                logger.error(f"Download failed with status {status}")
                return False

            local_file = Path(local_path)
            local_file.parent.mkdir(parents=True, exist_ok=True)

            with open(local_file, 'wb') as f:
                async for chunk in response.content.iter_chunked(8192):
                    f.write(chunk)

            logger.debug(f"Downloaded file: {remote_path} -> {local_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to download file {remote_path}: {e}")
            return False

    async def delete_file(self, remote_path: str) -> bool:
        """
        Delete a file via HTTP.

        Args:
            remote_path: Remote storage path

        Returns:
            True if deletion successful
        """
        try:
            response = await self._make_request('DELETE', f'/files/{remote_path}')

            if response and response.status in [200, 204]:
                logger.debug(f"Deleted file: {remote_path}")
                return True
            else:
                status = response.status if response else 'unknown'
                logger.error(f"Delete failed with status {status}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete file {remote_path}: {e}")
            return False

    async def list_files(self,
                        remote_path: str = "",
                        recursive: bool = False) -> List[SyncItem]:
        """
        List files via HTTP.

        Args:
            remote_path: Remote path to list (empty for root)
            recursive: Whether to list recursively

        Returns:
            List of sync items
        """
        try:
            params = {}
            if recursive:
                params['recursive'] = 'true'

            endpoint = f'/files/{remote_path}' if remote_path else '/files'
            response = await self._make_request('GET', endpoint, params=params)

            if not response or response.status != 200:
                status = response.status if response else 'unknown'
                logger.error(f"List files failed with status {status}")
                return []

            data = await response.json()

            items = []
            for item_data in data.get('files', []):
                try:
                    # Parse timestamp
                    modified_time = datetime.fromisoformat(item_data['modified_time'].replace('Z', '+00:00'))

                    item = SyncItem(
                        path=item_data['path'],
                        size=item_data.get('size', 0),
                        modified_time=modified_time,
                        is_directory=item_data.get('is_directory', False),
                        metadata=item_data.get('metadata')
                    )
                    items.append(item)

                except Exception as e:
                    logger.warning(f"Error parsing file item: {e}")
                    continue

            return items

        except Exception as e:
            logger.error(f"Failed to list files in {remote_path}: {e}")
            return []

    async def get_file_info(self, remote_path: str) -> Optional[SyncItem]:
        """
        Get file information via HTTP.

        Args:
            remote_path: Remote file path

        Returns:
            File information or None if not found
        """
        try:
            response = await self._make_request('GET', f'/files/{remote_path}/info')

            if not response:
                return None

            if response.status == 404:
                return None
            elif response.status != 200:
                logger.error(f"Get file info failed with status {response.status}")
                return None

            data = await response.json()

            # Parse timestamp
            modified_time = datetime.fromisoformat(data['modified_time'].replace('Z', '+00:00'))

            return SyncItem(
                path=data['path'],
                size=data.get('size', 0),
                modified_time=modified_time,
                is_directory=data.get('is_directory', False),
                metadata=data.get('metadata')
            )

        except Exception as e:
            logger.error(f"Failed to get file info for {remote_path}: {e}")
            return None

    async def create_directory(self, remote_path: str) -> bool:
        """
        Create a directory via HTTP.

        Args:
            remote_path: Remote directory path

        Returns:
            True if creation successful
        """
        try:
            response = await self._make_request('POST', f'/directories/{remote_path}')

            if response and response.status in [200, 201]:
                logger.debug(f"Created directory: {remote_path}")
                return True
            else:
                status = response.status if response else 'unknown'
                logger.error(f"Create directory failed with status {status}")
                return False

        except Exception as e:
            logger.error(f"Failed to create directory {remote_path}: {e}")
            return False

    async def delete_directory(self, remote_path: str) -> bool:
        """
        Delete a directory via HTTP.

        Args:
            remote_path: Remote directory path

        Returns:
            True if deletion successful
        """
        try:
            response = await self._make_request('DELETE', f'/directories/{remote_path}')

            if response and response.status in [200, 204]:
                logger.debug(f"Deleted directory: {remote_path}")
                return True
            else:
                status = response.status if response else 'unknown'
                logger.error(f"Delete directory failed with status {status}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete directory {remote_path}: {e}")
            return False

    async def get_server_info(self) -> Optional[Dict[str, Any]]:
        """
        Get server information.

        Returns:
            Server information or None if failed
        """
        try:
            response = await self._make_request('GET', '/info')

            if response and response.status == 200:
                return await response.json()
            else:
                return None

        except Exception as e:
            logger.error(f"Failed to get server info: {e}")
            return None