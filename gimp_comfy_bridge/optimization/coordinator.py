"""
Comfy Gimpy Studio - Phase 10: Distributed Coordinator
Multi-server coordination and load balancing for distributed execution.
"""

import asyncio
import logging
import aiohttp
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import time

from .engine import ServerNode, DistributedJob

logger = logging.getLogger(__name__)

@dataclass
class LoadBalancingStrategy:
    """Load balancing strategy configuration."""
    name: str
    weight_cpu: float = 1.0
    weight_memory: float = 1.0
    weight_gpu: float = 1.0
    weight_latency: float = 1.0
    priority_preference: bool = True

@dataclass
class NodeHealthStatus:
    """Health status of a server node."""
    node_id: str
    is_online: bool
    last_check: datetime
    response_time_ms: float
    error_message: Optional[str] = None
    system_load: Dict[str, float] = field(default_factory=dict)

class DistributedCoordinator:
    """Coordinates distributed execution across multiple ComfyUI servers."""

    def __init__(self):
        self.nodes: Dict[str, ServerNode] = {}
        self.health_status: Dict[str, NodeHealthStatus] = {}
        self.load_balancing_strategy = LoadBalancingStrategy("weighted_performance")
        self.health_check_interval = 30  # seconds
        self.max_retry_attempts = 3
        self.session_timeout = aiohttp.ClientTimeout(total=30)

        # Start health monitoring
        self._health_monitor_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the distributed coordinator."""
        self._health_monitor_task = asyncio.create_task(self._health_monitoring_loop())
        logger.info("Distributed coordinator started")

    async def stop(self):
        """Stop the distributed coordinator."""
        if self._health_monitor_task:
            self._health_monitor_task.cancel()
            try:
                await self._health_monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Distributed coordinator stopped")

    def add_node(self, host: str, port: int, priority: int = 1,
                 max_concurrent: int = 4, capabilities: Dict[str, Any] = None) -> str:
        """Add a server node to the cluster."""
        node_id = f"{host}:{port}"
        node = ServerNode(
            host=host,
            port=port,
            priority=priority,
            max_concurrent_jobs=max_concurrent,
            capabilities=capabilities or {}
        )
        self.nodes[node_id] = node
        logger.info(f"Added node {node_id} to cluster")
        return node_id

    def remove_node(self, node_id: str):
        """Remove a server node from the cluster."""
        if node_id in self.nodes:
            del self.nodes[node_id]
            if node_id in self.health_status:
                del self.health_status[node_id]
            logger.info(f"Removed node {node_id} from cluster")

    async def execute_workflow_distributed(self, workflow_data: Dict[str, Any],
                                         options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute workflow using distributed nodes."""
        options = options or {}

        # Select optimal node
        selected_node = await self._select_optimal_node(workflow_data, options)
        if not selected_node:
            raise RuntimeError("No available nodes for execution")

        # Execute on selected node
        result = await self._execute_on_node(selected_node, workflow_data, options)

        # Update node load
        selected_node.active_jobs += 1

        # Return result with node info
        result['executed_on'] = {
            'node_id': f"{selected_node.host}:{selected_node.port}",
            'host': selected_node.host,
            'port': selected_node.port
        }

        return result

    async def _select_optimal_node(self, workflow_data: Dict[str, Any],
                                 options: Dict[str, Any]) -> Optional[ServerNode]:
        """Select the optimal node for execution based on load balancing strategy."""
        available_nodes = []

        for node_id, node in self.nodes.items():
            health = self.health_status.get(node_id)
            if (node.is_online and
                health and health.is_online and
                node.active_jobs < node.max_concurrent_jobs):
                available_nodes.append((node, health))

        if not available_nodes:
            return None

        # Apply load balancing strategy
        if self.load_balancing_strategy.name == "round_robin":
            # Simple round-robin (would need to track last used)
            return available_nodes[0][0]
        elif self.load_balancing_strategy.name == "weighted_performance":
            return self._select_weighted_performance(available_nodes)
        elif self.load_balancing_strategy.name == "least_loaded":
            return min(available_nodes,
                      key=lambda x: x[0].active_jobs / max(1, x[0].max_concurrent_jobs))[0]
        else:
            # Default to first available
            return available_nodes[0][0]

    def _select_weighted_performance(self, node_health_pairs: List[Tuple[ServerNode, NodeHealthStatus]]) -> ServerNode:
        """Select node based on weighted performance metrics."""
        best_node = None
        best_score = float('-inf')

        for node, health in node_health_pairs:
            # Calculate load factor (0-1, lower is better)
            load_factor = node.active_jobs / max(1, node.max_concurrent_jobs)

            # Calculate performance score
            cpu_load = health.system_load.get('cpu_percent', 50) / 100
            memory_load = health.system_load.get('memory_percent', 50) / 100
            gpu_load = health.system_load.get('gpu_utilization', 50) / 100

            # Weighted score (higher is better)
            performance_score = (
                self.load_balancing_strategy.weight_cpu * (1 - cpu_load) +
                self.load_balancing_strategy.weight_memory * (1 - memory_load) +
                self.load_balancing_strategy.weight_gpu * (1 - gpu_load) +
                self.load_balancing_strategy.weight_latency * (1 / max(0.1, health.response_time_ms / 1000))
            )

            # Factor in priority
            if self.load_balancing_strategy.priority_preference:
                performance_score *= node.priority

            # Combine with load factor (prefer less loaded nodes)
            final_score = performance_score * (1 - load_factor * 0.5)

            if final_score > best_score:
                best_score = final_score
                best_node = node

        return best_node

    async def _execute_on_node(self, node: ServerNode, workflow_data: Dict[str, Any],
                             options: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow on a specific node."""
        url = f"http://{node.host}:{node.port}/prompt"

        # Prepare request data
        request_data = {
            "prompt": workflow_data,
            "client_id": f"comfy_gimpy_{int(time.time())}"
        }

        # Add execution options
        if options:
            request_data.update(options)

        async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
            for attempt in range(self.max_retry_attempts):
                try:
                    start_time = time.time()
                    async with session.post(url, json=request_data) as response:
                        response_time = time.time() - start_time

                        if response.status == 200:
                            result = await response.json()

                            # Update node performance score
                            node.performance_score = 0.9 * node.performance_score + 0.1 * (1.0 / response_time)

                            return {
                                "success": True,
                                "prompt_id": result.get("prompt_id"),
                                "execution_time": response_time,
                                "node_response": result
                            }
                        else:
                            error_text = await response.text()
                            logger.warning(f"Node {node.host}:{node.port} returned status {response.status}: {error_text}")

                            if attempt == self.max_retry_attempts - 1:
                                return {
                                    "success": False,
                                    "error": f"HTTP {response.status}: {error_text}",
                                    "execution_time": response_time
                                }

                except asyncio.TimeoutError:
                    logger.warning(f"Timeout executing on node {node.host}:{node.port} (attempt {attempt + 1})")
                    if attempt == self.max_retry_attempts - 1:
                        return {
                            "success": False,
                            "error": "Timeout",
                            "execution_time": self.session_timeout.total
                        }

                except Exception as e:
                    logger.error(f"Error executing on node {node.host}:{node.port}: {e}")
                    if attempt == self.max_retry_attempts - 1:
                        return {
                            "success": False,
                            "error": str(e),
                            "execution_time": time.time() - start_time if 'start_time' in locals() else 0
                        }

                # Wait before retry
                await asyncio.sleep(1 * (attempt + 1))

        return {"success": False, "error": "Max retries exceeded"}

    async def _health_monitoring_loop(self):
        """Continuously monitor node health."""
        while True:
            try:
                await self._check_all_nodes_health()
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")

            await asyncio.sleep(self.health_check_interval)

    async def _check_all_nodes_health(self):
        """Check health of all nodes."""
        tasks = []
        for node_id, node in self.nodes.items():
            tasks.append(self._check_node_health(node_id, node))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _check_node_health(self, node_id: str, node: ServerNode):
        """Check health of a specific node."""
        url = f"http://{node.host}:{node.port}/system_stats"

        start_time = time.time()
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(url) as response:
                    response_time = (time.time() - start_time) * 1000

                    if response.status == 200:
                        system_stats = await response.json()

                        health_status = NodeHealthStatus(
                            node_id=node_id,
                            is_online=True,
                            last_check=datetime.now(),
                            response_time_ms=response_time,
                            system_load=system_stats
                        )

                        # Update node online status
                        node.is_online = True
                        node.last_health_check = datetime.now()

                    else:
                        health_status = NodeHealthStatus(
                            node_id=node_id,
                            is_online=False,
                            last_check=datetime.now(),
                            response_time_ms=response_time,
                            error_message=f"HTTP {response.status}"
                        )
                        node.is_online = False

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            health_status = NodeHealthStatus(
                node_id=node_id,
                is_online=False,
                last_check=datetime.now(),
                response_time_ms=response_time,
                error_message=str(e)
            )
            node.is_online = False

        self.health_status[node_id] = health_status

    def get_cluster_status(self) -> Dict[str, Any]:
        """Get comprehensive cluster status."""
        nodes_status = []

        for node_id, node in self.nodes.items():
            health = self.health_status.get(node_id)
            nodes_status.append({
                "node_id": node_id,
                "host": node.host,
                "port": node.port,
                "online": node.is_online,
                "active_jobs": node.active_jobs,
                "max_jobs": node.max_concurrent_jobs,
                "utilization": node.active_jobs / max(1, node.max_concurrent_jobs),
                "performance_score": node.performance_score,
                "last_health_check": node.last_health_check.isoformat() if node.last_health_check else None,
                "health_response_time": health.response_time_ms if health else None,
                "system_load": health.system_load if health else {},
                "capabilities": node.capabilities
            })

        total_nodes = len(self.nodes)
        online_nodes = sum(1 for node in self.nodes.values() if node.is_online)
        total_capacity = sum(node.max_concurrent_jobs for node in self.nodes.values())
        used_capacity = sum(node.active_jobs for node in self.nodes.values())

        return {
            "total_nodes": total_nodes,
            "online_nodes": online_nodes,
            "offline_nodes": total_nodes - online_nodes,
            "total_capacity": total_capacity,
            "used_capacity": used_capacity,
            "utilization_rate": used_capacity / max(1, total_capacity),
            "load_balancing_strategy": self.load_balancing_strategy.name,
            "nodes": nodes_status
        }

    def set_load_balancing_strategy(self, strategy: LoadBalancingStrategy):
        """Set the load balancing strategy."""
        self.load_balancing_strategy = strategy
        logger.info(f"Load balancing strategy set to: {strategy.name}")

    async def failover_node(self, failed_node_id: str) -> bool:
        """Handle failover for a failed node."""
        if failed_node_id not in self.nodes:
            return False

        failed_node = self.nodes[failed_node_id]
        failed_node.is_online = False

        # Find alternative nodes and redistribute load
        # This is a simplified implementation
        available_nodes = [node for node in self.nodes.values()
                          if node.is_online and node != failed_node]

        if available_nodes:
            # Could implement job redistribution logic here
            logger.info(f"Failover initiated for node {failed_node_id}")
            return True

        logger.error(f"No available nodes for failover of {failed_node_id}")
        return False

# Global instance
_coordinator = None

async def initialize_distributed_coordinator() -> bool:
    """Initialize the distributed coordinator."""
    global _coordinator

    try:
        _coordinator = DistributedCoordinator()
        await _coordinator.start()

        # Add default local node
        _coordinator.add_node("127.0.0.1", 8188, priority=1, max_concurrent=4)

        logger.info("Distributed coordinator initialized")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize distributed coordinator: {e}")
        return False

async def shutdown_distributed_coordinator():
    """Shutdown the distributed coordinator."""
    global _coordinator
    if _coordinator:
        await _coordinator.stop()
        _coordinator = None

def get_distributed_coordinator() -> DistributedCoordinator:
    """Get the global distributed coordinator."""
    return _coordinator