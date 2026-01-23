"""
Local Filesystem Storage Provider.

Provides sync operations using local filesystem storage.
"""

import logging
import shutil
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, BinaryIO, Union
from datetime import datetime
import hashlib

from .provider import SyncProvider, SyncItem, SyncResult

logger = logging.getLogger(__name__)


class LocalSyncProvider(SyncProvider):
    """
    Local filesystem-based sync provider.

    Uses a local directory as the sync storage backend.
    Useful for local backups or network shares.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the local sync provider.

        Args:
            config: Configuration containing:
                - base_path: Base directory path for storage
                - create_if_missing: Whether to create base path if it doesn't exist
        """
        super().__init__(config)
        self.base_path = Path(config.get('base_path', './sync_storage'))
        self.create_if_missing = config.get('create_if_missing', True)

        if self.create_if_missing and not self.base_path.exists():
            self.base_path.mkdir(parents=True, exist_ok=True)

    async def connect(self) -> bool:
        """Establish connection to local storage."""
        try:
            if not self.base_path.exists():
                if self.create_if_missing:
                    self.base_path.mkdir(parents=True, exist_ok=True)
                else:
                    logger.error(f"Base path does not exist: {self.base_path}")
                    return False

            # Test write access
            test_file = self.base_path / '.sync_test'
            test_file.write_text('test')
            test_file.unlink()

            self._connected = True
            logger.info(f"Connected to local sync storage: {self.base_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to local storage: {e}")
            return False

    async def disconnect(self):
        """Close connection to local storage."""
        self._connected = False
        logger.info("Disconnected from local sync storage")

    async def is_connected(self) -> bool:
        """Check if connected to local storage."""
        return self._connected and self.base_path.exists()

    async def upload_file(self,
                         local_path: Union[str, Path],
                         remote_path: str,
                         metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Upload a file to local storage.

        Args:
            local_path: Local file path
            remote_path: Remote storage path
            metadata: Optional metadata (ignored for local storage)

        Returns:
            True if upload successful
        """
        try:
            local_file = Path(local_path)
            if not local_file.exists():
                logger.error(f"Local file does not exist: {local_file}")
                return False

            remote_file = self.base_path / remote_path.lstrip('/')
            remote_file.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(local_file, remote_file)

            # Store metadata if provided
            if metadata:
                meta_file = remote_file.with_suffix('.meta.json')
                import json
                meta_file.write_text(json.dumps(metadata, indent=2))

            logger.debug(f"Uploaded file: {local_file} -> {remote_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to upload file {local_path}: {e}")
            return False

    async def download_file(self,
                           remote_path: str,
                           local_path: Union[str, Path]) -> bool:
        """
        Download a file from local storage.

        Args:
            remote_path: Remote storage path
            local_path: Local file path

        Returns:
            True if download successful
        """
        try:
            remote_file = self.base_path / remote_path.lstrip('/')
            if not remote_file.exists():
                logger.error(f"Remote file does not exist: {remote_file}")
                return False

            local_file = Path(local_path)
            local_file.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(remote_file, local_file)

            logger.debug(f"Downloaded file: {remote_file} -> {local_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to download file {remote_path}: {e}")
            return False

    async def delete_file(self, remote_path: str) -> bool:
        """
        Delete a file from local storage.

        Args:
            remote_path: Remote storage path

        Returns:
            True if deletion successful
        """
        try:
            remote_file = self.base_path / remote_path.lstrip('/')
            if not remote_file.exists():
                logger.warning(f"File to delete does not exist: {remote_file}")
                return True

            remote_file.unlink()

            # Also delete metadata file if it exists
            meta_file = remote_file.with_suffix('.meta.json')
            if meta_file.exists():
                meta_file.unlink()

            logger.debug(f"Deleted file: {remote_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete file {remote_path}: {e}")
            return False

    async def list_files(self,
                        remote_path: str = "",
                        recursive: bool = False) -> List[SyncItem]:
        """
        List files in local storage.

        Args:
            remote_path: Remote path to list (empty for root)
            recursive: Whether to list recursively

        Returns:
            List of sync items
        """
        try:
            base_dir = self.base_path / remote_path.lstrip('/')
            if not base_dir.exists():
                return []

            items = []

            if recursive:
                pattern = '**/*'
            else:
                pattern = '*'

            for path in base_dir.glob(pattern):
                if path.name.startswith('.'):  # Skip hidden files
                    continue

                try:
                    stat = path.stat()
                    relative_path = path.relative_to(self.base_path)

                    # Load metadata if available
                    metadata = None
                    if path.is_file():
                        meta_file = path.with_suffix('.meta.json')
                        if meta_file.exists():
                            import json
                            try:
                                metadata = json.loads(meta_file.read_text())
                            except:
                                pass

                    item = SyncItem(
                        path=str(relative_path),
                        size=stat.st_size if path.is_file() else 0,
                        modified_time=datetime.fromtimestamp(stat.st_mtime),
                        is_directory=path.is_dir(),
                        metadata=metadata
                    )
                    items.append(item)

                except Exception as e:
                    logger.warning(f"Error processing {path}: {e}")
                    continue

            return items

        except Exception as e:
            logger.error(f"Failed to list files in {remote_path}: {e}")
            return []

    async def get_file_info(self, remote_path: str) -> Optional[SyncItem]:
        """
        Get information about a file in local storage.

        Args:
            remote_path: Remote file path

        Returns:
            File information or None if not found
        """
        try:
            remote_file = self.base_path / remote_path.lstrip('/')
            if not remote_file.exists():
                return None

            stat = remote_file.stat()

            # Load metadata if available
            metadata = None
            if remote_file.is_file():
                meta_file = remote_file.with_suffix('.meta.json')
                if meta_file.exists():
                    import json
                    try:
                        metadata = json.loads(meta_file.read_text())
                    except:
                        pass

            return SyncItem(
                path=remote_path,
                size=stat.st_size if remote_file.is_file() else 0,
                modified_time=datetime.fromtimestamp(stat.st_mtime),
                is_directory=remote_file.is_dir(),
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Failed to get file info for {remote_path}: {e}")
            return None

    async def create_directory(self, remote_path: str) -> bool:
        """
        Create a directory in local storage.

        Args:
            remote_path: Remote directory path

        Returns:
            True if creation successful
        """
        try:
            remote_dir = self.base_path / remote_path.lstrip('/')
            remote_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {remote_dir}")
            return True

        except Exception as e:
            logger.error(f"Failed to create directory {remote_path}: {e}")
            return False

    async def delete_directory(self, remote_path: str) -> bool:
        """
        Delete a directory from local storage.

        Args:
            remote_path: Remote directory path

        Returns:
            True if deletion successful
        """
        try:
            remote_dir = self.base_path / remote_path.lstrip('/')
            if not remote_dir.exists():
                logger.warning(f"Directory to delete does not exist: {remote_dir}")
                return True

            if not remote_dir.is_dir():
                logger.error(f"Path is not a directory: {remote_dir}")
                return False

            shutil.rmtree(remote_dir)
            logger.debug(f"Deleted directory: {remote_dir}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete directory {remote_path}: {e}")
            return False

    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get information about local storage.

        Returns:
            Storage information
        """
        try:
            stat = os.statvfs(self.base_path) if hasattr(os, 'statvfs') else None

            info = {
                'base_path': str(self.base_path),
                'exists': self.base_path.exists(),
                'total_space': None,
                'free_space': None,
                'used_space': None
            }

            if stat:
                info['total_space'] = stat.f_blocks * stat.f_frsize
                info['free_space'] = stat.f_available * stat.f_frsize
                info['used_space'] = info['total_space'] - info['free_space']

            return info

        except Exception as e:
            logger.error(f"Failed to get storage info: {e}")
            return {'error': str(e)}