# mobile_bridge/__init__.py

"""
Mobile Bridge System

Provides mobile companion functionality for Comfy Gimpy Studio including:
- Device pairing and authentication
- Asset push/pull operations
- Real-time preview streaming
- Remote control capabilities
"""

import logging
from typing import Dict, Any, Optional

from .api import MobileAPI
from .auth import MobileAuth
from .push import MobilePush
from .pull import MobilePull
from .preview import MobilePreview
from .remote_control import MobileRemoteControl

from ..sync_manager import SyncManager

logger = logging.getLogger(__name__)

class MobileBridge:
    """Main coordinator for mobile bridge functionality."""

    def __init__(self, sync_manager: SyncManager):
        self.sync_manager = sync_manager

        # Initialize components
        self.auth = MobileAuth()
        self.api = MobileAPI(self.auth, self)
        self.push = MobilePush(sync_manager)
        self.pull = MobilePull(sync_manager)
        self.preview = MobilePreview(sync_manager)
        self.remote_control = MobileRemoteControl(sync_manager)

        # Bridge state
        self.is_running = False
        self.mobile_devices: Dict[str, Dict[str, Any]] = {}

    def initialize(self):
        """Initialize the mobile bridge system."""
        logger.info("Initializing Mobile Bridge system")

        try:
            # Initialize all components
            self.auth.initialize()
            self.push.initialize()
            self.pull.initialize()
            self.preview.initialize()
            self.remote_control.initialize()

            # Set up component integrations
            self._setup_integrations()

            self.is_running = True
            logger.info("Mobile Bridge system initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Mobile Bridge: {e}")
            raise

    def shutdown(self):
        """Shutdown the mobile bridge system."""
        logger.info("Shutting down Mobile Bridge system")

        try:
            self.is_running = False

            # Shutdown components in reverse order
            self.remote_control.shutdown()
            self.preview.shutdown()
            self.pull.shutdown()
            self.push.shutdown()
            self.auth.shutdown()

            logger.info("Mobile Bridge system shut down successfully")

        except Exception as e:
            logger.error(f"Error during Mobile Bridge shutdown: {e}")

    def register_mobile_device(self, device_id: str, device_info: Dict[str, Any]) -> str:
        """Register a new mobile device."""
        auth_token = self.auth.register_device(device_id, device_info)
        self.mobile_devices[device_id] = {
            'device_id': device_id,
            'info': device_info,
            'registered_at': self.auth.devices[device_id]['registered_at'],
            'status': 'registered'
        }

        logger.info(f"Registered mobile device: {device_id}")
        return auth_token

    def unregister_mobile_device(self, device_id: str):
        """Unregister a mobile device."""
        self.auth.unregister_device(device_id)
        if device_id in self.mobile_devices:
            self.mobile_devices[device_id]['status'] = 'unregistered'

        logger.info(f"Unregistered mobile device: {device_id}")

    def authenticate_device(self, device_id: str, auth_token: str) -> bool:
        """Authenticate a device."""
        return self.auth.authenticate_device(device_id, auth_token)

    def handle_mobile_message(self, device_id: str, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle incoming message from mobile device."""
        message_type = message.get('type')

        try:
            if message_type == 'pairing_request':
                return self._handle_pairing_request(message)
            elif message_type == 'auth_request':
                return self._handle_auth_request(device_id, message)
            elif message_type == 'pull_response':
                self.pull.handle_incoming_data(device_id, message)
                return None
            elif message_type == 'asset_data':
                self.pull.handle_incoming_data(device_id, message)
                return None
            elif message_type == 'workflow_data':
                self.pull.handle_incoming_data(device_id, message)
                return None
            elif message_type == 'device_info_data':
                self.pull.handle_incoming_data(device_id, message)
                return None
            elif message_type == 'remote_command':
                return self.remote_control.handle_remote_command(device_id, message)
            elif message_type == 'preview_subscribe':
                preview_id = message.get('preview_id')
                if preview_id:
                    self.preview.subscribe_to_preview(preview_id, device_id)
                return {'status': 'success'}
            elif message_type == 'preview_unsubscribe':
                preview_id = message.get('preview_id')
                if preview_id:
                    self.preview.unsubscribe_from_preview(preview_id, device_id)
                return {'status': 'success'}
            else:
                logger.warning(f"Unknown message type from {device_id}: {message_type}")
                return {'status': 'error', 'error': 'Unknown message type'}

        except Exception as e:
            logger.error(f"Error handling mobile message: {e}")
            return {'status': 'error', 'error': str(e)}

    def push_asset_to_device(self, device_id: str, asset_path: str, asset_type: str) -> str:
        """Push an asset to a mobile device."""
        return self.push.push_asset(device_id, asset_path, asset_type)

    def push_workflow_to_device(self, device_id: str, workflow_data: Dict[str, Any], workflow_name: str) -> str:
        """Push a workflow to a mobile device."""
        return self.push.push_workflow(device_id, workflow_data, workflow_name)

    def push_notification_to_device(self, device_id: str, title: str, message: str, notification_type: str = 'info') -> str:
        """Push a notification to a mobile device."""
        return self.push.push_notification(device_id, title, message, notification_type)

    def request_asset_from_device(self, device_id: str, asset_type: str, asset_path: Optional[str] = None) -> str:
        """Request to pull an asset from a mobile device."""
        return self.pull.request_asset_pull(device_id, asset_type, asset_path)

    def request_workflow_from_device(self, device_id: str, workflow_name: Optional[str] = None) -> str:
        """Request to pull a workflow from a mobile device."""
        return self.pull.request_workflow_pull(device_id, workflow_name)

    def start_preview_stream(self, preview_id: str, preview_type: str) -> str:
        """Start a preview stream."""
        return self.preview.start_preview_stream(preview_id, preview_type)

    def send_preview_frame(self, preview_id: str, frame_data: Any, frame_type: str = 'image'):
        """Send a preview frame."""
        self.preview.send_preview_frame(preview_id, frame_data, frame_type)

    def start_remote_session(self, device_id: str, session_type: str = 'full') -> str:
        """Start a remote control session."""
        return self.remote_control.start_remote_session(device_id, session_type)

    def get_mobile_devices(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered mobile devices."""
        return self.mobile_devices.copy()

    def get_system_status(self) -> Dict[str, Any]:
        """Get mobile bridge system status."""
        return {
            'is_running': self.is_running,
            'registered_devices': len(self.mobile_devices),
            'active_previews': len(self.preview.list_active_previews()),
            'active_remote_sessions': len(self.remote_control.list_active_sessions()),
            'pending_pushes': len(self.push.push_queue),
            'pending_pulls': len([p for p in self.pull.active_pulls.values() if p['status'] == 'requested'])
        }

    def _setup_integrations(self):
        """Set up integrations between components."""
        # Register push callbacks
        self.push.register_push_callback('asset', self._on_asset_push_complete)
        self.push.register_push_callback('workflow', self._on_workflow_push_complete)

        # Register pull callbacks
        self.pull.register_pull_callback('asset', self._on_asset_pull_complete)
        self.pull.register_pull_callback('workflow', self._on_workflow_pull_complete)
        self.pull.register_pull_callback('device_info', self._on_device_info_pull_complete)

        # Register preview callbacks
        self.preview.register_preview_callback('frame_sent', self._on_preview_frame_sent)

    def _handle_pairing_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle device pairing request."""
        device_info = message.get('device_info', {})
        pairing_token = self.auth.generate_pairing_token(device_info)

        return {
            'status': 'success',
            'pairing_token': pairing_token,
            'expires_in': 300  # 5 minutes
        }

    def _handle_auth_request(self, device_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle device authentication request."""
        pairing_token = message.get('pairing_token')

        if not pairing_token:
            return {'status': 'error', 'error': 'Pairing token required'}

        device_info = self.auth.consume_pairing_token(pairing_token)
        if not device_info:
            return {'status': 'error', 'error': 'Invalid or expired pairing token'}

        # Register the device
        auth_token = self.register_mobile_device(device_id, device_info)

        return {
            'status': 'success',
            'auth_token': auth_token,
            'device_id': device_id
        }

    def _on_asset_push_complete(self, push_request: Dict[str, Any]):
        """Callback for completed asset push."""
        device_id = push_request['device_id']
        asset_type = push_request['asset_type']

        logger.info(f"Asset push completed: {push_request['push_id']} to {device_id}")

        # Notify device of completion
        notification = {
            'type': 'push_complete',
            'push_id': push_request['push_id'],
            'asset_type': asset_type
        }

        self.sync_manager.notify_mobile_device(device_id, notification)

    def _on_workflow_push_complete(self, push_request: Dict[str, Any]):
        """Callback for completed workflow push."""
        device_id = push_request['device_id']
        workflow_name = push_request['workflow_name']

        logger.info(f"Workflow push completed: {push_request['push_id']} to {device_id}")

        # Notify device of completion
        notification = {
            'type': 'push_complete',
            'push_id': push_request['push_id'],
            'workflow_name': workflow_name
        }

        self.sync_manager.notify_mobile_device(device_id, notification)

    def _on_asset_pull_complete(self, pull_request: Dict[str, Any]):
        """Callback for completed asset pull."""
        device_id = pull_request['device_id']
        final_path = pull_request.get('final_path')

        logger.info(f"Asset pull completed: {pull_request['pull_id']} from {device_id}")

        # Could trigger additional processing here
        if final_path:
            # Notify sync manager of new asset
            self.sync_manager.on_asset_received(final_path, pull_request.get('asset_type'))

    def _on_workflow_pull_complete(self, pull_request: Dict[str, Any]):
        """Callback for completed workflow pull."""
        device_id = pull_request['device_id']
        final_path = pull_request.get('final_path')

        logger.info(f"Workflow pull completed: {pull_request['pull_id']} from {device_id}")

        # Notify sync manager of new workflow
        if final_path:
            self.sync_manager.on_workflow_received(final_path)

    def _on_device_info_pull_complete(self, pull_request: Dict[str, Any]):
        """Callback for completed device info pull."""
        device_id = pull_request['device_id']
        device_info = pull_request.get('device_info')

        logger.info(f"Device info pull completed: {pull_request['pull_id']} from {device_id}")

        # Update device info
        if device_id in self.mobile_devices and device_info:
            self.mobile_devices[device_id]['info'].update(device_info)

    def _on_preview_frame_sent(self, frame_info: Dict[str, Any]):
        """Callback for sent preview frame."""
        # Could implement frame rate monitoring or analytics here
        pass