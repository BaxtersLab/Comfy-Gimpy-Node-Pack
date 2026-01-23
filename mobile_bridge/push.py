# mobile_bridge/push.py

"""
Mobile Asset Push System

Handles pushing assets, workflows, and data from Comfy Gimpy Studio to mobile devices.
"""

import json
import logging
import time
import threading
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
import base64
import hashlib

from ..shared.config import ConfigManager
from ..sync_manager import SyncManager

logger = logging.getLogger(__name__)

class MobilePush:
    """Mobile asset push system."""

    def __init__(self, sync_manager: SyncManager):
        self.sync_manager = sync_manager
        self.config_manager = ConfigManager()
        self.push_queue: List[Dict[str, Any]] = []
        self.active_pushes: Dict[str, Dict[str, Any]] = {}
        self.push_callbacks: Dict[str, Callable] = {}

        # Push settings
        self.max_concurrent_pushes = 3
        self.push_timeout = 300  # 5 minutes
        self.chunk_size = 1024 * 1024  # 1MB chunks

        # Start push worker thread
        self.worker_thread = threading.Thread(target=self._push_worker, daemon=True)
        self.worker_thread.start()

    def initialize(self):
        """Initialize the push system."""
        logger.info("Initializing mobile push system")

    def shutdown(self):
        """Shutdown the push system."""
        logger.info("Mobile push system shut down")

    def push_asset(self, device_id: str, asset_path: str, asset_type: str,
                   metadata: Optional[Dict[str, Any]] = None) -> str:
        """Push an asset to a mobile device."""
        push_id = f"push_{device_id}_{int(time.time())}_{hash(asset_path) % 10000}"

        push_request = {
            'push_id': push_id,
            'device_id': device_id,
            'type': 'asset',
            'asset_path': asset_path,
            'asset_type': asset_type,
            'metadata': metadata or {},
            'status': 'queued',
            'created_at': time.time(),
            'priority': 1
        }

        self.push_queue.append(push_request)
        self.active_pushes[push_id] = push_request

        logger.info(f"Queued asset push: {push_id} ({asset_type}) to {device_id}")
        return push_id

    def push_workflow(self, device_id: str, workflow_data: Dict[str, Any],
                     workflow_name: str) -> str:
        """Push a workflow to a mobile device."""
        push_id = f"push_{device_id}_{int(time.time())}_workflow"

        push_request = {
            'push_id': push_id,
            'device_id': device_id,
            'type': 'workflow',
            'workflow_data': workflow_data,
            'workflow_name': workflow_name,
            'status': 'queued',
            'created_at': time.time(),
            'priority': 2
        }

        self.push_queue.append(push_request)
        self.active_pushes[push_id] = push_request

        logger.info(f"Queued workflow push: {push_id} ({workflow_name}) to {device_id}")
        return push_id

    def push_notification(self, device_id: str, title: str, message: str,
                         notification_type: str = 'info') -> str:
        """Push a notification to a mobile device."""
        push_id = f"push_{device_id}_{int(time.time())}_notification"

        push_request = {
            'push_id': push_id,
            'device_id': device_id,
            'type': 'notification',
            'title': title,
            'message': message,
            'notification_type': notification_type,
            'status': 'queued',
            'created_at': time.time(),
            'priority': 3
        }

        self.push_queue.append(push_request)
        self.active_pushes[push_id] = push_request

        logger.info(f"Queued notification push: {push_id} to {device_id}")
        return push_id

    def push_status_update(self, device_id: str, status_data: Dict[str, Any]) -> str:
        """Push a status update to a mobile device."""
        push_id = f"push_{device_id}_{int(time.time())}_status"

        push_request = {
            'push_id': push_id,
            'device_id': device_id,
            'type': 'status',
            'status_data': status_data,
            'status': 'queued',
            'created_at': time.time(),
            'priority': 4
        }

        self.push_queue.append(push_request)
        self.active_pushes[push_id] = push_request

        logger.info(f"Queued status push: {push_id} to {device_id}")
        return push_id

    def get_push_status(self, push_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a push operation."""
        return self.active_pushes.get(push_id)

    def cancel_push(self, push_id: str) -> bool:
        """Cancel a queued or active push operation."""
        if push_id not in self.active_pushes:
            return False

        push_request = self.active_pushes[push_id]
        if push_request['status'] in ['completed', 'failed']:
            return False

        push_request['status'] = 'cancelled'
        push_request['cancelled_at'] = time.time()

        logger.info(f"Cancelled push: {push_id}")
        return True

    def register_push_callback(self, push_type: str, callback: Callable):
        """Register a callback for push completion."""
        self.push_callbacks[push_type] = callback

    def _push_worker(self):
        """Background worker for processing push requests."""
        while True:
            try:
                # Sort queue by priority (higher priority first)
                self.push_queue.sort(key=lambda x: x['priority'], reverse=True)

                # Process queued pushes
                active_count = sum(1 for p in self.active_pushes.values()
                                 if p['status'] == 'processing')

                if active_count < self.max_concurrent_pushes and self.push_queue:
                    push_request = self.push_queue.pop(0)
                    threading.Thread(target=self._process_push,
                                   args=(push_request,),
                                   daemon=True).start()

                time.sleep(0.1)  # Small delay to prevent busy waiting

            except Exception as e:
                logger.error(f"Push worker error: {e}")
                time.sleep(1)

    def _process_push(self, push_request: Dict[str, Any]):
        """Process a single push request."""
        push_id = push_request['push_id']
        device_id = push_request['device_id']

        try:
            push_request['status'] = 'processing'
            push_request['started_at'] = time.time()

            logger.info(f"Processing push: {push_id}")

            if push_request['type'] == 'asset':
                self._push_asset(push_request)
            elif push_request['type'] == 'workflow':
                self._push_workflow(push_request)
            elif push_request['type'] == 'notification':
                self._push_notification(push_request)
            elif push_request['type'] == 'status':
                self._push_status(push_request)

            push_request['status'] = 'completed'
            push_request['completed_at'] = time.time()

            # Call completion callback if registered
            push_type = push_request['type']
            if push_type in self.push_callbacks:
                try:
                    self.push_callbacks[push_type](push_request)
                except Exception as e:
                    logger.error(f"Push callback error for {push_type}: {e}")

            logger.info(f"Completed push: {push_id}")

        except Exception as e:
            logger.error(f"Push processing error for {push_id}: {e}")
            push_request['status'] = 'failed'
            push_request['error'] = str(e)
            push_request['failed_at'] = time.time()

    def _push_asset(self, push_request: Dict[str, Any]):
        """Push an asset file to a mobile device."""
        asset_path = push_request['asset_path']
        asset_type = push_request['asset_type']
        device_id = push_request['device_id']

        # Read and encode asset
        asset_file = Path(asset_path)
        if not asset_file.exists():
            raise FileNotFoundError(f"Asset file not found: {asset_path}")

        # Calculate file hash for integrity checking
        file_hash = self._calculate_file_hash(asset_file)

        # Read file in chunks if large
        file_size = asset_file.stat().st_size
        if file_size > self.chunk_size:
            # Handle large files with chunking
            self._push_large_asset(push_request, asset_file, file_hash)
        else:
            # Handle small files directly
            with open(asset_file, 'rb') as f:
                asset_data = base64.b64encode(f.read()).decode()

            push_data = {
                'type': 'asset_push',
                'asset_type': asset_type,
                'filename': asset_file.name,
                'data': asset_data,
                'hash': file_hash,
                'metadata': push_request.get('metadata', {})
            }

            # Send via sync manager (this would integrate with the mobile API)
            self._send_to_device(device_id, push_data)

    def _push_large_asset(self, push_request: Dict[str, Any], asset_file: Path, file_hash: str):
        """Push a large asset file in chunks."""
        device_id = push_request['device_id']
        asset_type = push_request['asset_type']

        # Send file metadata first
        metadata_push = {
            'type': 'asset_push_start',
            'asset_type': asset_type,
            'filename': asset_file.name,
            'total_size': asset_file.stat().st_size,
            'hash': file_hash,
            'chunk_size': self.chunk_size,
            'metadata': push_request.get('metadata', {})
        }

        self._send_to_device(device_id, metadata_push)

        # Send file in chunks
        with open(asset_file, 'rb') as f:
            chunk_num = 0
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break

                chunk_data = base64.b64encode(chunk).decode()

                chunk_push = {
                    'type': 'asset_push_chunk',
                    'filename': asset_file.name,
                    'chunk_num': chunk_num,
                    'data': chunk_data
                }

                self._send_to_device(device_id, chunk_push)
                chunk_num += 1

        # Send completion signal
        completion_push = {
            'type': 'asset_push_complete',
            'filename': asset_file.name,
            'total_chunks': chunk_num
        }

        self._send_to_device(device_id, completion_push)

    def _push_workflow(self, push_request: Dict[str, Any]):
        """Push a workflow to a mobile device."""
        device_id = push_request['device_id']
        workflow_data = push_request['workflow_data']
        workflow_name = push_request['workflow_name']

        push_data = {
            'type': 'workflow_push',
            'workflow_name': workflow_name,
            'workflow_data': workflow_data
        }

        self._send_to_device(device_id, push_data)

    def _push_notification(self, push_request: Dict[str, Any]):
        """Push a notification to a mobile device."""
        device_id = push_request['device_id']

        push_data = {
            'type': 'notification',
            'title': push_request['title'],
            'message': push_request['message'],
            'notification_type': push_request['notification_type']
        }

        self._send_to_device(device_id, push_data)

    def _push_status(self, push_request: Dict[str, Any]):
        """Push a status update to a mobile device."""
        device_id = push_request['device_id']

        push_data = {
            'type': 'status_update',
            'status_data': push_request['status_data']
        }

        self._send_to_device(device_id, push_data)

    def _send_to_device(self, device_id: str, data: Dict[str, Any]):
        """Send data to a mobile device via sync manager."""
        # This would integrate with the mobile API to send push notifications
        # For now, we'll use the sync manager's notification system
        self.sync_manager.notify_mobile_device(device_id, data)

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()