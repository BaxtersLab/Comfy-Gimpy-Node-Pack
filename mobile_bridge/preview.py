# mobile_bridge/preview.py

"""
Mobile Preview System

Handles real-time preview streaming of ComfyUI outputs to mobile devices.
"""

import json
import logging
import time
import threading
import asyncio
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
import base64
import io

from ..shared.config import ConfigManager
from ..sync_manager import SyncManager

logger = logging.getLogger(__name__)

class MobilePreview:
    """Mobile preview streaming system."""

    def __init__(self, sync_manager: SyncManager):
        self.sync_manager = sync_manager
        self.config_manager = ConfigManager()
        self.active_previews: Dict[str, Dict[str, Any]] = {}
        self.preview_subscribers: Dict[str, List[str]] = {}  # preview_id -> [device_ids]
        self.preview_callbacks: Dict[str, Callable] = {}

        # Preview settings
        self.max_preview_size = 1920  # Max dimension for previews
        self.preview_quality = 85  # JPEG quality (0-100)
        self.frame_rate_limit = 10  # Max FPS for live previews
        self.preview_timeout = 3600  # 1 hour timeout

        # Preview cache
        self.preview_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timeout = 300  # 5 minutes

    def initialize(self):
        """Initialize the preview system."""
        logger.info("Initializing mobile preview system")

        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self.cleanup_thread.start()

    def shutdown(self):
        """Shutdown the preview system."""
        logger.info("Mobile preview system shut down")

    def start_preview_stream(self, preview_id: str, preview_type: str,
                           metadata: Optional[Dict[str, Any]] = None) -> str:
        """Start a new preview stream."""
        if preview_id in self.active_previews:
            logger.warning(f"Preview stream already exists: {preview_id}")
            return preview_id

        preview_stream = {
            'preview_id': preview_id,
            'type': preview_type,
            'metadata': metadata or {},
            'status': 'active',
            'created_at': time.time(),
            'last_update': time.time(),
            'frame_count': 0,
            'subscribers': set(),
            'settings': {
                'max_size': self.max_preview_size,
                'quality': self.preview_quality,
                'fps_limit': self.frame_rate_limit
            }
        }

        self.active_previews[preview_id] = preview_stream
        self.preview_subscribers[preview_id] = []

        logger.info(f"Started preview stream: {preview_id} ({preview_type})")
        return preview_id

    def stop_preview_stream(self, preview_id: str):
        """Stop a preview stream."""
        if preview_id in self.active_previews:
            preview_stream = self.active_previews[preview_id]
            preview_stream['status'] = 'stopped'
            preview_stream['stopped_at'] = time.time()

            # Notify subscribers
            self._notify_subscribers_stream_ended(preview_id)

            logger.info(f"Stopped preview stream: {preview_id}")

    def subscribe_to_preview(self, preview_id: str, device_id: str) -> bool:
        """Subscribe a device to a preview stream."""
        if preview_id not in self.active_previews:
            return False

        if device_id not in self.preview_subscribers[preview_id]:
            self.preview_subscribers[preview_id].append(device_id)
            self.active_previews[preview_id]['subscribers'].add(device_id)

            logger.info(f"Device {device_id} subscribed to preview {preview_id}")
            return True

        return False

    def unsubscribe_from_preview(self, preview_id: str, device_id: str):
        """Unsubscribe a device from a preview stream."""
        if preview_id in self.preview_subscribers:
            if device_id in self.preview_subscribers[preview_id]:
                self.preview_subscribers[preview_id].remove(device_id)
                self.active_previews[preview_id]['subscribers'].discard(device_id)

                logger.info(f"Device {device_id} unsubscribed from preview {preview_id}")

    def send_preview_frame(self, preview_id: str, frame_data: Any,
                          frame_type: str = 'image', metadata: Optional[Dict[str, Any]] = None):
        """Send a preview frame to all subscribers."""
        if preview_id not in self.active_previews:
            return

        preview_stream = self.active_previews[preview_id]
        if preview_stream['status'] != 'active':
            return

        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - preview_stream['last_update']
        min_interval = 1.0 / self.frame_rate_limit

        if time_since_last < min_interval:
            return  # Skip frame to respect FPS limit

        # Process frame data
        processed_frame = self._process_frame_data(frame_data, frame_type)

        if processed_frame:
            frame_info = {
                'preview_id': preview_id,
                'frame_num': preview_stream['frame_count'],
                'timestamp': current_time,
                'frame_type': frame_type,
                'data': processed_frame,
                'metadata': metadata or {}
            }

            # Send to all subscribers
            self._send_frame_to_subscribers(preview_id, frame_info)

            # Update stream info
            preview_stream['last_update'] = current_time
            preview_stream['frame_count'] += 1

            # Cache frame for late subscribers
            self._cache_frame(preview_id, frame_info)

    def get_preview_info(self, preview_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a preview stream."""
        return self.active_previews.get(preview_id)

    def list_active_previews(self) -> List[Dict[str, Any]]:
        """List all active preview streams."""
        return [p for p in self.active_previews.values() if p['status'] == 'active']

    def get_cached_frame(self, preview_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent cached frame for a preview."""
        if preview_id in self.preview_cache:
            cache_entry = self.preview_cache[preview_id]
            if time.time() - cache_entry['cached_at'] < self.cache_timeout:
                return cache_entry['frame']
        return None

    def register_preview_callback(self, event_type: str, callback: Callable):
        """Register a callback for preview events."""
        self.preview_callbacks[event_type] = callback

    def _process_frame_data(self, frame_data: Any, frame_type: str) -> Optional[str]:
        """Process frame data for transmission."""
        try:
            if frame_type == 'image':
                return self._process_image_frame(frame_data)
            elif frame_type == 'text':
                return self._process_text_frame(frame_data)
            elif frame_type == 'data':
                return self._process_data_frame(frame_data)
            else:
                logger.warning(f"Unknown frame type: {frame_type}")
                return None

        except Exception as e:
            logger.error(f"Error processing frame data: {e}")
            return None

    def _process_image_frame(self, image_data: Any) -> Optional[str]:
        """Process image frame data."""
        try:
            # Handle different image formats
            if isinstance(image_data, str):
                # Assume base64 encoded
                return image_data
            elif hasattr(image_data, 'save'):
                # PIL Image
                buffer = io.BytesIO()
                # Resize if too large
                if max(image_data.size) > self.max_preview_size:
                    image_data.thumbnail((self.max_preview_size, self.max_preview_size))
                image_data.save(buffer, format='JPEG', quality=self.preview_quality)
                return base64.b64encode(buffer.getvalue()).decode()
            elif isinstance(image_data, bytes):
                # Raw image bytes
                return base64.b64encode(image_data).decode()
            else:
                logger.warning(f"Unsupported image data type: {type(image_data)}")
                return None

        except Exception as e:
            logger.error(f"Error processing image frame: {e}")
            return None

    def _process_text_frame(self, text_data: Any) -> Optional[str]:
        """Process text frame data."""
        try:
            if isinstance(text_data, str):
                return text_data
            elif isinstance(text_data, dict):
                return json.dumps(text_data)
            else:
                return str(text_data)
        except Exception as e:
            logger.error(f"Error processing text frame: {e}")
            return None

    def _process_data_frame(self, data: Any) -> Optional[str]:
        """Process generic data frame."""
        try:
            if isinstance(data, dict):
                return json.dumps(data)
            elif isinstance(data, (list, tuple)):
                return json.dumps(data)
            else:
                return str(data)
        except Exception as e:
            logger.error(f"Error processing data frame: {e}")
            return None

    def _send_frame_to_subscribers(self, preview_id: str, frame_info: Dict[str, Any]):
        """Send a frame to all subscribers of a preview."""
        if preview_id not in self.preview_subscribers:
            return

        frame_data = {
            'type': 'preview_frame',
            'preview_id': preview_id,
            'frame_num': frame_info['frame_num'],
            'timestamp': frame_info['timestamp'],
            'frame_type': frame_info['frame_type'],
            'data': frame_info['data'],
            'metadata': frame_info['metadata']
        }

        for device_id in self.preview_subscribers[preview_id]:
            try:
                self.sync_manager.notify_mobile_device(device_id, frame_data)
            except Exception as e:
                logger.error(f"Error sending frame to device {device_id}: {e}")

    def _notify_subscribers_stream_ended(self, preview_id: str):
        """Notify subscribers that a preview stream has ended."""
        if preview_id not in self.preview_subscribers:
            return

        end_data = {
            'type': 'preview_ended',
            'preview_id': preview_id,
            'timestamp': time.time()
        }

        for device_id in self.preview_subscribers[preview_id]:
            try:
                self.sync_manager.notify_mobile_device(device_id, end_data)
            except Exception as e:
                logger.error(f"Error sending end notification to device {device_id}: {e}")

    def _cache_frame(self, preview_id: str, frame_info: Dict[str, Any]):
        """Cache a frame for late subscribers."""
        self.preview_cache[preview_id] = {
            'frame': frame_info,
            'cached_at': time.time()
        }

    def _cleanup_worker(self):
        """Background worker for cleaning up expired previews and cache."""
        while True:
            try:
                current_time = time.time()

                # Clean up expired previews
                expired_previews = []
                for preview_id, preview in self.active_previews.items():
                    if (preview['status'] == 'active' and
                        current_time - preview['last_update'] > self.preview_timeout):
                        expired_previews.append(preview_id)

                for preview_id in expired_previews:
                    logger.info(f"Auto-stopping expired preview: {preview_id}")
                    self.stop_preview_stream(preview_id)

                # Clean up old cache entries
                expired_cache = []
                for preview_id, cache_entry in self.preview_cache.items():
                    if current_time - cache_entry['cached_at'] > self.cache_timeout:
                        expired_cache.append(preview_id)

                for preview_id in expired_cache:
                    del self.preview_cache[preview_id]

                time.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Cleanup worker error: {e}")
                time.sleep(60)