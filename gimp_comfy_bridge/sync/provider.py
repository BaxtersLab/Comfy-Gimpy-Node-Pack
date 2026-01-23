"""
Cloud Storage Provider Interface.

Abstract base class for cloud storage providers supporting sync operations.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, BinaryIO
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SyncItem:
    """Represents an item in sync storage."""
    path: str
    size: int
    modified_time: datetime
    is_directory: bool
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SyncResult:
    """Result of a sync operation."""
    success: bool
    items_synced: int = 0
    items_skipped: int = 0
    items_failed: int = 0
    errors: List[str] = None
    duration: float = 0.0

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class SyncProvider(ABC):
    """
    Abstract base class for cloud storage providers.

    Provides interface for uploading, downloading, listing, and managing
    files in cloud storage for sync operations.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the sync provider.

        Args:
            config: Provider-specific configuration
        """
        self.config = config
        self._connected = False

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to the storage provider.

        Returns:
            True if connection successful
        """
        pass

    @abstractmethod
    async def disconnect(self):
        """Close connection to the storage provider."""
        pass

    @abstractmethod
    async def is_connected(self) -> bool:
        """
        Check if provider is currently connected.

        Returns:
            True if connected
        """
        pass

    @abstractmethod
    async def upload_file(self,
                         local_path: Union[str, Path],
                         remote_path: str,
                         metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Upload a file to cloud storage.

        Args:
            local_path: Local file path
            remote_path: Remote storage path
            metadata: Optional metadata to store with file

        Returns:
            True if upload successful
        """
        pass

    @abstractmethod
    async def download_file(self,
                           remote_path: str,
                           local_path: Union[str, Path]) -> bool:
        """
        Download a file from cloud storage.

        Args:
            remote_path: Remote storage path
            local_path: Local file path

        Returns:
            True if download successful
        """
        pass

    @abstractmethod
    async def delete_file(self, remote_path: str) -> bool:
        """
        Delete a file from cloud storage.

        Args:
            remote_path: Remote storage path

        Returns:
            True if deletion successful
        """
        pass

    @abstractmethod
    async def list_files(self,
                        remote_path: str = "",
                        recursive: bool = False) -> List[SyncItem]:
        """
        List files in cloud storage.

        Args:
            remote_path: Remote path to list (empty for root)
            recursive: Whether to list recursively

        Returns:
            List of sync items
        """
        pass

    @abstractmethod
    async def get_file_info(self, remote_path: str) -> Optional[SyncItem]:
        """
        Get information about a file in cloud storage.

        Args:
            remote_path: Remote file path

        Returns:
            File information or None if not found
        """
        pass

    @abstractmethod
    async def create_directory(self, remote_path: str) -> bool:
        """
        Create a directory in cloud storage.

        Args:
            remote_path: Remote directory path

        Returns:
            True if creation successful
        """
        pass

    @abstractmethod
    async def delete_directory(self, remote_path: str) -> bool:
        """
        Delete a directory from cloud storage.

        Args:
            remote_path: Remote directory path

        Returns:
            True if deletion successful
        """
        pass

    async def sync_directory(self,
                           local_dir: Union[str, Path],
                           remote_dir: str,
                           direction: str = "bidirectional",
                           exclude_patterns: Optional[List[str]] = None) -> SyncResult:
        """
        Sync a directory with cloud storage.

        Args:
            local_dir: Local directory path
            remote_dir: Remote directory path
            direction: Sync direction ("upload", "download", "bidirectional")
            exclude_patterns: File patterns to exclude

        Returns:
            Sync operation result
        """
        start_time = datetime.now().timestamp()

        try:
            result = SyncResult(success=True)

            if direction in ["upload", "bidirectional"]:
                upload_result = await self._sync_upload(local_dir, remote_dir, exclude_patterns)
                result.items_synced += upload_result.items_synced
                result.items_skipped += upload_result.items_skipped
                result.items_failed += upload_result.items_failed
                result.errors.extend(upload_result.errors)

            if direction in ["download", "bidirectional"]:
                download_result = await self._sync_download(local_dir, remote_dir, exclude_patterns)
                result.items_synced += download_result.items_synced
                result.items_skipped += download_result.items_skipped
                result.items_failed += download_result.items_failed
                result.errors.extend(download_result.errors)

            result.success = len(result.errors) == 0
            result.duration = datetime.now().timestamp() - start_time

            return result

        except Exception as e:
            logger.error(f"Directory sync failed: {e}")
            return SyncResult(
                success=False,
                errors=[str(e)],
                duration=datetime.now().timestamp() - start_time
            )

    async def _sync_upload(self,
                          local_dir: Union[str, Path],
                          remote_dir: str,
                          exclude_patterns: Optional[List[str]] = None) -> SyncResult:
        """
        Upload local directory changes to remote.

        Args:
            local_dir: Local directory
            remote_dir: Remote directory
            exclude_patterns: Patterns to exclude

        Returns:
            Upload sync result
        """
        result = SyncResult(success=True)
        local_path = Path(local_dir)

        # Walk local directory
        for local_file in local_path.rglob('*'):
            if local_file.is_file():
                # Check exclude patterns
                if exclude_patterns and self._matches_pattern(str(local_file), exclude_patterns):
                    continue

                # Calculate relative path
                relative_path = local_file.relative_to(local_path)
                remote_path = f"{remote_dir}/{relative_path}"

                try:
                    # Check if remote file exists and is different
                    remote_info = await self.get_file_info(remote_path)

                    if remote_info is None or local_file.stat().st_mtime > remote_info.modified_time.timestamp():
                        # Upload file
                        success = await self.upload_file(local_file, remote_path)
                        if success:
                            result.items_synced += 1
                        else:
                            result.items_failed += 1
                            result.errors.append(f"Failed to upload {local_file}")
                    else:
                        result.items_skipped += 1

                except Exception as e:
                    result.items_failed += 1
                    result.errors.append(f"Error processing {local_file}: {e}")

        return result

    async def _sync_download(self,
                           local_dir: Union[str, Path],
                           remote_dir: str,
                           exclude_patterns: Optional[List[str]] = None) -> SyncResult:
        """
        Download remote directory changes to local.

        Args:
            local_dir: Local directory
            remote_dir: Remote directory
            exclude_patterns: Patterns to exclude

        Returns:
            Download sync result
        """
        result = SyncResult(success=True)
        local_path = Path(local_dir)

        # List remote files
        try:
            remote_files = await self.list_files(remote_dir, recursive=True)
        except Exception as e:
            return SyncResult(success=False, errors=[f"Failed to list remote files: {e}"])

        for remote_file in remote_files:
            if remote_file.is_directory:
                continue

            # Check exclude patterns
            if exclude_patterns and self._matches_pattern(remote_file.path, exclude_patterns):
                continue

            # Calculate local path
            relative_path = remote_file.path.replace(remote_dir, '').lstrip('/')
            local_file = local_path / relative_path

            try:
                # Check if local file exists and is different
                if local_file.exists():
                    local_mtime = local_file.stat().st_mtime
                    if local_mtime >= remote_file.modified_time.timestamp():
                        result.items_skipped += 1
                        continue

                # Ensure local directory exists
                local_file.parent.mkdir(parents=True, exist_ok=True)

                # Download file
                success = await self.download_file(remote_file.path, local_file)
                if success:
                    result.items_synced += 1
                else:
                    result.items_failed += 1
                    result.errors.append(f"Failed to download {remote_file.path}")

            except Exception as e:
                result.items_failed += 1
                result.errors.append(f"Error processing {remote_file.path}: {e}")

        return result

    def _matches_pattern(self, path: str, patterns: List[str]) -> bool:
        """
        Check if path matches any of the exclude patterns.

        Args:
            path: File path to check
            patterns: List of glob patterns

        Returns:
            True if path matches any pattern
        """
        from fnmatch import fnmatch

        for pattern in patterns:
            if fnmatch(path, pattern):
                return True
        return False

    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return self.__class__.__name__

    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get information about this provider.

        Returns:
            Provider information
        """
        return {
            'name': self.provider_name,
            'connected': self._connected,
            'config': {k: '***' if 'secret' in k.lower() or 'token' in k.lower() else v
                      for k, v in self.config.items()}
        }