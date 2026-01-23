# mobile_bridge/remote_control.py

"""
Mobile Remote Control System

Handles remote control commands from mobile devices to Comfy Gimpy Studio.
"""

import json
import logging
import time
import threading
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path

from ..shared.config import ConfigManager
from ..sync_manager import SyncManager

logger = logging.getLogger(__name__)

class MobileRemoteControl:
    """Mobile remote control system."""

    def __init__(self, sync_manager: SyncManager):
        self.sync_manager = sync_manager
        self.config_manager = ConfigManager()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.command_handlers: Dict[str, Callable] = {}
        self.session_permissions: Dict[str, Dict[str, bool]] = {}

        # Remote control settings
        self.max_concurrent_sessions = 5
        self.session_timeout = 1800  # 30 minutes
        self.command_timeout = 30  # 30 seconds

        # Register default command handlers
        self._register_default_handlers()

    def initialize(self):
        """Initialize the remote control system."""
        logger.info("Initializing mobile remote control system")

        # Start session cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self.cleanup_thread.start()

    def shutdown(self):
        """Shutdown the remote control system."""
        logger.info("Mobile remote control system shut down")

    def start_remote_session(self, device_id: str, session_type: str = 'full',
                           permissions: Optional[Dict[str, bool]] = None) -> str:
        """Start a new remote control session."""
        # Check concurrent session limit
        active_count = sum(1 for s in self.active_sessions.values()
                          if s['status'] == 'active')
        if active_count >= self.max_concurrent_sessions:
            raise ValueError("Maximum concurrent remote sessions reached")

        session_id = f"remote_{device_id}_{int(time.time())}"

        session = {
            'session_id': session_id,
            'device_id': device_id,
            'type': session_type,
            'status': 'active',
            'created_at': time.time(),
            'last_activity': time.time(),
            'permissions': permissions or self._get_default_permissions(session_type),
            'command_history': [],
            'pending_commands': {}
        }

        self.active_sessions[session_id] = session
        self.session_permissions[session_id] = session['permissions']

        logger.info(f"Started remote session: {session_id} for device {device_id}")
        return session_id

    def end_remote_session(self, session_id: str):
        """End a remote control session."""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session['status'] = 'ended'
            session['ended_at'] = time.time()

            # Cancel any pending commands
            for cmd_id, cmd in session['pending_commands'].items():
                cmd['status'] = 'cancelled'

            logger.info(f"Ended remote session: {session_id}")

    def handle_remote_command(self, device_id: str, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a remote control command from a device."""
        command_type = command_data.get('command')
        session_id = command_data.get('session_id')

        # Validate session
        if not session_id or session_id not in self.active_sessions:
            return {'status': 'error', 'error': 'Invalid session'}

        session = self.active_sessions[session_id]
        if session['status'] != 'active':
            return {'status': 'error', 'error': 'Session not active'}

        if session['device_id'] != device_id:
            return {'status': 'error', 'error': 'Session device mismatch'}

        # Check permissions
        if not self._check_command_permission(session_id, command_type):
            return {'status': 'error', 'error': 'Command not permitted'}

        # Update session activity
        session['last_activity'] = time.time()

        # Handle command
        try:
            result = self._execute_command(session_id, command_type, command_data)
            session['command_history'].append({
                'command': command_type,
                'timestamp': time.time(),
                'result': 'success'
            })
            return result

        except Exception as e:
            logger.error(f"Remote command error: {command_type} - {e}")
            session['command_history'].append({
                'command': command_type,
                'timestamp': time.time(),
                'result': 'error',
                'error': str(e)
            })
            return {'status': 'error', 'error': str(e)}

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a remote session."""
        return self.active_sessions.get(session_id)

    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """List all active remote control sessions."""
        return [s for s in self.active_sessions.values() if s['status'] == 'active']

    def register_command_handler(self, command_type: str, handler: Callable):
        """Register a handler for a specific command type."""
        self.command_handlers[command_type] = handler
        logger.info(f"Registered command handler: {command_type}")

    def _register_default_handlers(self):
        """Register default command handlers."""
        self.register_command_handler('execute_workflow', self._handle_execute_workflow)
        self.register_command_handler('cancel_workflow', self._handle_cancel_workflow)
        self.register_command_handler('get_workflow_status', self._handle_get_workflow_status)
        self.register_command_handler('list_workflows', self._handle_list_workflows)
        self.register_command_handler('get_system_status', self._handle_get_system_status)
        self.register_command_handler('shutdown_system', self._handle_shutdown_system)
        self.register_command_handler('restart_service', self._handle_restart_service)
        self.register_command_handler('update_settings', self._handle_update_settings)
        self.register_command_handler('get_logs', self._handle_get_logs)

    def _execute_command(self, session_id: str, command_type: str, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a remote command."""
        if command_type in self.command_handlers:
            handler = self.command_handlers[command_type]
            return handler(session_id, command_data)
        else:
            raise ValueError(f"Unknown command type: {command_type}")

    def _check_command_permission(self, session_id: str, command_type: str) -> bool:
        """Check if a command is permitted for a session."""
        permissions = self.session_permissions.get(session_id, {})
        return permissions.get(command_type, False)

    def _get_default_permissions(self, session_type: str) -> Dict[str, bool]:
        """Get default permissions for a session type."""
        if session_type == 'full':
            return {
                'execute_workflow': True,
                'cancel_workflow': True,
                'get_workflow_status': True,
                'list_workflows': True,
                'get_system_status': True,
                'shutdown_system': False,  # Requires special permission
                'restart_service': False,  # Requires special permission
                'update_settings': False,  # Requires special permission
                'get_logs': True
            }
        elif session_type == 'monitor':
            return {
                'execute_workflow': False,
                'cancel_workflow': False,
                'get_workflow_status': True,
                'list_workflows': True,
                'get_system_status': True,
                'shutdown_system': False,
                'restart_service': False,
                'update_settings': False,
                'get_logs': True
            }
        elif session_type == 'limited':
            return {
                'execute_workflow': False,
                'cancel_workflow': False,
                'get_workflow_status': True,
                'list_workflows': False,
                'get_system_status': False,
                'shutdown_system': False,
                'restart_service': False,
                'update_settings': False,
                'get_logs': False
            }
        else:
            return {}

    def _handle_execute_workflow(self, session_id: str, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle workflow execution command."""
        workflow_id = command_data.get('workflow_id')
        parameters = command_data.get('parameters', {})

        if not workflow_id:
            raise ValueError("Workflow ID required")

        # Execute workflow via sync manager
        execution_id = self.sync_manager.execute_workflow(workflow_id, parameters)

        return {
            'status': 'success',
            'execution_id': execution_id,
            'message': f'Workflow {workflow_id} started'
        }

    def _handle_cancel_workflow(self, session_id: str, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle workflow cancellation command."""
        execution_id = command_data.get('execution_id')

        if not execution_id:
            raise ValueError("Execution ID required")

        # Cancel workflow via sync manager
        success = self.sync_manager.cancel_workflow_execution(execution_id)

        return {
            'status': 'success' if success else 'error',
            'execution_id': execution_id,
            'message': f'Workflow execution {execution_id} cancelled' if success else 'Cancellation failed'
        }

    def _handle_get_workflow_status(self, session_id: str, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle workflow status query."""
        execution_id = command_data.get('execution_id')

        if execution_id:
            # Get specific execution status
            status = self.sync_manager.get_workflow_execution_status(execution_id)
            return {
                'status': 'success',
                'execution_status': status
            }
        else:
            # Get all active executions
            executions = self.sync_manager.get_active_workflow_executions()
            return {
                'status': 'success',
                'active_executions': executions
            }

    def _handle_list_workflows(self, session_id: str, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle workflow listing command."""
        workflows = self.sync_manager.list_available_workflows()

        return {
            'status': 'success',
            'workflows': workflows
        }

    def _handle_get_system_status(self, session_id: str, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system status query."""
        system_status = self.sync_manager.get_system_status()

        return {
            'status': 'success',
            'system_status': system_status
        }

    def _handle_shutdown_system(self, session_id: str, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system shutdown command."""
        # This would require special permissions and confirmation
        force = command_data.get('force', False)

        if not force:
            return {
                'status': 'error',
                'error': 'Shutdown requires force=true parameter'
            }

        # Schedule shutdown
        def delayed_shutdown():
            time.sleep(5)  # Give time for response
            self.sync_manager.shutdown_system()

        threading.Thread(target=delayed_shutdown, daemon=True).start()

        return {
            'status': 'success',
            'message': 'System shutdown initiated'
        }

    def _handle_restart_service(self, session_id: str, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle service restart command."""
        service_name = command_data.get('service')

        if not service_name:
            raise ValueError("Service name required")

        # Restart service via sync manager
        success = self.sync_manager.restart_service(service_name)

        return {
            'status': 'success' if success else 'error',
            'service': service_name,
            'message': f'Service {service_name} restarted' if success else f'Failed to restart {service_name}'
        }

    def _handle_update_settings(self, session_id: str, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle settings update command."""
        settings = command_data.get('settings', {})

        if not settings:
            raise ValueError("Settings required")

        # Update settings via config manager
        for key, value in settings.items():
            self.config_manager.set(key, value)

        return {
            'status': 'success',
            'message': 'Settings updated'
        }

    def _handle_get_logs(self, session_id: str, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle log retrieval command."""
        lines = command_data.get('lines', 100)
        service = command_data.get('service')

        # Get logs via sync manager
        logs = self.sync_manager.get_service_logs(service, lines)

        return {
            'status': 'success',
            'logs': logs
        }

    def _cleanup_worker(self):
        """Background worker for cleaning up expired sessions."""
        while True:
            try:
                current_time = time.time()

                expired_sessions = []
                for session_id, session in self.active_sessions.items():
                    if (session['status'] == 'active' and
                        current_time - session['last_activity'] > self.session_timeout):
                        expired_sessions.append(session_id)

                for session_id in expired_sessions:
                    logger.info(f"Auto-ending expired remote session: {session_id}")
                    self.end_remote_session(session_id)

                time.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Session cleanup error: {e}")
                time.sleep(60)