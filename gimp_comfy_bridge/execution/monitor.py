"""
Execution Monitor - Phase 9
Real-time monitoring, analytics, and performance tracking for ComfyUI executions.
"""

import asyncio
import logging
import time
import statistics
from dataclasses import dataclass, field
from collections import defaultdict, deque
from typing import Dict, List, Optional, Any, Deque
from datetime import datetime, timedelta

from gimp_comfy_bridge.execution.engine import ExecutionJob, ExecutionState

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for execution monitoring."""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    average_execution_time: float = 0.0
    median_execution_time: float = 0.0
    min_execution_time: float = float('inf')
    max_execution_time: float = 0.0
    execution_times: List[float] = field(default_factory=list)
    throughput_per_minute: float = 0.0
    error_rate: float = 0.0
    queue_wait_times: List[float] = field(default_factory=list)
    average_queue_wait_time: float = 0.0


@dataclass
class SystemHealth:
    """System health metrics."""
    comfyui_connected: bool = False
    websocket_connected: bool = False
    active_jobs: int = 0
    queued_jobs: int = 0
    memory_usage: float = 0.0  # MB
    cpu_usage: float = 0.0     # Percentage
    gpu_memory_used: float = 0.0  # MB
    gpu_memory_total: float = 0.0  # MB
    last_health_check: Optional[float] = None


@dataclass
class ExecutionEvent:
    """Represents an execution event for monitoring."""
    event_type: str  # "started", "completed", "failed", "cancelled"
    job_id: str
    timestamp: float
    execution_time: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExecutionMonitor:
    """Monitors execution performance and system health."""

    def __init__(self, max_history_size: int = 1000):
        self.max_history_size = max_history_size
        self.execution_history: Deque[ExecutionEvent] = deque(maxlen=max_history_size)
        self.active_jobs: Dict[str, ExecutionJob] = {}
        self.performance_metrics = PerformanceMetrics()
        self.system_health = SystemHealth()
        self.monitoring_task: Optional[asyncio.Task] = None
        self.is_monitoring = False

        # Rolling metrics (last hour)
        self.rolling_window = timedelta(hours=1)
        self.rolling_events: Deque[ExecutionEvent] = deque()

    async def start_monitoring(self):
        """Start the monitoring system."""
        if self.is_monitoring:
            return

        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Execution monitoring started")

    async def stop_monitoring(self):
        """Stop the monitoring system."""
        if not self.is_monitoring:
            return

        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("Execution monitoring stopped")

    def record_job_start(self, job: ExecutionJob):
        """Record when a job starts execution."""
        event = ExecutionEvent(
            event_type="started",
            job_id=job.job_id,
            timestamp=time.time(),
            metadata={
                "template_id": getattr(job.workflow_data, 'template_id', None),
                "style_id": getattr(job.workflow_data, 'style_id', None),
                "fusion_result": job.fusion_result.id if job.fusion_result else None
            }
        )

        self.execution_history.append(event)
        self.rolling_events.append(event)
        self.active_jobs[job.job_id] = job

        # Update queue wait time if we have start time
        if job.start_time:
            queue_wait_time = job.start_time - (job.start_time - 0.1)  # Placeholder
            self.performance_metrics.queue_wait_times.append(queue_wait_time)

    def record_job_completion(self, job: ExecutionJob):
        """Record when a job completes successfully."""
        execution_time = None
        if job.end_time and job.start_time:
            execution_time = job.end_time - job.start_time

        event = ExecutionEvent(
            event_type="completed",
            job_id=job.job_id,
            timestamp=time.time(),
            execution_time=execution_time,
            metadata={
                "node_count": getattr(job.workflow_data, 'node_count', None),
                "output_count": len(job.result.outputs) if job.result else 0
            }
        )

        self.execution_history.append(event)
        self.rolling_events.append(event)
        self.active_jobs.pop(job.job_id, None)

        # Update performance metrics
        self._update_performance_metrics(event)

    def record_job_failure(self, job: ExecutionJob):
        """Record when a job fails."""
        execution_time = None
        if job.end_time and job.start_time:
            execution_time = job.end_time - job.start_time

        event = ExecutionEvent(
            event_type="failed",
            job_id=job.job_id,
            timestamp=time.time(),
            execution_time=execution_time,
            error_message=job.error_message,
            metadata={
                "failure_reason": self._categorize_error(job.error_message)
            }
        )

        self.execution_history.append(event)
        self.rolling_events.append(event)
        self.active_jobs.pop(job.job_id, None)

        # Update performance metrics
        self._update_performance_metrics(event)

    def record_job_cancellation(self, job: ExecutionJob):
        """Record when a job is cancelled."""
        event = ExecutionEvent(
            event_type="cancelled",
            job_id=job.job_id,
            timestamp=time.time(),
            metadata={"cancel_reason": "user_request"}
        )

        self.execution_history.append(event)
        self.rolling_events.append(event)
        self.active_jobs.pop(job.job_id, None)

    def update_system_health(self, health_data: Dict[str, Any]):
        """Update system health information."""
        self.system_health.comfyui_connected = health_data.get("comfyui_connected", False)
        self.system_health.websocket_connected = health_data.get("websocket_connected", False)
        self.system_health.active_jobs = health_data.get("active_jobs", 0)
        self.system_health.queued_jobs = health_data.get("queued_jobs", 0)
        self.system_health.last_health_check = time.time()

        # Update resource usage if available
        system_stats = health_data.get("system_stats", {})
        if "ram" in system_stats:
            self.system_health.memory_usage = system_stats["ram"].get("used", 0) / (1024 * 1024)  # Convert to MB

        if "cpu" in system_stats:
            self.system_health.cpu_usage = system_stats["cpu"].get("usage", 0)

        if "gpu" in system_stats:
            gpu_stats = system_stats["gpu"]
            self.system_health.gpu_memory_used = gpu_stats.get("memory_used", 0) / (1024 * 1024)  # Convert to MB
            self.system_health.gpu_memory_total = gpu_stats.get("memory_total", 0) / (1024 * 1024)  # Convert to MB

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate a comprehensive performance report."""
        return {
            "overall_metrics": self._calculate_overall_metrics(),
            "rolling_metrics": self._calculate_rolling_metrics(),
            "system_health": self.system_health.__dict__,
            "active_jobs": len(self.active_jobs),
            "recent_events": [event.__dict__ for event in list(self.execution_history)[-10:]]
        }

    def get_execution_stats(self, hours: int = 1) -> Dict[str, Any]:
        """Get execution statistics for the specified time period."""
        cutoff_time = time.time() - (hours * 3600)

        # Filter events in time window
        recent_events = [e for e in self.rolling_events if e.timestamp >= cutoff_time]

        completed_events = [e for e in recent_events if e.event_type == "completed"]
        failed_events = [e for e in recent_events if e.event_type == "failed"]

        stats = {
            "time_window_hours": hours,
            "total_executions": len(recent_events),
            "successful_executions": len(completed_events),
            "failed_executions": len(failed_events),
            "success_rate": len(completed_events) / max(len(recent_events), 1),
            "average_execution_time": statistics.mean([e.execution_time for e in completed_events if e.execution_time]) if completed_events else 0,
            "throughput_per_hour": len(completed_events) / hours if hours > 0 else 0
        }

        return stats

    def _update_performance_metrics(self, event: ExecutionEvent):
        """Update performance metrics with a new event."""
        self.performance_metrics.total_executions += 1

        if event.event_type == "completed":
            self.performance_metrics.successful_executions += 1
            if event.execution_time:
                self.performance_metrics.execution_times.append(event.execution_time)
                self.performance_metrics.min_execution_time = min(
                    self.performance_metrics.min_execution_time, event.execution_time
                )
                self.performance_metrics.max_execution_time = max(
                    self.performance_metrics.max_execution_time, event.execution_time
                )
        elif event.event_type == "failed":
            self.performance_metrics.failed_executions += 1

        # Recalculate averages
        if self.performance_metrics.execution_times:
            self.performance_metrics.average_execution_time = statistics.mean(
                self.performance_metrics.execution_times
            )
            self.performance_metrics.median_execution_time = statistics.median(
                self.performance_metrics.execution_times
            )

        # Calculate error rate
        total_completed = (self.performance_metrics.successful_executions +
                          self.performance_metrics.failed_executions)
        if total_completed > 0:
            self.performance_metrics.error_rate = (
                self.performance_metrics.failed_executions / total_completed
            )

        # Calculate average queue wait time
        if self.performance_metrics.queue_wait_times:
            self.performance_metrics.average_queue_wait_time = statistics.mean(
                self.performance_metrics.queue_wait_times
            )

    def _calculate_overall_metrics(self) -> Dict[str, Any]:
        """Calculate overall performance metrics."""
        return {
            "total_executions": self.performance_metrics.total_executions,
            "success_rate": (self.performance_metrics.successful_executions /
                           max(self.performance_metrics.total_executions, 1)),
            "error_rate": self.performance_metrics.error_rate,
            "average_execution_time": self.performance_metrics.average_execution_time,
            "median_execution_time": self.performance_metrics.median_execution_time,
            "min_execution_time": self.performance_metrics.min_execution_time if self.performance_metrics.min_execution_time != float('inf') else 0,
            "max_execution_time": self.performance_metrics.max_execution_time,
            "average_queue_wait_time": self.performance_metrics.average_queue_wait_time,
            "execution_time_stddev": statistics.stdev(self.performance_metrics.execution_times) if len(self.performance_metrics.execution_times) > 1 else 0
        }

    def _calculate_rolling_metrics(self) -> Dict[str, Any]:
        """Calculate rolling window metrics."""
        # Clean old events from rolling window
        cutoff_time = time.time() - self.rolling_window.total_seconds()
        while self.rolling_events and self.rolling_events[0].timestamp < cutoff_time:
            self.rolling_events.popleft()

        # Calculate metrics for rolling window
        completed_in_window = [e for e in self.rolling_events
                             if e.event_type == "completed" and e.execution_time]

        if completed_in_window:
            window_duration_hours = self.rolling_window.total_seconds() / 3600
            throughput = len(completed_in_window) / window_duration_hours
            avg_time = statistics.mean([e.execution_time for e in completed_in_window])
        else:
            throughput = 0
            avg_time = 0

        return {
            "window_duration_hours": self.rolling_window.total_seconds() / 3600,
            "events_in_window": len(self.rolling_events),
            "throughput_per_hour": throughput,
            "average_execution_time": avg_time,
            "completions_in_window": len(completed_in_window)
        }

    def _categorize_error(self, error_message: Optional[str]) -> str:
        """Categorize error messages for analytics."""
        if not error_message:
            return "unknown"

        error_lower = error_message.lower()

        if "timeout" in error_lower:
            return "timeout"
        elif "connection" in error_lower or "network" in error_lower:
            return "connection"
        elif "memory" in error_lower or "gpu" in error_lower:
            return "resource"
        elif "validation" in error_lower or "invalid" in error_lower:
            return "validation"
        elif "cancelled" in error_lower:
            return "cancelled"
        else:
            return "other"

    async def _monitoring_loop(self):
        """Main monitoring loop for periodic tasks."""
        while self.is_monitoring:
            try:
                # Clean up old rolling events
                cutoff_time = time.time() - self.rolling_window.total_seconds()
                while self.rolling_events and self.rolling_events[0].timestamp < cutoff_time:
                    self.rolling_events.popleft()

                # Log periodic health summary
                if len(self.execution_history) > 0:
                    recent_completed = [e for e in list(self.execution_history)[-20:]
                                      if e.event_type == "completed"]
                    if recent_completed:
                        avg_time = statistics.mean([e.execution_time for e in recent_completed if e.execution_time])
                        logger.debug(f"Recent performance: {len(recent_completed)} completions, avg time: {avg_time:.2f}s")

                await asyncio.sleep(60)  # Check every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(60)


class AnalyticsDashboard:
    """Analytics dashboard for execution insights."""

    def __init__(self, monitor: ExecutionMonitor):
        self.monitor = monitor

    def generate_dashboard_data(self) -> Dict[str, Any]:
        """Generate data for an analytics dashboard."""
        performance = self.monitor.get_performance_report()
        hourly_stats = self.monitor.get_execution_stats(hours=1)
        daily_stats = self.monitor.get_execution_stats(hours=24)

        # Calculate trends
        trends = self._calculate_trends()

        return {
            "performance": performance,
            "hourly_stats": hourly_stats,
            "daily_stats": daily_stats,
            "trends": trends,
            "alerts": self._generate_alerts(),
            "recommendations": self._generate_recommendations()
        }

    def _calculate_trends(self) -> Dict[str, Any]:
        """Calculate performance trends."""
        # Get stats for different time windows
        current_hour = self.monitor.get_execution_stats(hours=1)
        previous_hour = self.monitor.get_execution_stats(hours=2)
        previous_hour = {k: v for k, v in previous_hour.items()
                        if k in current_hour}  # Filter to matching keys

        trends = {}
        for key in ["success_rate", "average_execution_time", "throughput_per_hour"]:
            current = current_hour.get(key, 0)
            previous = previous_hour.get(key, 0)

            if previous > 0:
                change = ((current - previous) / previous) * 100
                trends[key] = {
                    "current": current,
                    "previous": previous,
                    "change_percent": change,
                    "direction": "up" if change > 0 else "down" if change < 0 else "stable"
                }
            else:
                trends[key] = {
                    "current": current,
                    "previous": previous,
                    "change_percent": 0,
                    "direction": "stable"
                }

        return trends

    def _generate_alerts(self) -> List[Dict[str, Any]]:
        """Generate system alerts based on current state."""
        alerts = []

        # High error rate alert
        if self.monitor.performance_metrics.error_rate > 0.1:  # >10% error rate
            alerts.append({
                "level": "warning",
                "message": f"High error rate: {self.monitor.performance_metrics.error_rate:.1%}",
                "recommendation": "Check ComfyUI logs and system resources"
            })

        # Long execution times alert
        if self.monitor.performance_metrics.average_execution_time > 60:  # >1 minute
            alerts.append({
                "level": "warning",
                "message": f"Long execution times: {self.monitor.performance_metrics.average_execution_time:.1f}s average",
                "recommendation": "Consider optimizing workflows or upgrading hardware"
            })

        # System health alerts
        if not self.monitor.system_health.comfyui_connected:
            alerts.append({
                "level": "error",
                "message": "ComfyUI connection lost",
                "recommendation": "Check ComfyUI server status and network connection"
            })

        if self.monitor.system_health.gpu_memory_used > 0.9 * self.monitor.system_health.gpu_memory_total:
            alerts.append({
                "level": "warning",
                "message": "High GPU memory usage",
                "recommendation": "Monitor for memory-related failures, consider reducing batch sizes"
            })

        return alerts

    def _generate_recommendations(self) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []

        # Performance-based recommendations
        if self.monitor.performance_metrics.average_execution_time > 30:
            recommendations.append("Consider using smaller models or optimizing workflow complexity")

        if self.monitor.performance_metrics.error_rate > 0.05:
            recommendations.append("Investigate common failure patterns in execution logs")

        if len(self.monitor.active_jobs) > 10:
            recommendations.append("High job concurrency detected - monitor system resources")

        # System-based recommendations
        if self.monitor.system_health.memory_usage > 8000:  # 8GB
            recommendations.append("High memory usage - consider increasing system RAM")

        return recommendations


# Global monitor instance
_monitor: Optional[ExecutionMonitor] = None


def get_execution_monitor() -> ExecutionMonitor:
    """Get the global execution monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = ExecutionMonitor()
    return _monitor


async def initialize_monitoring() -> ExecutionMonitor:
    """Initialize the execution monitoring system."""
    monitor = get_execution_monitor()
    await monitor.start_monitoring()
    return monitor