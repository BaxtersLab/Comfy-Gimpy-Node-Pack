"""
Remote ComfyUI Node Load Balancer.

Implements load balancing strategies for distributing tasks across
remote ComfyUI nodes including round-robin, weighted, and health-based balancing.
"""

import logging
import random
import time
import threading
from typing import List, Optional, Dict, Any, Callable
from enum import Enum
from dataclasses import dataclass

from ..shared.types import RemoteNode, NodeStatus
from .node_manager import get_node_manager

logger = logging.getLogger(__name__)


class LoadBalancingStrategy(Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_RANDOM = "weighted_random"
    LEAST_LOADED = "least_loaded"
    HEALTH_BASED = "health_based"
    RANDOM = "random"


@dataclass
class LoadBalancingResult:
    """Result of load balancing decision."""
    node_id: str
    node_url: str
    strategy_used: LoadBalancingStrategy
    reason: str
    score: Optional[float] = None


class LoadBalancer:
    """
    Load balancer for distributing tasks across remote ComfyUI nodes.

    Supports multiple load balancing strategies and automatic failover.
    """

    def __init__(self,
                 strategy: LoadBalancingStrategy = LoadBalancingStrategy.HEALTH_BASED,
                 enable_failover: bool = True,
                 max_retries: int = 3):
        """
        Initialize the load balancer.

        Args:
            strategy: Load balancing strategy to use
            enable_failover: Whether to enable automatic failover
            max_retries: Maximum number of retries for failed nodes
        """
        self.strategy = strategy
        self.enable_failover = enable_failover
        self.max_retries = max_retries

        # Round-robin state
        self._round_robin_index = 0
        self._lock = threading.RLock()

        # Node manager reference
        self._node_manager = get_node_manager()

    def select_node(self,
                   required_capabilities: Optional[Dict[str, Any]] = None,
                   preferred_node: Optional[str] = None,
                   exclude_nodes: Optional[List[str]] = None) -> Optional[LoadBalancingResult]:
        """
        Select a node for task execution using the configured strategy.

        Args:
            required_capabilities: Required node capabilities
            preferred_node: Preferred node ID (if available)
            exclude_nodes: List of node IDs to exclude

        Returns:
            Load balancing result or None if no suitable node found
        """
        with self._lock:
            # Get available nodes
            available_nodes = self._get_available_nodes(required_capabilities, exclude_nodes)

            if not available_nodes:
                logger.warning("No available nodes for task execution")
                return None

            # If preferred node is available and meets requirements, use it
            if preferred_node:
                preferred = next((node for node in available_nodes if node.id == preferred_node), None)
                if preferred:
                    return LoadBalancingResult(
                        node_id=preferred.id,
                        node_url=preferred.url,
                        strategy_used=self.strategy,
                        reason=f"Preferred node {preferred_node} selected",
                        score=1.0
                    )

            # Apply load balancing strategy
            if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
                return self._round_robin_select(available_nodes)
            elif self.strategy == LoadBalancingStrategy.WEIGHTED_RANDOM:
                return self._weighted_random_select(available_nodes)
            elif self.strategy == LoadBalancingStrategy.LEAST_LOADED:
                return self._least_loaded_select(available_nodes)
            elif self.strategy == LoadBalancingStrategy.HEALTH_BASED:
                return self._health_based_select(available_nodes)
            elif self.strategy == LoadBalancingStrategy.RANDOM:
                return self._random_select(available_nodes)
            else:
                logger.error(f"Unknown load balancing strategy: {self.strategy}")
                return self._random_select(available_nodes)

    def select_node_with_failover(self,
                                required_capabilities: Optional[Dict[str, Any]] = None,
                                preferred_node: Optional[str] = None,
                                exclude_nodes: Optional[List[str]] = None) -> Optional[LoadBalancingResult]:
        """
        Select a node with automatic failover support.

        Args:
            required_capabilities: Required node capabilities
            preferred_node: Preferred node ID
            exclude_nodes: Initial list of excluded nodes

        Returns:
            Load balancing result or None if no suitable node found after retries
        """
        if not self.enable_failover:
            return self.select_node(required_capabilities, preferred_node, exclude_nodes)

        excluded = list(exclude_nodes or [])
        failed_nodes = []

        for attempt in range(self.max_retries + 1):
            result = self.select_node(required_capabilities, preferred_node, excluded)

            if result:
                if attempt > 0:
                    logger.info(f"Selected node {result.node_id} on attempt {attempt + 1} "
                              f"(failed nodes: {failed_nodes})")
                return result

            # If no node found, try excluding previously failed nodes
            if failed_nodes:
                excluded.extend(failed_nodes)
                failed_nodes = []

            # Mark current preferred node as failed for next attempt
            if preferred_node and preferred_node not in excluded:
                excluded.append(preferred_node)
                failed_nodes.append(preferred_node)
                preferred_node = None

        logger.error(f"No suitable node found after {self.max_retries + 1} attempts")
        return None

    def _get_available_nodes(self,
                           required_capabilities: Optional[Dict[str, Any]] = None,
                           exclude_nodes: Optional[List[str]] = None) -> List[RemoteNode]:
        """
        Get list of available nodes that meet requirements.

        Args:
            required_capabilities: Required capabilities
            exclude_nodes: Nodes to exclude

        Returns:
            List of available nodes
        """
        all_nodes = self._node_manager.list_nodes()
        exclude_set = set(exclude_nodes or [])

        available = []

        for node in all_nodes:
            # Skip excluded nodes
            if node.id in exclude_set:
                continue

            # Skip offline/unstable nodes
            if node.status not in [NodeStatus.ONLINE]:
                continue

            # Check capabilities if required
            if required_capabilities and node.capabilities:
                if not self._check_capabilities(node.capabilities, required_capabilities):
                    continue

            available.append(node)

        return available

    def _check_capabilities(self,
                          capabilities: Any,
                          required: Dict[str, Any]) -> bool:
        """
        Check if node capabilities meet requirements.

        Args:
            capabilities: Node capabilities
            required: Required capabilities

        Returns:
            True if requirements are met
        """
        # Check VRAM
        min_vram = required.get('min_vram_gb')
        if min_vram and capabilities.vram_gb < min_vram:
            return False

        # Check required models
        required_models = required.get('required_models', [])
        if required_models:
            installed_models = {model.name for model in capabilities.installed_models}
            if not all(model in installed_models for model in required_models):
                return False

        # Check required workflows
        required_workflow = required.get('required_workflow')
        if required_workflow:
            supported_workflows = {wf.name for wf in capabilities.supported_workflows}
            if required_workflow not in supported_workflows:
                return False

        return True

    def _round_robin_select(self, nodes: List[RemoteNode]) -> Optional[LoadBalancingResult]:
        """Select node using round-robin strategy."""
        if not nodes:
            return None

        selected_node = nodes[self._round_robin_index % len(nodes)]
        self._round_robin_index = (self._round_robin_index + 1) % len(nodes)

        return LoadBalancingResult(
            node_id=selected_node.id,
            node_url=selected_node.url,
            strategy_used=LoadBalancingStrategy.ROUND_ROBIN,
            reason="Round-robin selection",
            score=None
        )

    def _weighted_random_select(self, nodes: List[RemoteNode]) -> Optional[LoadBalancingResult]:
        """Select node using weighted random strategy based on VRAM."""
        if not nodes:
            return None

        # Calculate weights based on VRAM
        weights = []
        for node in nodes:
            vram_weight = node.capabilities.vram_gb if node.capabilities else 1
            weights.append(max(vram_weight, 1))  # Minimum weight of 1

        # Weighted random selection
        total_weight = sum(weights)
        if total_weight == 0:
            return self._random_select(nodes)

        pick = random.uniform(0, total_weight)
        current_weight = 0

        for i, node in enumerate(nodes):
            current_weight += weights[i]
            if pick <= current_weight:
                return LoadBalancingResult(
                    node_id=node.id,
                    node_url=node.url,
                    strategy_used=LoadBalancingStrategy.WEIGHTED_RANDOM,
                    reason=f"Weighted random selection (VRAM: {node.capabilities.vram_gb if node.capabilities else 'unknown'}GB)",
                    score=weights[i] / total_weight
                )

        # Fallback
        return self._random_select(nodes)

    def _least_loaded_select(self, nodes: List[RemoteNode]) -> Optional[LoadBalancingResult]:
        """Select node using least loaded strategy (simplified)."""
        if not nodes:
            return None

        # For now, use random selection as we don't have load metrics
        # In a real implementation, this would check current task queues
        selected_node = random.choice(nodes)

        return LoadBalancingResult(
            node_id=selected_node.id,
            node_url=selected_node.url,
            strategy_used=LoadBalancingStrategy.LEAST_LOADED,
            reason="Least loaded selection (simplified)",
            score=None
        )

    def _health_based_select(self, nodes: List[RemoteNode]) -> Optional[LoadBalancingResult]:
        """Select node using health-based strategy."""
        if not nodes:
            return None

        # Get healthiest nodes from health monitor
        health_monitor = self._node_manager.health_monitor
        healthiest_node_ids = health_monitor.get_healthiest_nodes(limit=len(nodes))

        if not healthiest_node_ids:
            return self._random_select(nodes)

        # Find the healthiest available node
        for node_id in healthiest_node_ids:
            node = next((n for n in nodes if n.id == node_id), None)
            if node:
                health = health_monitor.get_health(node_id)
                score = health.uptime_percentage / 100.0 if health else 0.5

                return LoadBalancingResult(
                    node_id=node.id,
                    node_url=node.url,
                    strategy_used=LoadBalancingStrategy.HEALTH_BASED,
                    reason=f"Health-based selection (uptime: {health.uptime_percentage:.1f}%)" if health else "Health-based selection",
                    score=score
                )

        # Fallback
        return self._random_select(nodes)

    def _random_select(self, nodes: List[RemoteNode]) -> Optional[LoadBalancingResult]:
        """Select node randomly."""
        if not nodes:
            return None

        selected_node = random.choice(nodes)

        return LoadBalancingResult(
            node_id=selected_node.id,
            node_url=selected_node.url,
            strategy_used=LoadBalancingStrategy.RANDOM,
            reason="Random selection",
            score=1.0 / len(nodes)
        )

    def set_strategy(self, strategy: LoadBalancingStrategy):
        """
        Change the load balancing strategy.

        Args:
            strategy: New strategy to use
        """
        with self._lock:
            self.strategy = strategy
            logger.info(f"Load balancing strategy changed to: {strategy.value}")

    def get_strategy(self) -> LoadBalancingStrategy:
        """Get the current load balancing strategy."""
        return self.strategy

    def get_load_distribution(self) -> Dict[str, Any]:
        """
        Get current load distribution statistics.

        Returns:
            Load distribution information
        """
        nodes = self._node_manager.list_nodes()
        online_nodes = [node for node in nodes if node.status == NodeStatus.ONLINE]

        return {
            'total_nodes': len(nodes),
            'online_nodes': len(online_nodes),
            'strategy': self.strategy.value,
            'enable_failover': self.enable_failover,
            'max_retries': self.max_retries,
            'nodes': [
                {
                    'id': node.id,
                    'name': node.name,
                    'status': node.status.value,
                    'vram_gb': node.capabilities.vram_gb if node.capabilities else 0,
                    'url': node.url
                }
                for node in online_nodes
            ]
        }


# Global load balancer instance
_load_balancer: Optional[LoadBalancer] = None


def initialize_load_balancer(strategy: LoadBalancingStrategy = LoadBalancingStrategy.HEALTH_BASED,
                           enable_failover: bool = True,
                           max_retries: int = 3) -> LoadBalancer:
    """Initialize the global load balancer."""
    global _load_balancer
    if _load_balancer is None:
        _load_balancer = LoadBalancer(strategy, enable_failover, max_retries)
    return _load_balancer


def get_load_balancer() -> LoadBalancer:
    """Get the global load balancer instance."""
    if _load_balancer is None:
        raise RuntimeError("Load balancer not initialized")
    return _load_balancer