# mobile_bridge/pull.py

"""
Mobile Asset Pull System

Handles pulling assets, workflows, and data from mobile devices to Comfy Gimpy Studio.
"""

import json
import logging
import time
import threading
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
import base64
import hashlib
import tempfile

from ..shared.config import ConfigManager
from ..sync_manager import SyncManager

logger = logging.getLogger(__name__)

class MobilePull:
    """Mobile asset pull system."""

    def __init__(self, sync_manager: SyncManager):
        self.sync_manager = sync_manager
        self.config_manager = ConfigManager()
        self.pull_requests: Dict[str, Dict[str, Any]] = {}
        self.active_pulls: Dict[str, Dict[str, Any]] = {}
        self.pull_callbacks: Dict[str, Callable] = {}

        # Pull settings
        self.pull_timeout = 300  # 5 minutes
        self.max_file_size = 100 * 1024 * 1024  # 100MB limit

        # Temporary storage for incoming files
        self.temp_dir = Path(tempfile.gettempdir()) / 'comfy_gimpy_mobile_pulls'
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def initialize(self):
        """Initialize the pull system."""
        logger.info("Initializing mobile pull system")

        # Clean up old temp files
        self._cleanup_temp_files()

    def shutdown(self):
        """Shutdown the pull system."""
        self._cleanup_temp_files()
        logger.info("Mobile pull system shut down")

    def request_asset_pull(self, device_id: str, asset_type: str,
                          asset_path: Optional[str] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> str:
        """Request to pull an asset from a mobile device."""
        pull_id = f"pull_{device_id}_{int(time.time())}_{hash(asset_type) % 10000}"

        pull_request = {
            'pull_id': pull_id,
            'device_id': device_id,
            'type': 'asset',
            'asset_type': asset_type,
            'asset_path': asset_path,
            'metadata': metadata or {},
            'status': 'requested',
            'created_at': time.time(),
            'timeout_at': time.time() + self.pull_timeout
        }

        self.pull_requests[pull_id] = pull_request
        self.active_pulls[pull_id] = pull_request

        # Send pull request to device
        self._send_pull_request_to_device(pull_request)

        logger.info(f"Requested asset pull: {pull_id} ({asset_type}) from {device_id}")
        return pull_id

    def request_workflow_pull(self, device_id: str, workflow_name: Optional[str] = None) -> str:
        """Request to pull a workflow from a mobile device."""
        pull_id = f"pull_{device_id}_{int(time.time())}_workflow"

        pull_request = {
            'pull_id': pull_id,
            'device_id': device_id,
            'type': 'workflow',
            'workflow_name': workflow_name,
            'status': 'requested',
            'created_at': time.time(),
            'timeout_at': time.time() + self.pull_timeout
        }

        self.pull_requests[pull_id] = pull_request
        self.active_pulls[pull_id] = pull_request

        # Send pull request to device
        self._send_pull_request_to_device(pull_request)

        logger.info(f"Requested workflow pull: {pull_id} from {device_id}")
        return pull_id

    def request_device_info_pull(self, device_id: str) -> str:
        """Request device information from a mobile device."""
        pull_id = f"pull_{device_id}_{int(time.time())}_device_info"

        pull_request = {
            'pull_id': pull_id,
            'device_id': device_id,
            'type': 'device_info',
            'status': 'requested',
            'created_at': time.time(),
            'timeout_at': time.time() + self.pull_timeout
        }

        self.pull_requests[pull_id] = pull_request
        self.active_pulls[pull_id] = pull_request

        # Send pull request to device
        self._send_pull_request_to_device(pull_request)

        logger.info(f"Requested device info pull: {pull_id} from {device_id}")
        return pull_id

    def handle_incoming_data(self, device_id: str, data: Dict[str, Any]):
        """Handle incoming data from a mobile device."""
        data_type = data.get('type')

        if data_type == 'pull_response':
            self._handle_pull_response(device_id, data)
        elif data_type == 'asset_data':
            self._handle_asset_data(device_id, data)
        elif data_type == 'workflow_data':
            self._handle_workflow_data(device_id, data)
        elif data_type == 'device_info_data':
            self._handle_device_info_data(device_id, data)

    def get_pull_status(self, pull_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a pull operation."""
        return self.active_pulls.get(pull_id)

    def cancel_pull(self, pull_id: str) -> bool:
        """Cancel an active pull operation."""
        if pull_id not in self.active_pulls:
            return False

        pull_request = self.active_pulls[pull_id]
        if pull_request['status'] in ['completed', 'failed']:
            return False

        pull_request['status'] = 'cancelled'
        pull_request['cancelled_at'] = time.time()

        logger.info(f"Cancelled pull: {pull_id}")
        return True

    def register_pull_callback(self, pull_type: str, callback: Callable):
        """Register a callback for pull completion."""
        self.pull_callbacks[pull_type] = callback

    def _send_pull_request_to_device(self, pull_request: Dict[str, Any]):
        """Send a pull request to the mobile device."""
        device_id = pull_request['device_id']

        request_data = {
            'type': 'pull_request',
            'pull_id': pull_request['pull_id'],
            'request_type': pull_request['type'],
            'asset_type': pull_request.get('asset_type'),
            'asset_path': pull_request.get('asset_path'),
            'workflow_name': pull_request.get('workflow_name'),
            'metadata': pull_request.get('metadata', {})
        }

        # Send via sync manager
        self.sync_manager.notify_mobile_device(device_id, request_data)

    def _handle_pull_response(self, device_id: str, data: Dict[str, Any]):
        """Handle a pull response from a device."""
        pull_id = data.get('pull_id')
        accepted = data.get('accepted', False)

        if pull_id not in self.active_pulls:
            logger.warning(f"Received response for unknown pull: {pull_id}")
            return

        pull_request = self.active_pulls[pull_id]

        if accepted:
            pull_request['status'] = 'accepted'
            pull_request['accepted_at'] = time.time()
            logger.info(f"Pull request accepted: {pull_id}")
        else:
            pull_request['status'] = 'rejected'
            pull_request['rejected_at'] = time.time()
            pull_request['rejection_reason'] = data.get('reason', 'Unknown')
            logger.info(f"Pull request rejected: {pull_id}")

    def _handle_asset_data(self, device_id: str, data: Dict[str, Any]):
        """Handle incoming asset data from a device."""
        pull_id = data.get('pull_id')
        asset_type = data.get('asset_type')
        filename = data.get('filename')
        asset_data = data.get('data')  # base64 encoded
        file_hash = data.get('hash')

        if not pull_id or pull_id not in self.active_pulls:
            logger.warning(f"Received asset data for unknown pull: {pull_id}")
            return

        pull_request = self.active_pulls[pull_id]

        try:
            # Decode asset data
            if asset_data:
                decoded_data = base64.b64decode(asset_data)

                # Verify file size limit
                if len(decoded_data) > self.max_file_size:
                    raise ValueError(f"File too large: {len(decoded_data)} bytes")

                # Verify hash if provided
                if file_hash:
                    calculated_hash = hashlib.sha256(decoded_data).hexdigest()
                    if calculated_hash != file_hash:
                        raise ValueError("File hash mismatch")

                # Save to temporary file
                temp_file = self.temp_dir / f"{pull_id}_{filename}"
                with open(temp_file, 'wb') as f:
                    f.write(decoded_data)

                # Move to final location based on asset type
                final_path = self._get_asset_destination(asset_type, filename)
                final_path.parent.mkdir(parents=True, exist_ok=True)
                temp_file.rename(final_path)

                pull_request['status'] = 'completed'
                pull_request['completed_at'] = time.time()
                pull_request['final_path'] = str(final_path)
                pull_request['file_size'] = len(decoded_data)

                logger.info(f"Asset pull completed: {pull_id} -> {final_path}")

                # Call completion callback
                if 'asset' in self.pull_callbacks:
                    try:
                        self.pull_callbacks['asset'](pull_request)
                    except Exception as e:
                        logger.error(f"Asset pull callback error: {e}")

            else:
                # Handle chunked transfer
                self._handle_asset_chunk(device_id, data)

        except Exception as e:
            logger.error(f"Asset pull error for {pull_id}: {e}")
            pull_request['status'] = 'failed'
            pull_request['error'] = str(e)
            pull_request['failed_at'] = time.time()

    def _handle_asset_chunk(self, device_id: str, data: Dict[str, Any]):
        """Handle a chunk of asset data."""
        pull_id = data.get('pull_id')
        filename = data.get('filename')
        chunk_num = data.get('chunk_num')
        chunk_data = data.get('data')  # base64 encoded
        is_last = data.get('is_last', False)

        if not pull_id or pull_id not in self.active_pulls:
            logger.warning(f"Received chunk for unknown pull: {pull_id}")
            return

        pull_request = self.active_pulls[pull_id]

        # Initialize chunk tracking if first chunk
        if 'chunks' not in pull_request:
            pull_request['chunks'] = {}
            pull_request['temp_file'] = self.temp_dir / f"{pull_id}_{filename}"

        # Save chunk
        decoded_chunk = base64.b64decode(chunk_data)
        pull_request['chunks'][chunk_num] = decoded_chunk

        if is_last:
            # Assemble complete file
            temp_file = pull_request['temp_file']
            with open(temp_file, 'wb') as f:
                for i in sorted(pull_request['chunks'].keys()):
                    f.write(pull_request['chunks'][i])

            # Move to final location
            asset_type = pull_request.get('asset_type', 'unknown')
            final_path = self._get_asset_destination(asset_type, filename)
            final_path.parent.mkdir(parents=True, exist_ok=True)
            temp_file.rename(final_path)

            # Calculate file size
            file_size = sum(len(chunk) for chunk in pull_request['chunks'].values())

            pull_request['status'] = 'completed'
            pull_request['completed_at'] = time.time()
            pull_request['final_path'] = str(final_path)
            pull_request['file_size'] = file_size

            # Clean up
            del pull_request['chunks']
            del pull_request['temp_file']

            logger.info(f"Chunked asset pull completed: {pull_id} -> {final_path}")

            # Call completion callback
            if 'asset' in self.pull_callbacks:
                try:
                    self.pull_callbacks['asset'](pull_request)
                except Exception as e:
                    logger.error(f"Asset pull callback error: {e}")

    def _handle_workflow_data(self, device_id: str, data: Dict[str, Any]):
        """Handle incoming workflow data from a device."""
        pull_id = data.get('pull_id')
        workflow_name = data.get('workflow_name')
        workflow_data = data.get('workflow_data')

        if not pull_id or pull_id not in self.active_pulls:
            logger.warning(f"Received workflow data for unknown pull: {pull_id}")
            return

        pull_request = self.active_pulls[pull_id]

        try:
            # Save workflow data
            workflow_path = self._get_workflow_destination(workflow_name)
            workflow_path.parent.mkdir(parents=True, exist_ok=True)

            with open(workflow_path, 'w') as f:
                json.dump(workflow_data, f, indent=2)

            pull_request['status'] = 'completed'
            pull_request['completed_at'] = time.time()
            pull_request['final_path'] = str(workflow_path)

            logger.info(f"Workflow pull completed: {pull_id} -> {workflow_path}")

            # Call completion callback
            if 'workflow' in self.pull_callbacks:
                try:
                    self.pull_callbacks['workflow'](pull_request)
                except Exception as e:
                    logger.error(f"Workflow pull callback error: {e}")

        except Exception as e:
            logger.error(f"Workflow pull error for {pull_id}: {e}")
            pull_request['status'] = 'failed'
            pull_request['error'] = str(e)
            pull_request['failed_at'] = time.time()

    def _handle_device_info_data(self, device_id: str, data: Dict[str, Any]):
        """Handle incoming device info data."""
        pull_id = data.get('pull_id')
        device_info = data.get('device_info')

        if not pull_id or pull_id not in self.active_pulls:
            logger.warning(f"Received device info for unknown pull: {pull_id}")
            return

        pull_request = self.active_pulls[pull_id]

        try:
            pull_request['status'] = 'completed'
            pull_request['completed_at'] = time.time()
            pull_request['device_info'] = device_info

            logger.info(f"Device info pull completed: {pull_id}")

            # Call completion callback
            if 'device_info' in self.pull_callbacks:
                try:
                    self.pull_callbacks['device_info'](pull_request)
                except Exception as e:
                    logger.error(f"Device info pull callback error: {e}")

        except Exception as e:
            logger.error(f"Device info pull error for {pull_id}: {e}")
            pull_request['status'] = 'failed'
            pull_request['error'] = str(e)
            pull_request['failed_at'] = time.time()

    def _get_asset_destination(self, asset_type: str, filename: str) -> Path:
        """Get the destination path for an asset."""
        base_dir = Path(self.config_manager.get('paths.assets', 'assets'))

        if asset_type == 'image':
            return base_dir / 'images' / filename
        elif asset_type == 'video':
            return base_dir / 'videos' / filename
        elif asset_type == 'audio':
            return base_dir / 'audio' / filename
        elif asset_type == 'document':
            return base_dir / 'documents' / filename
        else:
            return base_dir / 'misc' / filename

    def _get_workflow_destination(self, workflow_name: str) -> Path:
        """Get the destination path for a workflow."""
        workflows_dir = Path(self.config_manager.get('paths.workflows', 'workflows'))
        return workflows_dir / f"{workflow_name}.json"

    def _cleanup_temp_files(self):
        """Clean up temporary files older than 1 hour."""
        try:
            cutoff_time = time.time() - 3600  # 1 hour ago

            for temp_file in self.temp_dir.glob('*'):
                if temp_file.stat().st_mtime < cutoff_time:
                    temp_file.unlink()
                    logger.debug(f"Cleaned up temp file: {temp_file}")

        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")