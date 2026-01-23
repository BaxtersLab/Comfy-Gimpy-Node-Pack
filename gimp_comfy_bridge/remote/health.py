"""
Remote ComfyUI Node Health Monitoring.

Monitors the health status of remote nodes including heartbeat tracking,
response times, and failure detection.
"""

import logging
import time
import threading
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import deque

from ..shared.types import NodeHealth, NodeStatus

logger = logging.getLogger(__name__)


@dataclass
class HeartbeatRecord:
    """Record of a node heartbeat."""
    timestamp: datetime
    response_time: float
    success: bool
    error_message: Optional[str] = None


class HealthMonitor:
    """
    Monitors the health of remote ComfyUI nodes.

    Tracks heartbeats, response times, failure rates, and provides
    health status information for load balancing decisions.
    """

    def __init__(self,
                 max_heartbeat_history: int = 100,
                 heartbeat_timeout: float = 30.0,
                 failure_threshold: int = 3):
        """
        Initialize the health monitor.

        Args:
            max_heartbeat_history: Maximum number of heartbeats to keep per node
            heartbeat_timeout: Timeout for considering a node failed (seconds)
            failure_threshold: Number of consecutive failures to mark node as unhealthy
        """
        self.max_heartbeat_history = max_heartbeat_history
        self.heartbeat_timeout = heartbeat_timeout
        self.failure_threshold = failure_threshold

        # Node ID -> list of heartbeat records
        self._heartbeats: Dict[str, deque] = {}
        self._lock = threading.RLock()

    def update_heartbeat(self,
                        node_id: str,
                        response_time: float = 0.0,
                        success: bool = True,
                        error_message: Optional[str] = None):
        """
        Update heartbeat for a node.

        Args:
            node_id: Node ID
            response_time: Response time in seconds
            success: Whether the heartbeat was successful
            error_message: Optional error message if failed
        """
        with self._lock:
            if node_id not in self._heartbeats:
                self._heartbeats[node_id] = deque(maxlen=self.max_heartbeat_history)

            record = HeartbeatRecord(
                timestamp=datetime.now(),
                response_time=response_time,
                success=success,
                error_message=error_message
            )

            self._heartbeats[node_id].append(record)

            if success:
                logger.debug(f"Heartbeat success for node {node_id}: {response_time:.3f}s")
            else:
                logger.warning(f"Heartbeat failure for node {node_id}: {error_message}")

    def get_health(self, node_id: str) -> Optional[NodeHealth]:
        """
        Get health status for a node.

        Args:
            node_id: Node ID

        Returns:
            Node health information or None if no data
        """
        with self._lock:
            heartbeats = self._heartbeats.get(node_id)
            if not heartbeats:
                return None

            # Calculate health metrics
            recent_heartbeats = list(heartbeats)
            if not recent_heartbeats:
                return None

            # Get last heartbeat
            last_heartbeat = recent_heartbeats[-1]

            # Calculate uptime percentage (last 24 hours)
            now = datetime.now()
            one_day_ago = now - timedelta(days=1)

            recent_beats = [hb for hb in recent_heartbeats if hb.timestamp >= one_day_ago]
            if recent_beats:
                successful_beats = sum(1 for hb in recent_beats if hb.success)
                uptime_percentage = (successful_beats / len(recent_beats)) * 100
            else:
                uptime_percentage = 100.0 if last_heartbeat.success else 0.0

            # Calculate average response time
            successful_beats = [hb for hb in recent_beats if hb.success and hb.response_time > 0]
            avg_response_time = sum(hb.response_time for hb in successful_beats) / len(successful_beats) if successful_beats else 0.0

            # Check if node is currently healthy
            time_since_last_success = (now - last_heartbeat.timestamp).total_seconds()
            is_currently_healthy = (last_heartbeat.success and
                                  time_since_last_success < self.heartbeat_timeout)

            # Check for consecutive failures
            consecutive_failures = 0
            for hb in reversed(recent_heartbeats):
                if hb.success:
                    break
                consecutive_failures += 1

            is_stable = consecutive_failures < self.failure_threshold

            # Determine overall status
            if not is_currently_healthy:
                status = NodeStatus.OFFLINE
            elif not is_stable:
                status = NodeStatus.UNSTABLE
            else:
                status = NodeStatus.ONLINE

            return NodeHealth(
                status=status,
                uptime_percentage=uptime_percentage,
                average_response_time=avg_response_time,
                last_heartbeat=last_heartbeat.timestamp,
                consecutive_failures=consecutive_failures,
                total_heartbeats=len(recent_heartbeats),
                is_currently_healthy=is_currently_healthy,
                is_stable=is_stable
            )

    def get_all_health(self) -> Dict[str, NodeHealth]:
        """
        Get health status for all nodes.

        Returns:
            Dictionary of node ID to health status
        """
        with self._lock:
            health_status = {}
            for node_id in self._heartbeats.keys():
                health = self.get_health(node_id)
                if health:
                    health_status[node_id] = health
            return health_status

    def remove_node(self, node_id: str):
        """
        Remove a node from health monitoring.

        Args:
            node_id: Node ID to remove
        """
        with self._lock:
            if node_id in self._heartbeats:
                del self._heartbeats[node_id]
                logger.debug(f"Removed health monitoring for node {node_id}")

    def get_unhealthy_nodes(self) -> List[str]:
        """
        Get list of unhealthy node IDs.

        Returns:
            List of node IDs that are currently unhealthy
        """
        unhealthy = []
        for node_id, health in self.get_all_health().items():
            if health.status in [NodeStatus.OFFLINE, NodeStatus.UNSTABLE]:
                unhealthy.append(node_id)
        return unhealthy

    def get_healthiest_nodes(self, limit: Optional[int] = None) -> List[str]:
        """
        Get list of healthiest node IDs, sorted by health score.

        Args:
            limit: Maximum number of nodes to return

        Returns:
            List of node IDs sorted by health (best first)
        """
        health_scores = []

        for node_id, health in self.get_all_health().items():
            if health.status != NodeStatus.ONLINE:
                continue

            # Calculate health score (0-100)
            # Factors: uptime, response time, stability
            uptime_score = health.uptime_percentage
            response_score = max(0, 100 - (health.average_response_time * 10))  # Faster is better
            stability_score = 100 if health.is_stable else 50

            overall_score = (uptime_score * 0.4 + response_score * 0.4 + stability_score * 0.2)

            health_scores.append((node_id, overall_score))

        # Sort by score (highest first)
        health_scores.sort(key=lambda x: x[1], reverse=True)

        # Return node IDs
        result = [node_id for node_id, _ in health_scores]
        if limit:
            result = result[:limit]

        return result

    def get_health_summary(self) -> Dict[str, Any]:
        """
        Get a summary of overall system health.

        Returns:
            Health summary statistics
        """
        all_health = self.get_all_health()

        if not all_health:
            return {
                'total_nodes': 0,
                'online_nodes': 0,
                'offline_nodes': 0,
                'unstable_nodes': 0,
                'average_uptime': 0.0,
                'average_response_time': 0.0
            }

        status_counts = {
            'online': 0,
            'offline': 0,
            'unstable': 0,
            'unknown': 0
        }

        total_uptime = 0.0
        total_response_time = 0.0
        response_time_count = 0

        for health in all_health.values():
            status_counts[health.status.value] += 1
            total_uptime += health.uptime_percentage

            if health.average_response_time > 0:
                total_response_time += health.average_response_time
                response_time_count += 1

        return {
            'total_nodes': len(all_health),
            'online_nodes': status_counts['online'],
            'offline_nodes': status_counts['offline'],
            'unstable_nodes': status_counts['unstable'],
            'unknown_nodes': status_counts['unknown'],
            'average_uptime': total_uptime / len(all_health),
            'average_response_time': total_response_time / response_time_count if response_time_count > 0 else 0.0
        }

    def cleanup_old_data(self, max_age_days: int = 30):
        """
        Clean up old heartbeat data.

        Args:
            max_age_days: Maximum age of data to keep (days)
        """
        with self._lock:
            cutoff_time = datetime.now() - timedelta(days=max_age_days)

            for node_id, heartbeats in self._heartbeats.items():
                # Remove old heartbeats
                while heartbeats and heartbeats[0].timestamp < cutoff_time:
                    heartbeats.popleft()

                # Remove empty deques
                if not heartbeats:
                    del self._heartbeats[node_id]

            logger.debug(f"Cleaned up old health data (>{max_age_days} days)")

    def export_health_data(self, node_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Export health data for analysis or debugging.

        Args:
            node_id: Specific node ID, or None for all nodes

        Returns:
            Health data export
        """
        with self._lock:
            if node_id:
                heartbeats = self._heartbeats.get(node_id, [])
                health = self.get_health(node_id)

                return {
                    'node_id': node_id,
                    'health': health.__dict__ if health else None,
                    'heartbeats': [
                        {
                            'timestamp': hb.timestamp.isoformat(),
                            'response_time': hb.response_time,
                            'success': hb.success,
                            'error_message': hb.error_message
                        }
                        for hb in heartbeats
                    ]
                }
            else:
                # Export all nodes
                return {
                    'exported_at': datetime.now().isoformat(),
                    'nodes': {
                        node_id: self.export_health_data(node_id)
                        for node_id in self._heartbeats.keys()
                    },
                    'summary': self.get_health_summary()
                }