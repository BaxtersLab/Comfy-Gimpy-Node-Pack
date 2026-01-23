# sync_manager.py

"""
Sync Manager for Comfy Gimpy Studio

Coordinates synchronization between ComfyUI, GIMP, and mobile devices.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class SyncManager:
    """Main synchronization coordinator."""

    def __init__(self):
        self.mobile_devices: Dict[str, Dict[str, Any]] = {}
        self.workflows: Dict[str, Dict[str, Any]] = {}
        self.active_executions: Dict[str, Dict[str, Any]] = {}

    def initialize(self):
        """Initialize the sync manager."""
        logger.info("Initializing Sync Manager")

    def shutdown(self):
        """Shutdown the sync manager."""
        logger.info("Sync Manager shut down")

    def notify_mobile_device(self, device_id: str, message: Dict[str, Any]):
        """Send a notification to a mobile device."""
        # This would integrate with the actual mobile communication system
        # For now, we'll store the message for the device
        if device_id not in self.mobile_devices:
            self.mobile_devices[device_id] = {'messages': []}

        if 'messages' not in self.mobile_devices[device_id]:
            self.mobile_devices[device_id]['messages'] = []

        self.mobile_devices[device_id]['messages'].append(message)
        logger.info(f"Notification queued for device {device_id}: {message.get('type', 'unknown')}")

    def execute_workflow(self, workflow_id: str, parameters: Dict[str, Any]) -> str:
        """Execute a workflow."""
        execution_id = f"exec_{workflow_id}_{len(self.active_executions)}"
        self.active_executions[execution_id] = {
            'workflow_id': workflow_id,
            'parameters': parameters,
            'status': 'running',
            'start_time': self._get_timestamp()
        }
        logger.info(f"Workflow execution started: {execution_id}")
        return execution_id

    def cancel_workflow_execution(self, execution_id: str) -> bool:
        """Cancel a workflow execution."""
        if execution_id in self.active_executions:
            self.active_executions[execution_id]['status'] = 'cancelled'
            logger.info(f"Workflow execution cancelled: {execution_id}")
            return True
        return False

    def get_workflow_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a workflow execution."""
        return self.active_executions.get(execution_id)

    def get_active_workflow_executions(self) -> List[Dict[str, Any]]:
        """Get all active workflow executions."""
        return [exec for exec in self.active_executions.values() if exec['status'] == 'running']

    def list_available_workflows(self) -> List[Dict[str, Any]]:
        """List all available workflows."""
        return list(self.workflows.values())

    def get_system_status(self) -> Dict[str, Any]:
        """Get system status."""
        return {
            'active_executions': len(self.get_active_workflow_executions()),
            'registered_devices': len(self.mobile_devices),
            'available_workflows': len(self.workflows)
        }

    def shutdown_system(self):
        """Shutdown the system."""
        logger.info("System shutdown requested")

    def restart_service(self, service_name: str) -> bool:
        """Restart a service."""
        logger.info(f"Service restart requested: {service_name}")
        return True

    def get_service_logs(self, service: Optional[str], lines: int) -> List[str]:
        """Get service logs."""
        # Mock logs
        return [f"Log line {i}" for i in range(min(lines, 10))]

    def on_asset_received(self, asset_path: str, asset_type: str):
        """Handle received asset."""
        logger.info(f"Asset received: {asset_path} ({asset_type})")

    def on_workflow_received(self, workflow_path: str):
        """Handle received workflow."""
        logger.info(f"Workflow received: {workflow_path}")

    def _get_timestamp(self):
        """Get current timestamp."""
        import time
        return int(time.time())