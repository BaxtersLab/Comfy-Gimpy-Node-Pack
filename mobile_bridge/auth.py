# mobile_bridge/auth.py

"""
Mobile Authentication System

Handles device pairing, authentication, and session management for mobile companions.
"""

import json
import logging
import secrets
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
import jwt
import hashlib

from ..shared.config import ConfigManager

logger = logging.getLogger(__name__)

class MobileAuth:
    """Mobile device authentication and session management."""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.devices: Dict[str, Dict[str, Any]] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.pairing_tokens: Dict[str, Dict[str, Any]] = {}

        # JWT settings
        self.jwt_secret = self._generate_jwt_secret()
        self.jwt_algorithm = 'HS256'
        self.token_expiry = 24 * 60 * 60  # 24 hours

        # Load persisted data
        self._load_devices()
        self._load_sessions()

    def initialize(self):
        """Initialize the authentication system."""
        logger.info("Initializing mobile authentication system")

        # Clean up expired tokens and sessions
        self._cleanup_expired_tokens()
        self._cleanup_expired_sessions()

    def shutdown(self):
        """Shutdown the authentication system."""
        self._save_devices()
        self._save_sessions()
        logger.info("Mobile authentication system shut down")

    def generate_pairing_token(self, device_info: Optional[Dict[str, Any]] = None) -> str:
        """Generate a pairing token for device registration."""
        token = secrets.token_urlsafe(32)

        self.pairing_tokens[token] = {
            'created_at': time.time(),
            'expires_at': time.time() + 300,  # 5 minutes
            'device_info': device_info or {},
            'used': False
        }

        logger.info(f"Generated pairing token: {token[:8]}...")
        return token

    def validate_pairing_token(self, token: str) -> bool:
        """Validate a pairing token."""
        if token not in self.pairing_tokens:
            return False

        token_data = self.pairing_tokens[token]

        # Check if expired
        if time.time() > token_data['expires_at']:
            del self.pairing_tokens[token]
            return False

        # Check if already used
        if token_data['used']:
            return False

        return True

    def consume_pairing_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Consume a pairing token and return device info."""
        if not self.validate_pairing_token(token):
            return None

        token_data = self.pairing_tokens[token]
        token_data['used'] = True

        # Clean up token after short delay
        def cleanup_token():
            time.sleep(60)  # Keep for 1 minute for debugging
            self.pairing_tokens.pop(token, None)

        import threading
        threading.Thread(target=cleanup_token, daemon=True).start()

        return token_data['device_info']

    def register_device(self, device_id: str, device_info: Dict[str, Any]) -> str:
        """Register a mobile device."""
        auth_token = self._generate_auth_token(device_id)

        self.devices[device_id] = {
            'device_id': device_id,
            'device_info': device_info,
            'auth_token_hash': self._hash_token(auth_token),
            'registered_at': time.time(),
            'last_seen': time.time(),
            'status': 'active'
        }

        self._save_devices()
        logger.info(f"Registered mobile device: {device_id}")

        return auth_token

    def unregister_device(self, device_id: str):
        """Unregister a mobile device."""
        if device_id in self.devices:
            self.devices[device_id]['status'] = 'unregistered'
            self._save_devices()
            logger.info(f"Unregistered mobile device: {device_id}")

    def authenticate_device(self, device_id: str, auth_token: str) -> bool:
        """Authenticate a device with its token."""
        if device_id not in self.devices:
            return False

        device = self.devices[device_id]
        if device['status'] != 'active':
            return False

        # Verify token hash
        token_hash = self._hash_token(auth_token)
        if token_hash != device['auth_token_hash']:
            return False

        # Update last seen
        device['last_seen'] = time.time()
        return True

    def create_session(self, device_id: str, session_type: str) -> str:
        """Create a new authenticated session."""
        session_id = f"{device_id}_{session_type}_{int(time.time())}"

        self.sessions[session_id] = {
            'session_id': session_id,
            'device_id': device_id,
            'type': session_type,
            'created_at': time.time(),
            'expires_at': time.time() + self.token_expiry,
            'status': 'active'
        }

        logger.info(f"Created session: {session_id}")
        return session_id

    def validate_session(self, session_id: str) -> bool:
        """Validate an active session."""
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]

        if session['status'] != 'active':
            return False

        if time.time() > session['expires_at']:
            session['status'] = 'expired'
            return False

        return True

    def end_session(self, session_id: str):
        """End an active session."""
        if session_id in self.sessions:
            self.sessions[session_id]['status'] = 'ended'
            self.sessions[session_id]['ended_at'] = time.time()
            logger.info(f"Ended session: {session_id}")

    def get_device_info(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a registered device."""
        return self.devices.get(device_id)

    def list_devices(self) -> List[Dict[str, Any]]:
        """List all registered devices."""
        return list(self.devices.values())

    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions."""
        return [s for s in self.sessions.values() if s['status'] == 'active']

    def generate_jwt_token(self, device_id: str, session_id: str) -> str:
        """Generate a JWT token for authenticated requests."""
        payload = {
            'device_id': device_id,
            'session_id': session_id,
            'iat': int(time.time()),
            'exp': int(time.time()) + self.token_expiry
        }

        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    def validate_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate a JWT token and return payload."""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])

            # Validate session
            session_id = payload.get('session_id')
            if not session_id or not self.validate_session(session_id):
                return None

            return payload

        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def _generate_auth_token(self, device_id: str) -> str:
        """Generate an authentication token for a device."""
        return secrets.token_urlsafe(64)

    def _hash_token(self, token: str) -> str:
        """Hash a token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    def _generate_jwt_secret(self) -> str:
        """Generate or load JWT secret."""
        # In production, this should be loaded from secure config
        return secrets.token_hex(32)

    def _cleanup_expired_tokens(self):
        """Clean up expired pairing tokens."""
        current_time = time.time()
        expired = [token for token, data in self.pairing_tokens.items()
                  if current_time > data['expires_at']]

        for token in expired:
            del self.pairing_tokens[token]

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired pairing tokens")

    def _cleanup_expired_sessions(self):
        """Clean up expired sessions."""
        current_time = time.time()
        expired = [session_id for session_id, session in self.sessions.items()
                  if current_time > session.get('expires_at', 0)]

        for session_id in expired:
            self.sessions[session_id]['status'] = 'expired'

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")

    def _load_devices(self):
        """Load persisted device data."""
        try:
            devices_file = Path.home() / '.comfy_gimpy' / 'mobile_devices.json'
            if devices_file.exists():
                with open(devices_file, 'r') as f:
                    self.devices = json.load(f)
                logger.info(f"Loaded {len(self.devices)} registered devices")
        except Exception as e:
            logger.error(f"Failed to load device data: {e}")

    def _save_devices(self):
        """Save device data to disk."""
        try:
            config_dir = Path.home() / '.comfy_gimpy'
            config_dir.mkdir(parents=True, exist_ok=True)

            devices_file = config_dir / 'mobile_devices.json'
            with open(devices_file, 'w') as f:
                json.dump(self.devices, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save device data: {e}")

    def _load_sessions(self):
        """Load persisted session data."""
        try:
            sessions_file = Path.home() / '.comfy_gimpy' / 'mobile_sessions.json'
            if sessions_file.exists():
                with open(sessions_file, 'r') as f:
                    self.sessions = json.load(f)
                logger.info(f"Loaded {len(self.sessions)} sessions")
        except Exception as e:
            logger.error(f"Failed to load session data: {e}")

    def _save_sessions(self):
        """Save session data to disk."""
        try:
            config_dir = Path.home() / '.comfy_gimpy'
            config_dir.mkdir(parents=True, exist_ok=True)

            sessions_file = config_dir / 'mobile_sessions.json'
            with open(sessions_file, 'w') as f:
                json.dump(self.sessions, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save session data: {e}")