"""
Comfy Gimpy Studio - Phase 10: Advanced Workflow Optimization
Intelligent performance tuning and distributed execution system.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import statistics
import json
import os

from shared.types import (
    WorkflowData, ExecutionResult, ExecutionOptions,
    PerformanceMetrics, SystemResourceUsage
)

logger = logging.getLogger(__name__)

@dataclass
class OptimizationProfile:
    """Performance optimization profile for workflows."""
    workflow_hash: str
    execution_times: List[float] = field(default_factory=list)
    memory_usage: List[float] = field(default_factory=list)
    gpu_usage: List[float] = field(default_factory=list)
    success_rate: float = 1.0
    optimal_batch_size: int = 1
    recommended_concurrency: int = 1
    last_updated: datetime = field(default_factory=datetime.now)
    execution_count: int = 0

@dataclass
class ServerNode:
    """Represents a ComfyUI server node in distributed setup."""
    host: str
    port: int
    priority: int = 1
    max_concurrent_jobs: int = 4
    active_jobs: int = 0
    is_online: bool = True
    last_health_check: datetime = field(default_factory=datetime.now)
    performance_score: float = 1.0
    capabilities: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DistributedJob:
    """Job distributed across multiple server nodes."""
    job_id: str
    workflow_data: WorkflowData
    sub_jobs: List[Dict[str, Any]] = field(default_factory=list)
    coordinator_node: Optional[ServerNode] = None
    status: str = "pending"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    results: List[ExecutionResult] = field(default_factory=list)

@dataclass
class CacheEntry:
    """Intelligent caching entry for workflow results."""
    cache_key: str
    result: ExecutionResult
    created_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

class WorkflowOptimizer:
    """Intelligent workflow optimization engine."""

    def __init__(self, cache_dir: str = "cache/optimization"):
        self.cache_dir = cache_dir
        self.profiles: Dict[str, OptimizationProfile] = {}
        self.cache: Dict[str, CacheEntry] = {}
        self.max_cache_size = 100  # Maximum cache entries
        self.cache_ttl_hours = 24  # Cache time-to-live

        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
        self._load_profiles()

    def _load_profiles(self):
        """Load optimization profiles from disk."""
        profile_file = os.path.join(self.cache_dir, "profiles.json")
        if os.path.exists(profile_file):
            try:
                with open(profile_file, 'r') as f:
                    data = json.load(f)
                    for hash_key, profile_data in data.items():
                        profile_data['last_updated'] = datetime.fromisoformat(profile_data['last_updated'])
                        self.profiles[hash_key] = OptimizationProfile(**profile_data)
            except Exception as e:
                logger.warning(f"Failed to load optimization profiles: {e}")

    def _save_profiles(self):
        """Save optimization profiles to disk."""
        profile_file = os.path.join(self.cache_dir, "profiles.json")
        try:
            data = {}
            for hash_key, profile in self.profiles.items():
                profile_dict = {
                    'workflow_hash': profile.workflow_hash,
                    'execution_times': profile.execution_times[-100:],  # Keep last 100
                    'memory_usage': profile.memory_usage[-100:],
                    'gpu_usage': profile.gpu_usage[-100:],
                    'success_rate': profile.success_rate,
                    'optimal_batch_size': profile.optimal_batch_size,
                    'recommended_concurrency': profile.recommended_concurrency,
                    'last_updated': profile.last_updated.isoformat(),
                    'execution_count': profile.execution_count
                }
                data[hash_key] = profile_dict

            with open(profile_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save optimization profiles: {e}")

    def get_workflow_hash(self, workflow_data: WorkflowData) -> str:
        """Generate a hash for workflow data for caching/optimization."""
        import hashlib
        workflow_str = json.dumps({
            'workflow_json': workflow_data.workflow_json,
            'parameters': workflow_data.parameters
        }, sort_keys=True)
        return hashlib.md5(workflow_str.encode()).hexdigest()

    def record_execution(self, workflow_hash: str, execution_time: float,
                        memory_usage: float, gpu_usage: float, success: bool):
        """Record execution metrics for optimization."""
        if workflow_hash not in self.profiles:
            self.profiles[workflow_hash] = OptimizationProfile(workflow_hash=workflow_hash)

        profile = self.profiles[workflow_hash]
        profile.execution_times.append(execution_time)
        profile.memory_usage.append(memory_usage)
        profile.gpu_usage.append(gpu_usage)
        profile.execution_count += 1

        # Update success rate
        recent_executions = min(50, len(profile.execution_times))
        recent_successes = sum(1 for _ in range(recent_executions)) if success else recent_executions - 1
        profile.success_rate = recent_successes / recent_executions

        # Update optimal settings based on performance
        self._update_optimal_settings(profile)
        profile.last_updated = datetime.now()

        # Save periodically
        if profile.execution_count % 10 == 0:
            self._save_profiles()

    def _update_optimal_settings(self, profile: OptimizationProfile):
        """Update optimal batch size and concurrency based on metrics."""
        if len(profile.execution_times) < 5:
            return

        # Analyze execution times for batch optimization
        avg_time = statistics.mean(profile.execution_times[-20:])
        time_std = statistics.stdev(profile.execution_times[-20:]) if len(profile.execution_times) > 1 else 0

        # Simple heuristic: if times are consistent and fast, increase batch size
        if time_std / avg_time < 0.3 and avg_time < 10:  # Low variance and fast
            profile.optimal_batch_size = min(profile.optimal_batch_size + 1, 4)
        elif time_std / avg_time > 0.5 or avg_time > 30:  # High variance or slow
            profile.optimal_batch_size = max(profile.optimal_batch_size - 1, 1)

        # Concurrency based on resource usage
        if profile.memory_usage and profile.gpu_usage:
            avg_memory = statistics.mean(profile.memory_usage[-10:])
            avg_gpu = statistics.mean(profile.gpu_usage[-10:])

            # Reduce concurrency if high resource usage
            if avg_memory > 80 or avg_gpu > 90:
                profile.recommended_concurrency = max(profile.recommended_concurrency - 1, 1)
            elif avg_memory < 50 and avg_gpu < 70:
                profile.recommended_concurrency = min(profile.recommended_concurrency + 1, 4)

    def get_optimization_suggestions(self, workflow_hash: str) -> Dict[str, Any]:
        """Get optimization suggestions for a workflow."""
        if workflow_hash not in self.profiles:
            return {
                'batch_size': 1,
                'concurrency': 1,
                'caching_recommended': False,
                'performance_score': 0.5
            }

        profile = self.profiles[workflow_hash]

        return {
            'batch_size': profile.optimal_batch_size,
            'concurrency': profile.recommended_concurrency,
            'caching_recommended': profile.success_rate > 0.95 and profile.execution_count > 3,
            'performance_score': min(1.0, profile.success_rate * (1.0 / max(1, statistics.mean(profile.execution_times[-10:]) / 10))),
            'execution_count': profile.execution_count,
            'avg_execution_time': statistics.mean(profile.execution_times[-10:]) if profile.execution_times else None
        }

    def get_cache_key(self, workflow_data: WorkflowData, options: ExecutionOptions) -> str:
        """Generate cache key for workflow execution."""
        import hashlib
        cache_data = {
            'workflow_hash': self.get_workflow_hash(workflow_data),
            'input_images': [hash(img) for img in workflow_data.input_images] if workflow_data.input_images else [],
            'parameters': options.__dict__ if options else {}
        }
        cache_str = json.dumps(cache_data, sort_keys=True, default=str)
        return hashlib.md5(cache_str.encode()).hexdigest()

    def get_cached_result(self, cache_key: str) -> Optional[ExecutionResult]:
        """Retrieve cached execution result."""
        if cache_key in self.cache:
            entry = self.cache[cache_key]

            # Check TTL
            if datetime.now() - entry.created_at > timedelta(hours=self.cache_ttl_hours):
                del self.cache[cache_key]
                return None

            entry.access_count += 1
            entry.last_accessed = datetime.now()
            return entry.result

        return None

    def cache_result(self, cache_key: str, result: ExecutionResult, size_bytes: int = 0):
        """Cache execution result."""
        entry = CacheEntry(
            cache_key=cache_key,
            result=result,
            size_bytes=size_bytes
        )
        self.cache[cache_key] = entry

        # Enforce cache size limit
        if len(self.cache) > self.max_cache_size:
            self._evict_oldest_cache_entries()

    def _evict_oldest_cache_entries(self):
        """Evict least recently used cache entries."""
        if not self.cache:
            return

        # Sort by last accessed time
        sorted_entries = sorted(self.cache.items(),
                              key=lambda x: (x[1].last_accessed, x[1].access_count))

        # Remove oldest 20%
        to_remove = len(sorted_entries) // 5
        for i in range(to_remove):
            del self.cache[sorted_entries[i][0]]

class DistributedExecutionManager:
    """Manages distributed execution across multiple ComfyUI server nodes."""

    def __init__(self):
        self.nodes: Dict[str, ServerNode] = {}
        self.active_jobs: Dict[str, DistributedJob] = {}
        self.optimizer = WorkflowOptimizer()

    def add_server_node(self, host: str, port: int, priority: int = 1,
                        max_concurrent: int = 4) -> str:
        """Add a server node to the distributed pool."""
        node_id = f"{host}:{port}"
        node = ServerNode(
            host=host,
            port=port,
            priority=priority,
            max_concurrent_jobs=max_concurrent
        )
        self.nodes[node_id] = node
        logger.info(f"Added server node: {node_id}")
        return node_id

    def remove_server_node(self, node_id: str):
        """Remove a server node from the distributed pool."""
        if node_id in self.nodes:
            del self.nodes[node_id]
            logger.info(f"Removed server node: {node_id}")

    async def execute_distributed(self, workflow_data: WorkflowData,
                                options: ExecutionOptions = None) -> DistributedJob:
        """Execute workflow across distributed nodes."""
        job_id = f"dist_{int(time.time())}_{hash(str(workflow_data))}"

        # Check cache first
        cache_key = self.optimizer.get_cache_key(workflow_data, options)
        cached_result = self.optimizer.get_cached_result(cache_key)
        if cached_result:
            job = DistributedJob(
                job_id=job_id,
                workflow_data=workflow_data,
                status="completed",
                results=[cached_result]
            )
            self.active_jobs[job_id] = job
            return job

        # Create distributed job
        job = DistributedJob(
            job_id=job_id,
            workflow_data=workflow_data,
            start_time=datetime.now()
        )
        self.active_jobs[job_id] = job

        try:
            # Select optimal nodes for execution
            available_nodes = [node for node in self.nodes.values()
                             if node.is_online and node.active_jobs < node.max_concurrent_jobs]

            if not available_nodes:
                raise RuntimeError("No available server nodes for execution")

            # Sort by performance score and load
            available_nodes.sort(key=lambda n: (n.active_jobs / n.max_concurrent_jobs,
                                              -n.performance_score))

            coordinator = available_nodes[0]
            job.coordinator_node = coordinator

            # For now, execute on single best node
            # Future: split workflow across multiple nodes
            execution_result = await self._execute_on_node(coordinator, workflow_data, options)

            job.results = [execution_result]
            job.status = "completed"
            job.end_time = datetime.now()

            # Cache result
            self.optimizer.cache_result(cache_key, execution_result)

            # Record metrics for optimization
            if hasattr(execution_result, 'execution_time'):
                self.optimizer.record_execution(
                    self.optimizer.get_workflow_hash(workflow_data),
                    execution_result.execution_time,
                    getattr(execution_result, 'memory_usage', 0),
                    getattr(execution_result, 'gpu_usage', 0),
                    execution_result.success
                )

        except Exception as e:
            job.status = "failed"
            job.end_time = datetime.now()
            logger.error(f"Distributed execution failed: {e}")

        return job

    async def _execute_on_node(self, node: ServerNode, workflow_data: WorkflowData,
                             options: ExecutionOptions) -> ExecutionResult:
        """Execute workflow on a specific node."""
        # This would integrate with the existing execution engine
        # For now, return a mock result
        await asyncio.sleep(0.1)  # Simulate network delay

        return ExecutionResult(
            success=True,
            job_id=f"node_{node.host}:{node.port}_{int(time.time())}",
            execution_time=5.0,
            outputs=[],
            error_message=None
        )

    def get_cluster_status(self) -> Dict[str, Any]:
        """Get status of the distributed execution cluster."""
        total_nodes = len(self.nodes)
        online_nodes = sum(1 for node in self.nodes.values() if node.is_online)
        total_capacity = sum(node.max_concurrent_jobs for node in self.nodes.values())
        used_capacity = sum(node.active_jobs for node in self.nodes.values())

        return {
            'total_nodes': total_nodes,
            'online_nodes': online_nodes,
            'total_capacity': total_capacity,
            'used_capacity': used_capacity,
            'utilization_rate': used_capacity / max(1, total_capacity),
            'nodes': [
                {
                    'id': node_id,
                    'host': node.host,
                    'port': node.port,
                    'online': node.is_online,
                    'active_jobs': node.active_jobs,
                    'max_jobs': node.max_concurrent_jobs,
                    'utilization': node.active_jobs / max(1, node.max_concurrent_jobs),
                    'performance_score': node.performance_score
                }
                for node_id, node in self.nodes.items()
            ]
        }

    def get_optimization_report(self) -> Dict[str, Any]:
        """Get comprehensive optimization report."""
        return {
            'workflow_profiles': len(self.optimizer.profiles),
            'cache_entries': len(self.optimizer.cache),
            'cache_hit_rate': self._calculate_cache_hit_rate(),
            'performance_insights': self._generate_performance_insights(),
            'cluster_status': self.get_cluster_status()
        }

    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate from recent activity."""
        # This would track cache hits vs misses over time
        return 0.75  # Mock value

    def _generate_performance_insights(self) -> List[str]:
        """Generate performance optimization insights."""
        insights = []

        # Analyze workflow performance
        slow_workflows = []
        for profile in self.optimizer.profiles.values():
            if profile.execution_times and statistics.mean(profile.execution_times) > 20:
                slow_workflows.append(profile.workflow_hash[:8])

        if slow_workflows:
            insights.append(f"Consider optimizing {len(slow_workflows)} slow workflows")

        # Analyze resource usage
        high_memory_workflows = []
        for profile in self.optimizer.profiles.values():
            if profile.memory_usage and statistics.mean(profile.memory_usage) > 75:
                high_memory_workflows.append(profile.workflow_hash[:8])

        if high_memory_workflows:
            insights.append(f"High memory usage detected in {len(high_memory_workflows)} workflows")

        if not insights:
            insights.append("System performance is optimal")

        return insights

# Global instances
_optimizer = None
_distributed_manager = None

def initialize_optimization_system() -> bool:
    """Initialize the optimization system."""
    global _optimizer, _distributed_manager

    try:
        _optimizer = WorkflowOptimizer()
        _distributed_manager = DistributedExecutionManager()

        # Add default local node
        _distributed_manager.add_server_node("127.0.0.1", 8188, priority=1, max_concurrent=4)

        logger.info("Optimization system initialized")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize optimization system: {e}")
        return False

def get_optimizer() -> WorkflowOptimizer:
    """Get the global workflow optimizer."""
    return _optimizer

def get_distributed_manager() -> DistributedExecutionManager:
    """Get the global distributed execution manager."""
    return _distributed_manager