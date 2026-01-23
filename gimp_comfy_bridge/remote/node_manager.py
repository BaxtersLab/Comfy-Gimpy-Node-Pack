"""
Remote ComfyUI Node Manager for distributed compute.

Manages registration, authentication, capabilities tracking, health monitoring,
and load balancing for remote ComfyUI nodes.
"""

import logging
import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import aiohttp
import threading

from ..shared.config import load_config
from ..shared.types import RemoteNode, NodeCapabilities, NodeStatus, NodeHealth
from .capabilities import detect_capabilities
from .health import HealthMonitor

logger = logging.getLogger(__name__)


@dataclass
class NodeRegistration:
    """Node registration data."""
    url: str
    token: str
    name: Optional[str] = None
    description: Optional[str] = None
    registered_at: datetime = None
    last_seen: datetime = None
    status: NodeStatus = NodeStatus.UNKNOWN

    def __post_init__(self):
        if self.registered_at is None:
            self.registered_at = datetime.now()
        if self.last_seen is None:
            self.last_seen = datetime.now()


class RemoteNodeManager:
    """
    Manages remote ComfyUI nodes for distributed compute.

    Handles node registration, authentication, capabilities detection,
    health monitoring, and load balancing.
    """

    def __init__(self):
        self.config = load_config()
        self.nodes: Dict[str, NodeRegistration] = {}
        self.capabilities: Dict[str, NodeCapabilities] = {}
        self.health_monitor = HealthMonitor()
        self._lock = threading.RLock()
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

        # Load persisted nodes
        self._load_nodes()

    def start(self):
        """Start the node manager."""
        with self._lock:
            if self._running:
                return

            self._running = True
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            logger.info("Remote node manager started")

    def stop(self):
        """Stop the node manager."""
        with self._lock:
            if not self._running:
                return

            self._running = False
            if self._monitor_task:
                self._monitor_task.cancel()
            self._save_nodes()
            logger.info("Remote node manager stopped")

    async def register_node(self,
                          url: str,
                          token: str,
                          name: Optional[str] = None,
                          description: Optional[str] = None) -> str:
        """
        Register a new remote node.

        Args:
            url: Node URL
            token: Authentication token
            name: Optional node name
            description: Optional description

        Returns:
            Node ID

        Raises:
            ValueError: If registration fails
        """
        # Validate URL format
        if not url.startswith(('http://', 'https://')):
            raise ValueError(f"Invalid URL format: {url}")

        # Generate node ID
        node_id = f"node_{int(time.time() * 1000)}"

        # Create registration
        registration = NodeRegistration(
            url=url.rstrip('/'),
            token=token,
            name=name or f"Remote Node {node_id}",
            description=description,
            status=NodeStatus.CONNECTING
        )

        with self._lock:
            self.nodes[node_id] = registration

        logger.info(f"Registered node {node_id} at {url}")

        # Test connection and detect capabilities
        try:
            await self._test_connection(node_id)
            await self._detect_capabilities(node_id)
            registration.status = NodeStatus.ONLINE
            registration.last_seen = datetime.now()
            logger.info(f"Node {node_id} is online and ready")
        except Exception as e:
            logger.error(f"Failed to connect to node {node_id}: {e}")
            registration.status = NodeStatus.OFFLINE
            raise ValueError(f"Node registration failed: {e}")

        # Save nodes
        self._save_nodes()

        return node_id

    async def unregister_node(self, node_id: str) -> bool:
        """
        Unregister a node.

        Args:
            node_id: Node ID to remove

        Returns:
            True if removed, False if not found
        """
        with self._lock:
            if node_id not in self.nodes:
                return False

            del self.nodes[node_id]
            if node_id in self.capabilities:
                del self.capabilities[node_id]

        self.health_monitor.remove_node(node_id)
        self._save_nodes()

        logger.info(f"Unregistered node {node_id}")
        return True

    def list_nodes(self) -> List[RemoteNode]:
        """
        List all registered nodes.

        Returns:
            List of node information
        """
        with self._lock:
            nodes = []
            for node_id, registration in self.nodes.items():
                capabilities = self.capabilities.get(node_id)
                health = self.health_monitor.get_health(node_id)

                node = RemoteNode(
                    id=node_id,
                    url=registration.url,
                    name=registration.name,
                    description=registration.description,
                    status=registration.status,
                    capabilities=capabilities,
                    health=health,
                    registered_at=registration.registered_at,
                    last_seen=registration.last_seen
                )
                nodes.append(node)

            return nodes

    def get_node(self, node_id: str) -> Optional[RemoteNode]:
        """
        Get information about a specific node.

        Args:
            node_id: Node ID

        Returns:
            Node information or None if not found
        """
        with self._lock:
            registration = self.nodes.get(node_id)
            if not registration:
                return None

            capabilities = self.capabilities.get(node_id)
            health = self.health_monitor.get_health(node_id)

            return RemoteNode(
                id=node_id,
                url=registration.url,
                name=registration.name,
                description=registration.description,
                status=registration.status,
                capabilities=capabilities,
                health=health,
                registered_at=registration.registered_at,
                last_seen=registration.last_seen
            )

    def get_online_nodes(self) -> List[RemoteNode]:
        """
        Get all online nodes.

        Returns:
            List of online nodes
        """
        return [node for node in self.list_nodes()
                if node.status == NodeStatus.ONLINE]

    async def refresh_node_status(self, node_id: str) -> bool:
        """
        Refresh the status of a specific node.

        Args:
            node_id: Node ID

        Returns:
            True if node is online, False otherwise
        """
        try:
            await self._test_connection(node_id)
            await self._detect_capabilities(node_id)

            with self._lock:
                if node_id in self.nodes:
                    self.nodes[node_id].status = NodeStatus.ONLINE
                    self.nodes[node_id].last_seen = datetime.now()

            self.health_monitor.update_heartbeat(node_id)
            return True

        except Exception as e:
            logger.warning(f"Node {node_id} status check failed: {e}")

            with self._lock:
                if node_id in self.nodes:
                    self.nodes[node_id].status = NodeStatus.OFFLINE

            return False

    async def _test_connection(self, node_id: str) -> None:
        """
        Test connection to a node.

        Args:
            node_id: Node ID

        Raises:
            Exception: If connection fails
        """
        registration = self.nodes.get(node_id)
        if not registration:
            raise ValueError(f"Node {node_id} not found")

        async with aiohttp.ClientSession() as session:
            headers = {'Authorization': f'Bearer {registration.token}'}

            try:
                async with session.get(f"{registration.url}/system_stats",
                                     headers=headers, timeout=10) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP {response.status}: {await response.text()}")

                    # Basic validation that it's a ComfyUI instance
                    data = await response.json()
                    if 'system' not in data:
                        raise Exception("Invalid ComfyUI response")

            except asyncio.TimeoutError:
                raise Exception("Connection timeout")
            except aiohttp.ClientError as e:
                raise Exception(f"Connection error: {e}")

    async def _detect_capabilities(self, node_id: str) -> None:
        """
        Detect capabilities of a node.

        Args:
            node_id: Node ID
        """
        registration = self.nodes.get(node_id)
        if not registration:
            return

        try:
            capabilities = await detect_capabilities(registration.url, registration.token)
            with self._lock:
                self.capabilities[node_id] = capabilities
        except Exception as e:
            logger.warning(f"Failed to detect capabilities for node {node_id}: {e}")

    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                # Check all nodes
                node_ids = list(self.nodes.keys())
                for node_id in node_ids:
                    if not self._running:
                        break

                    await self.refresh_node_status(node_id)
                    await asyncio.sleep(1)  # Small delay between checks

                # Wait before next cycle
                await asyncio.sleep(self.config.remote_node_check_interval)

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying

    def _load_nodes(self):
        """Load persisted nodes from disk."""
        nodes_file = self.config.remote_nodes_file

        if not nodes_file.exists():
            return

        try:
            with open(nodes_file, 'r') as f:
                data = json.load(f)

            for node_id, node_data in data.items():
                # Convert datetime strings back to datetime objects
                if 'registered_at' in node_data:
                    node_data['registered_at'] = datetime.fromisoformat(node_data['registered_at'])
                if 'last_seen' in node_data:
                    node_data['last_seen'] = datetime.fromisoformat(node_data['last_seen'])

                self.nodes[node_id] = NodeRegistration(**node_data)

            logger.info(f"Loaded {len(self.nodes)} persisted nodes")

        except Exception as e:
            logger.error(f"Failed to load persisted nodes: {e}")

    def _save_nodes(self):
        """Save nodes to disk."""
        nodes_file = self.config.remote_nodes_file

        try:
            nodes_file.parent.mkdir(parents=True, exist_ok=True)

            data = {}
            for node_id, registration in self.nodes.items():
                node_dict = asdict(registration)
                # Convert datetime objects to ISO strings
                if isinstance(node_dict['registered_at'], datetime):
                    node_dict['registered_at'] = node_dict['registered_at'].isoformat()
                if isinstance(node_dict['last_seen'], datetime):
                    node_dict['last_seen'] = node_dict['last_seen'].isoformat()

                data[node_id] = node_dict

            with open(nodes_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save nodes: {e}")


# Global node manager instance
_node_manager: Optional[RemoteNodeManager] = None


def initialize_node_manager() -> RemoteNodeManager:
    """Initialize the global node manager."""
    global _node_manager
    if _node_manager is None:
        _node_manager = RemoteNodeManager()
        _node_manager.start()
    return _node_manager


def get_node_manager() -> RemoteNodeManager:
    """Get the global node manager instance."""
    if _node_manager is None:
        raise RuntimeError("Node manager not initialized")
    return _node_manager