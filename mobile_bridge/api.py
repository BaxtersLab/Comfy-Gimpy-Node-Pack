# mobile_bridge/api.py

"""
Mobile API Server

Provides REST API endpoints for mobile companion communication.
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from flask import Blueprint, request, jsonify, current_app
import qrcode
import io
import base64

from ..gimp_comfy_bridge.sync.sync_manager import SyncManager
from ..shared.config import ConfigManager

logger = logging.getLogger(__name__)

# Create blueprint
mobile_bp = Blueprint('mobile', __name__, url_prefix='/api/mobile')

class MobileAPI:
    """Mobile API server for companion app communication."""

    def __init__(self):
        self.app = None
        self.server = None
        self.sync_manager = SyncManager()
        self.config_manager = ConfigManager()

        # Mobile sessions
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.devices: Dict[str, Dict[str, Any]] = {}

    def start(self, host: str = '0.0.0.0', port: int = 8081):
        """Start the mobile API server."""
        from flask import Flask

        self.app = Flask(__name__)
        self.app.register_blueprint(mobile_bp)

        # Initialize with mobile bridge context
        with self.app.app_context():
            current_app.mobile_api = self

        logger.info(f"Starting mobile API server on {host}:{port}")
        self.server = self.app.run(host=host, port=port, debug=False, use_reloader=False)

    def stop(self):
        """Stop the mobile API server."""
        if self.server:
            self.server.shutdown()
            logger.info("Mobile API server stopped")

    def register_device(self, device_id: str, device_info: Dict[str, Any]):
        """Register a mobile device."""
        self.devices[device_id] = {
            **device_info,
            'registered_at': self._get_timestamp(),
            'last_seen': self._get_timestamp()
        }
        logger.info(f"Registered mobile device: {device_id}")

    def unregister_device(self, device_id: str):
        """Unregister a mobile device."""
        self.devices.pop(device_id, None)
        logger.info(f"Unregistered mobile device: {device_id}")

    def update_device_heartbeat(self, device_id: str):
        """Update device last seen timestamp."""
        if device_id in self.devices:
            self.devices[device_id]['last_seen'] = self._get_timestamp()

    def create_session(self, device_id: str, session_type: str) -> str:
        """Create a new mobile session."""
        session_id = f"{device_id}_{session_type}_{len(self.sessions)}"
        self.sessions[session_id] = {
            'device_id': device_id,
            'type': session_type,
            'created_at': self._get_timestamp(),
            'status': 'active'
        }
        logger.info(f"Created mobile session: {session_id}")
        return session_id

    def end_session(self, session_id: str):
        """End a mobile session."""
        if session_id in self.sessions:
            self.sessions[session_id]['status'] = 'ended'
            self.sessions[session_id]['ended_at'] = self._get_timestamp()
            logger.info(f"Ended mobile session: {session_id}")

    def _get_timestamp(self):
        """Get current timestamp."""
        import time
        return int(time.time())

# API Endpoints

@mobile_bp.route('/pairing/qr', methods=['GET'])
def get_pairing_qr():
    """Generate QR code for device pairing."""
    try:
        # Generate pairing token
        pairing_token = _generate_pairing_token()

        # Create pairing URL
        pairing_url = f"comfy-gimpy://pair?token={pairing_token}"

        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(pairing_url)
        qr.make(fit=True)

        # Create image
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()

        return jsonify({
            'success': True,
            'pairing_token': pairing_token,
            'qr_code': f"data:image/png;base64,{qr_base64}",
            'pairing_url': pairing_url
        })

    except Exception as e:
        logger.error(f"Failed to generate pairing QR: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mobile_bp.route('/pairing/<token>', methods=['POST'])
def complete_pairing(token: str):
    """Complete device pairing."""
    try:
        data = request.get_json()

        if not data or 'device_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing device_id'
            }), 400

        device_id = data['device_id']
        device_info = data.get('device_info', {})

        # Validate token (in real implementation, check against stored tokens)
        if not _validate_pairing_token(token):
            return jsonify({
                'success': False,
                'error': 'Invalid pairing token'
            }), 401

        # Register device
        mobile_api = current_app.mobile_api
        mobile_api.register_device(device_id, device_info)

        # Generate auth token
        auth_token = _generate_auth_token(device_id)

        return jsonify({
            'success': True,
            'auth_token': auth_token,
            'device_id': device_id
        })

    except Exception as e:
        logger.error(f"Failed to complete pairing: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mobile_bp.route('/devices', methods=['GET'])
def list_devices():
    """List registered mobile devices."""
    try:
        mobile_api = current_app.mobile_api
        devices = mobile_api.devices

        return jsonify({
            'success': True,
            'devices': list(devices.values())
        })

    except Exception as e:
        logger.error(f"Failed to list devices: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mobile_bp.route('/preview/start', methods=['POST'])
def start_preview():
    """Start preview streaming to mobile device."""
    try:
        data = request.get_json()
        device_id = data.get('device_id')

        if not device_id:
            return jsonify({
                'success': False,
                'error': 'Missing device_id'
            }), 400

        mobile_api = current_app.mobile_api
        session_id = mobile_api.create_session(device_id, 'preview')

        # Start preview streaming (implementation would integrate with preview system)
        _start_preview_stream(session_id, device_id)

        return jsonify({
            'success': True,
            'session_id': session_id
        })

    except Exception as e:
        logger.error(f"Failed to start preview: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mobile_bp.route('/preview/stop', methods=['POST'])
def stop_preview():
    """Stop preview streaming."""
    try:
        data = request.get_json()
        session_id = data.get('session_id')

        if not session_id:
            return jsonify({
                'success': False,
                'error': 'Missing session_id'
            }), 400

        mobile_api = current_app.mobile_api
        mobile_api.end_session(session_id)

        # Stop preview streaming
        _stop_preview_stream(session_id)

        return jsonify({
            'success': True
        })

    except Exception as e:
        logger.error(f"Failed to stop preview: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mobile_bp.route('/remote/execute', methods=['POST'])
def execute_remote_command():
    """Execute remote command from mobile device."""
    try:
        data = request.get_json()

        if not data or 'command' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing command'
            }), 400

        command = data['command']
        params = data.get('params', {})
        device_id = data.get('device_id')

        # Authenticate device
        if not _authenticate_device(device_id, request.headers.get('Authorization')):
            return jsonify({
                'success': False,
                'error': 'Authentication failed'
            }), 401

        # Execute command
        result = _execute_remote_command(command, params)

        return jsonify({
            'success': True,
            'result': result
        })

    except Exception as e:
        logger.error(f"Failed to execute remote command: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mobile_bp.route('/assets/push', methods=['POST'])
def push_assets():
    """Push assets from mobile device."""
    try:
        device_id = request.form.get('device_id')
        files = request.files.getlist('assets')

        if not device_id:
            return jsonify({
                'success': False,
                'error': 'Missing device_id'
            }), 400

        # Authenticate device
        if not _authenticate_device(device_id, request.headers.get('Authorization')):
            return jsonify({
                'success': False,
                'error': 'Authentication failed'
            }), 401

        # Process uploaded assets
        uploaded_assets = []
        for file in files:
            asset_info = _process_uploaded_asset(file, device_id)
            uploaded_assets.append(asset_info)

        return jsonify({
            'success': True,
            'uploaded_assets': uploaded_assets
        })

    except Exception as e:
        logger.error(f"Failed to push assets: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mobile_bp.route('/workflows/trigger', methods=['POST'])
def trigger_workflow():
    """Trigger workflow execution from mobile."""
    try:
        data = request.get_json()

        if not data or 'workflow_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing workflow_id'
            }), 400

        workflow_id = data['workflow_id']
        inputs = data.get('inputs', {})
        device_id = data.get('device_id')

        # Authenticate device
        if not _authenticate_device(device_id, request.headers.get('Authorization')):
            return jsonify({
                'success': False,
                'error': 'Authentication failed'
            }), 401

        # Trigger workflow execution
        execution_id = _trigger_workflow_execution(workflow_id, inputs, device_id)

        return jsonify({
            'success': True,
            'execution_id': execution_id
        })

    except Exception as e:
        logger.error(f"Failed to trigger workflow: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mobile_bp.route('/brand-kits/sync', methods=['GET'])
def get_brand_kits():
    """Get available brand kits for mobile sync."""
    try:
        device_id = request.args.get('device_id')

        if not device_id:
            return jsonify({
                'success': False,
                'error': 'Missing device_id'
            }), 400

        # Authenticate device
        if not _authenticate_device(device_id, request.headers.get('Authorization')):
            return jsonify({
                'success': False,
                'error': 'Authentication failed'
            }), 401

        # Get brand kits
        brand_kits = _get_brand_kits_for_sync()

        return jsonify({
            'success': True,
            'brand_kits': brand_kits
        })

    except Exception as e:
        logger.error(f"Failed to get brand kits: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mobile_bp.route('/templates/select', methods=['POST'])
def select_template():
    """Select template from mobile device."""
    try:
        data = request.get_json()

        if not data or 'template_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing template_id'
            }), 400

        template_id = data['template_id']
        device_id = data.get('device_id')

        # Authenticate device
        if not _authenticate_device(device_id, request.headers.get('Authorization')):
            return jsonify({
                'success': False,
                'error': 'Authentication failed'
            }), 401

        # Select template
        _select_template(template_id, device_id)

        return jsonify({
            'success': True
        })

    except Exception as e:
        logger.error(f"Failed to select template: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Helper functions

def _generate_pairing_token() -> str:
    """Generate a unique pairing token."""
    import secrets
    return secrets.token_urlsafe(32)

def _validate_pairing_token(token: str) -> bool:
    """Validate pairing token."""
    # In real implementation, check against stored valid tokens
    return len(token) > 10  # Simple validation

def _generate_auth_token(device_id: str) -> str:
    """Generate authentication token for device."""
    import secrets
    return secrets.token_urlsafe(64)

def _authenticate_device(device_id: str, auth_header: str) -> bool:
    """Authenticate mobile device."""
    # In real implementation, validate JWT token or similar
    return bool(device_id and auth_header)

def _start_preview_stream(session_id: str, device_id: str):
    """Start preview streaming to device."""
    # Implementation would integrate with preview system
    pass

def _stop_preview_stream(session_id: str):
    """Stop preview streaming."""
    # Implementation would integrate with preview system
    pass

def _execute_remote_command(command: str, params: Dict[str, Any]) -> Any:
    """Execute remote command."""
    # Implementation would route to appropriate system
    if command == 'get_status':
        return {'status': 'ready'}
    elif command == 'list_workflows':
        return {'workflows': []}
    else:
        return {'result': 'command_executed'}

def _process_uploaded_asset(file, device_id: str) -> Dict[str, Any]:
    """Process uploaded asset from mobile device."""
    # Implementation would save asset and return info
    return {
        'asset_id': f'mobile_{device_id}_{file.filename}',
        'filename': file.filename,
        'size': len(file.read())
    }

def _trigger_workflow_execution(workflow_id: str, inputs: Dict[str, Any], device_id: str) -> str:
    """Trigger workflow execution."""
    # Implementation would integrate with workflow system
    return f'execution_{workflow_id}_{device_id}'

def _get_brand_kits_for_sync() -> List[Dict[str, Any]]:
    """Get brand kits for mobile sync."""
    # Implementation would integrate with brand kit system
    return [
        {'id': 'brand_1', 'name': 'Brand One'},
        {'id': 'brand_2', 'name': 'Brand Two'}
    ]

def _select_template(template_id: str, device_id: str):
    """Select template from mobile."""
    # Implementation would integrate with template system
    pass

# Register blueprint
def init_app(app):
    """Initialize the mobile API with the Flask app."""
    app.register_blueprint(mobile_bp)