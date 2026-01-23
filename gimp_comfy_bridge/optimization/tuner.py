"""
Comfy Gimpy Studio - Phase 10: Performance Tuning
Intelligent performance optimization and resource management.
"""

import asyncio
import logging
import psutil
import GPUtil
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading
import time

logger = logging.getLogger(__name__)

@dataclass
class ResourceMetrics:
    """Real-time resource usage metrics."""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    gpu_memory_percent: float = 0.0
    gpu_utilization: float = 0.0
    disk_usage_percent: float = 0.0
    network_io: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class PerformanceThreshold:
    """Performance threshold configuration."""
    metric_name: str
    warning_threshold: float
    critical_threshold: float
    action: str  # 'reduce_concurrency', 'pause_jobs', 'alert', 'optimize'

@dataclass
class OptimizationAction:
    """Optimization action to be taken."""
    action_type: str  # 'reduce_batch_size', 'increase_concurrency', 'enable_caching', etc.
    target_component: str
    parameters: Dict[str, Any]
    priority: int = 1
    timestamp: datetime = field(default_factory=datetime.now)

class PerformanceTuner:
    """Intelligent performance tuning and resource management."""

    def __init__(self):
        self.metrics_history: List[ResourceMetrics] = []
        self.max_history_size = 1000
        self.monitoring_interval = 5  # seconds
        self.thresholds = self._load_default_thresholds()
        self.optimization_actions: List[OptimizationAction] = []
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None

        # Performance tuning parameters
        self.current_concurrency = 4
        self.current_batch_size = 1
        self.adaptive_enabled = True

    def _load_default_thresholds(self) -> List[PerformanceThreshold]:
        """Load default performance thresholds."""
        return [
            PerformanceThreshold("cpu_percent", 80.0, 95.0, "reduce_concurrency"),
            PerformanceThreshold("memory_percent", 85.0, 95.0, "reduce_batch_size"),
            PerformanceThreshold("gpu_memory_percent", 90.0, 98.0, "pause_jobs"),
            PerformanceThreshold("gpu_utilization", 95.0, 99.0, "alert"),
            PerformanceThreshold("disk_usage_percent", 90.0, 98.0, "enable_caching")
        ]

    def start_monitoring(self):
        """Start real-time performance monitoring."""
        if self.is_monitoring:
            return

        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Performance monitoring started")

    def stop_monitoring(self):
        """Stop performance monitoring."""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Performance monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                metrics = self._collect_metrics()
                self.metrics_history.append(metrics)

                # Keep history size manageable
                if len(self.metrics_history) > self.max_history_size:
                    self.metrics_history = self.metrics_history[-self.max_history_size:]

                # Check thresholds and generate actions
                self._check_thresholds(metrics)

                # Adaptive optimization
                if self.adaptive_enabled:
                    self._perform_adaptive_optimization()

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")

            time.sleep(self.monitoring_interval)

    def _collect_metrics(self) -> ResourceMetrics:
        """Collect current system resource metrics."""
        metrics = ResourceMetrics()

        # CPU usage
        metrics.cpu_percent = psutil.cpu_percent(interval=1)

        # Memory usage
        memory = psutil.virtual_memory()
        metrics.memory_percent = memory.percent

        # Disk usage
        disk = psutil.disk_usage('/')
        metrics.disk_usage_percent = disk.percent

        # GPU metrics (if available)
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]  # Primary GPU
                metrics.gpu_memory_percent = gpu.memoryPercent
                metrics.gpu_utilization = gpu.load * 100
        except Exception:
            # GPU monitoring not available
            pass

        # Network I/O (basic)
        net_io = psutil.net_io_counters()
        metrics.network_io = {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv
        }

        return metrics

    def _check_thresholds(self, metrics: ResourceMetrics):
        """Check metrics against thresholds and generate actions."""
        for threshold in self.thresholds:
            value = getattr(metrics, threshold.metric_name, 0)

            if value >= threshold.critical_threshold:
                action = OptimizationAction(
                    action_type=threshold.action,
                    target_component="system",
                    parameters={
                        "metric": threshold.metric_name,
                        "value": value,
                        "threshold": threshold.critical_threshold,
                        "severity": "critical"
                    },
                    priority=3
                )
                self.optimization_actions.append(action)
                logger.warning(f"Critical threshold exceeded: {threshold.metric_name} = {value}")

            elif value >= threshold.warning_threshold:
                action = OptimizationAction(
                    action_type=threshold.action,
                    target_component="system",
                    parameters={
                        "metric": threshold.metric_name,
                        "value": value,
                        "threshold": threshold.warning_threshold,
                        "severity": "warning"
                    },
                    priority=2
                )
                self.optimization_actions.append(action)
                logger.info(f"Warning threshold exceeded: {threshold.metric_name} = {value}")

    def _perform_adaptive_optimization(self):
        """Perform adaptive optimization based on recent metrics."""
        if len(self.metrics_history) < 10:
            return

        recent_metrics = self.metrics_history[-10:]

        # Analyze trends
        cpu_trend = self._calculate_trend([m.cpu_percent for m in recent_metrics])
        memory_trend = self._calculate_trend([m.memory_percent for m in recent_metrics])
        gpu_trend = self._calculate_trend([m.gpu_utilization for m in recent_metrics])

        # Adaptive concurrency adjustment
        avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)

        if avg_cpu > 85 or avg_memory > 90:
            if self.current_concurrency > 1:
                self.current_concurrency -= 1
                action = OptimizationAction(
                    action_type="reduce_concurrency",
                    target_component="execution_engine",
                    parameters={"new_concurrency": self.current_concurrency},
                    priority=2
                )
                self.optimization_actions.append(action)
                logger.info(f"Reduced concurrency to {self.current_concurrency}")

        elif avg_cpu < 60 and avg_memory < 70 and cpu_trend < 0.1:
            if self.current_concurrency < 8:
                self.current_concurrency += 1
                action = OptimizationAction(
                    action_type="increase_concurrency",
                    target_component="execution_engine",
                    parameters={"new_concurrency": self.current_concurrency},
                    priority=1
                )
                self.optimization_actions.append(action)
                logger.info(f"Increased concurrency to {self.current_concurrency}")

        # Adaptive batch size adjustment
        if avg_memory > 85:
            if self.current_batch_size > 1:
                self.current_batch_size -= 1
                action = OptimizationAction(
                    action_type="reduce_batch_size",
                    target_component="execution_engine",
                    parameters={"new_batch_size": self.current_batch_size},
                    priority=2
                )
                self.optimization_actions.append(action)
                logger.info(f"Reduced batch size to {self.current_batch_size}")

    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend slope for a series of values."""
        if len(values) < 2:
            return 0.0

        # Simple linear regression slope
        n = len(values)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(values) / n

        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        return numerator / denominator

    def get_current_metrics(self) -> ResourceMetrics:
        """Get current system metrics."""
        return self._collect_metrics()

    def get_metrics_history(self, hours: int = 1) -> List[ResourceMetrics]:
        """Get metrics history for the specified time period."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [m for m in self.metrics_history if m.timestamp > cutoff_time]

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        if not self.metrics_history:
            return {"error": "No metrics available"}

        recent_metrics = self.metrics_history[-min(100, len(self.metrics_history)):]

        # Calculate averages
        avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
        avg_gpu_util = sum(m.gpu_utilization for m in recent_metrics) / len(recent_metrics)
        avg_gpu_mem = sum(m.gpu_memory_percent for m in recent_metrics) / len(recent_metrics)

        # Calculate peaks
        peak_cpu = max(m.cpu_percent for m in recent_metrics)
        peak_memory = max(m.memory_percent for m in recent_metrics)
        peak_gpu_util = max(m.gpu_utilization for m in recent_metrics)
        peak_gpu_mem = max(m.gpu_memory_percent for m in recent_metrics)

        # Performance score (0-100)
        performance_score = 100 - (
            (avg_cpu / 100 * 25) +
            (avg_memory / 100 * 25) +
            (avg_gpu_util / 100 * 25) +
            (avg_gpu_mem / 100 * 25)
        )

        return {
            "current_metrics": self.get_current_metrics().__dict__,
            "averages": {
                "cpu_percent": avg_cpu,
                "memory_percent": avg_memory,
                "gpu_utilization": avg_gpu_util,
                "gpu_memory_percent": avg_gpu_mem
            },
            "peaks": {
                "cpu_percent": peak_cpu,
                "memory_percent": peak_memory,
                "gpu_utilization": peak_gpu_util,
                "gpu_memory_percent": peak_gpu_mem
            },
            "performance_score": max(0, performance_score),
            "optimization_settings": {
                "current_concurrency": self.current_concurrency,
                "current_batch_size": self.current_batch_size,
                "adaptive_enabled": self.adaptive_enabled
            },
            "pending_actions": len(self.optimization_actions),
            "recommendations": self._generate_recommendations()
        }

    def _generate_recommendations(self) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []

        if not self.metrics_history:
            return ["Start monitoring to get performance insights"]

        recent = self.metrics_history[-20:] if len(self.metrics_history) > 20 else self.metrics_history

        avg_cpu = sum(m.cpu_percent for m in recent) / len(recent)
        avg_memory = sum(m.memory_percent for m in recent) / len(recent)

        if avg_cpu > 80:
            recommendations.append("Consider reducing concurrent executions to lower CPU usage")
        elif avg_cpu < 50:
            recommendations.append("CPU usage is low - consider increasing concurrency for better throughput")

        if avg_memory > 85:
            recommendations.append("High memory usage detected - consider reducing batch sizes or enabling caching")
        elif avg_memory < 60:
            recommendations.append("Memory usage is low - can handle larger batches or increased concurrency")

        if not recommendations:
            recommendations.append("System performance is well balanced")

        return recommendations

    def get_pending_actions(self) -> List[OptimizationAction]:
        """Get pending optimization actions."""
        return self.optimization_actions.copy()

    def execute_action(self, action: OptimizationAction) -> bool:
        """Execute an optimization action."""
        try:
            logger.info(f"Executing optimization action: {action.action_type}")

            # This would integrate with the actual system components
            # For now, just log and remove from pending
            if action in self.optimization_actions:
                self.optimization_actions.remove(action)

            return True
        except Exception as e:
            logger.error(f"Failed to execute action {action.action_type}: {e}")
            return False

    def set_adaptive_mode(self, enabled: bool):
        """Enable or disable adaptive optimization."""
        self.adaptive_enabled = enabled
        logger.info(f"Adaptive optimization {'enabled' if enabled else 'disabled'}")

    def set_concurrency_limit(self, limit: int):
        """Set maximum concurrency limit."""
        self.current_concurrency = max(1, min(limit, 16))
        logger.info(f"Concurrency limit set to {self.current_concurrency}")

    def set_batch_size_limit(self, size: int):
        """Set batch size limit."""
        self.current_batch_size = max(1, min(size, 8))
        logger.info(f"Batch size limit set to {self.current_batch_size}")

# Global instance
_performance_tuner = None

def initialize_performance_tuner() -> bool:
    """Initialize the performance tuner."""
    global _performance_tuner

    try:
        _performance_tuner = PerformanceTuner()
        _performance_tuner.start_monitoring()
        logger.info("Performance tuner initialized")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize performance tuner: {e}")
        return False

def get_performance_tuner() -> PerformanceTuner:
    """Get the global performance tuner."""
    return _performance_tuner

def shutdown_performance_tuner():
    """Shutdown the performance tuner."""
    global _performance_tuner
    if _performance_tuner:
        _performance_tuner.stop_monitoring()
        _performance_tuner = None