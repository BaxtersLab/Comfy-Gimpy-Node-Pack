"""
Comfy Gimpy Studio - Phase 10: Advanced Workflow Optimization
Module for intelligent performance tuning and distributed execution.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from .engine import (
    WorkflowOptimizer,
    DistributedExecutionManager,
    initialize_optimization_system,
    get_optimizer,
    get_distributed_manager
)

from .tuner import (
    PerformanceTuner,
    initialize_performance_tuner,
    get_performance_tuner,
    shutdown_performance_tuner
)

from .coordinator import (
    DistributedCoordinator,
    initialize_distributed_coordinator,
    shutdown_distributed_coordinator,
    get_distributed_coordinator
)

logger = logging.getLogger(__name__)

# Global initialization flag
_optimization_initialized = False

async def initialize_phase10_system() -> bool:
    """Initialize the complete Phase 10 optimization system."""
    global _optimization_initialized

    if _optimization_initialized:
        logger.info("Phase 10 optimization system already initialized")
        return True

    try:
        # Initialize core optimization system
        if not initialize_optimization_system():
            logger.error("Failed to initialize optimization system")
            return False

        # Initialize performance tuner
        if not initialize_performance_tuner():
            logger.error("Failed to initialize performance tuner")
            return False

        # Initialize distributed coordinator
        if not await initialize_distributed_coordinator():
            logger.error("Failed to initialize distributed coordinator")
            return False

        _optimization_initialized = True
        logger.info("Phase 10 optimization system fully initialized")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize Phase 10 system: {e}")
        return False

async def shutdown_phase10_system():
    """Shutdown the Phase 10 optimization system."""
    global _optimization_initialized

    try:
        await shutdown_distributed_coordinator()
        shutdown_performance_tuner()
        _optimization_initialized = False
        logger.info("Phase 10 optimization system shutdown")
    except Exception as e:
        logger.error(f"Error during Phase 10 shutdown: {e}")

def get_system_status() -> Dict[str, Any]:
    """Get comprehensive system status."""
    status = {
        "phase10_initialized": _optimization_initialized,
        "components": {}
    }

    try:
        if _optimization_initialized:
            # Get optimizer status
            optimizer = get_optimizer()
            status["components"]["optimizer"] = {
                "profiles_count": len(optimizer.profiles),
                "cache_entries": len(optimizer.cache),
                "cache_size_limit": optimizer.max_cache_size
            }

            # Get distributed manager status
            dist_manager = get_distributed_manager()
            status["components"]["distributed_manager"] = dist_manager.get_cluster_status()

            # Get performance tuner status
            tuner = get_performance_tuner()
            status["components"]["performance_tuner"] = tuner.get_performance_report()

            # Get coordinator status
            coordinator = get_distributed_coordinator()
            status["components"]["coordinator"] = coordinator.get_cluster_status()

        status["overall_health"] = "healthy" if _optimization_initialized else "not_initialized"

    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        status["overall_health"] = "error"
        status["error"] = str(e)

    return status

def get_optimization_report() -> Dict[str, Any]:
    """Get comprehensive optimization report."""
    if not _optimization_initialized:
        return {"error": "Phase 10 system not initialized"}

    try:
        optimizer = get_optimizer()
        tuner = get_performance_tuner()
        coordinator = get_distributed_coordinator()

        return {
            "workflow_optimization": optimizer.get_optimization_report(),
            "performance_metrics": tuner.get_performance_report(),
            "distributed_execution": coordinator.get_cluster_status(),
            "system_insights": _generate_system_insights()
        }

    except Exception as e:
        logger.error(f"Error generating optimization report: {e}")
        return {"error": str(e)}

def _generate_system_insights() -> List[str]:
    """Generate system-wide optimization insights."""
    insights = []

    try:
        if not _optimization_initialized:
            return ["Phase 10 system not initialized"]

        optimizer = get_optimizer()
        tuner = get_performance_tuner()
        coordinator = get_distributed_coordinator()

        # Workflow insights
        opt_report = optimizer.get_optimization_report()
        if opt_report.get('workflow_profiles', 0) == 0:
            insights.append("No workflow profiles available - run more executions to enable optimization")

        # Performance insights
        perf_report = tuner.get_performance_report()
        perf_score = perf_report.get('performance_score', 0)
        if perf_score < 50:
            insights.append("System performance is degraded - consider resource optimization")
        elif perf_score > 80:
            insights.append("System performance is excellent")

        # Distributed insights
        cluster_status = coordinator.get_cluster_status()
        online_nodes = cluster_status.get('online_nodes', 0)
        total_nodes = cluster_status.get('total_nodes', 0)

        if total_nodes == 0:
            insights.append("No execution nodes configured")
        elif online_nodes < total_nodes:
            insights.append(f"{total_nodes - online_nodes} execution nodes are offline")

        if online_nodes > 1:
            insights.append("Distributed execution is active - consider load balancing optimization")

        # Cache insights
        cache_entries = opt_report.get('cache_entries', 0)
        if cache_entries > 100:
            insights.append("Large cache size detected - consider cache optimization")

    except Exception as e:
        insights.append(f"Error generating insights: {e}")

    if not insights:
        insights.append("System is running optimally")

    return insights

# Convenience functions for common operations
async def optimize_workflow_execution(workflow_data: Dict[str, Any],
                                   options: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute workflow with full optimization."""
    if not _optimization_initialized:
        raise RuntimeError("Phase 10 system not initialized")

    coordinator = get_distributed_coordinator()
    return await coordinator.execute_workflow_distributed(workflow_data, options)

def get_workflow_optimization_suggestions(workflow_hash: str) -> Dict[str, Any]:
    """Get optimization suggestions for a workflow."""
    if not _optimization_initialized:
        return {"error": "Phase 10 system not initialized"}

    optimizer = get_optimizer()
    return optimizer.get_optimization_suggestions(workflow_hash)

def add_execution_node(host: str, port: int, priority: int = 1, max_concurrent: int = 4):
    """Add an execution node to the distributed cluster."""
    if not _optimization_initialized:
        raise RuntimeError("Phase 10 system not initialized")

    coordinator = get_distributed_coordinator()
    coordinator.add_node(host, port, priority, max_concurrent)

def get_performance_metrics() -> Dict[str, Any]:
    """Get current performance metrics."""
    if not _optimization_initialized:
        return {"error": "Phase 10 system not initialized"}

    tuner = get_performance_tuner()
    return tuner.get_performance_report()

__all__ = [
    # Core components
    'WorkflowOptimizer',
    'DistributedExecutionManager',
    'PerformanceTuner',
    'DistributedCoordinator',

    # Initialization functions
    'initialize_phase10_system',
    'shutdown_phase10_system',

    # Status and reporting
    'get_system_status',
    'get_optimization_report',

    # Convenience functions
    'optimize_workflow_execution',
    'get_workflow_optimization_suggestions',
    'add_execution_node',
    'get_performance_metrics',

    # Individual component access
    'get_optimizer',
    'get_distributed_manager',
    'get_performance_tuner',
    'get_distributed_coordinator'
]