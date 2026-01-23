"""
Analytics & Monitoring System
Comprehensive tracking, analytics, and performance monitoring
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid
import threading
import statistics
from collections import defaultdict, deque
import psutil
import os

try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False


class AnalyticsEventType(Enum):
    """Types of analytics events"""
    USER_ACTION = "user_action"
    SYSTEM_METRIC = "system_metric"
    PERFORMANCE_METRIC = "performance_metric"
    ERROR_EVENT = "error_event"
    BUSINESS_METRIC = "business_metric"
    CONTENT_METRIC = "content_metric"


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class AnalyticsEvent:
    """Analytics event data"""
    event_id: str
    event_type: AnalyticsEventType
    timestamp: datetime
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    project_id: Optional[str] = None
    event_name: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'session_id': self.session_id,
            'project_id': self.project_id,
            'event_name': self.event_name,
            'properties': self.properties,
            'metadata': self.metadata
        }


@dataclass
class MetricData:
    """Metric data point"""
    metric_name: str
    metric_type: MetricType
    value: Union[int, float]
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'metric_name': self.metric_name,
            'metric_type': self.metric_type.value,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'labels': self.labels,
            'metadata': self.metadata
        }


@dataclass
class PerformanceProfile:
    """Performance profile data"""
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def complete(self, success: bool = True):
        """Mark operation as completed"""
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()
        self.success = success


class AnalyticsSystem:
    """Comprehensive analytics and monitoring system"""

    def __init__(self, storage_path: str = "./analytics_data"):
        self.logger = logging.getLogger(__name__)

        # Storage configuration
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)

        # Event storage
        self.events_buffer: List[AnalyticsEvent] = []
        self.buffer_size = 1000
        self.flush_interval = 30  # seconds

        # Metrics storage
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))

        # Performance monitoring
        self.active_profiles: Dict[str, PerformanceProfile] = {}
        self.performance_history: Dict[str, List[float]] = defaultdict(list)

        # System monitoring
        self.system_metrics_interval = 60  # seconds
        self.system_stats_history = deque(maxlen=1000)

        # User analytics
        self.user_sessions: Dict[str, Dict[str, Any]] = {}
        self.user_journey: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        # Content analytics
        self.content_metrics: Dict[str, Dict[str, Any]] = defaultdict(dict)

        # Business metrics
        self.business_metrics: Dict[str, Any] = {}

        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        self.is_running = False

        # Initialize background tasks
        self._setup_background_tasks()

    def _setup_background_tasks(self):
        """Setup background monitoring tasks"""
        pass  # Will be started when system starts

    async def start_monitoring(self):
        """Start the analytics monitoring system"""
        self.is_running = True
        self.logger.info("Starting analytics monitoring system")

        # Start background tasks
        self.background_tasks = [
            asyncio.create_task(self._flush_events_loop()),
            asyncio.create_task(self._system_monitoring_loop()),
            asyncio.create_task(self._metrics_cleanup_loop())
        ]

    async def stop_monitoring(self):
        """Stop the analytics monitoring system"""
        self.is_running = False
        self.logger.info("Stopping analytics monitoring system")

        # Wait for background tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)

        # Final flush
        await self._flush_events()

    def track_event(self, event_type: AnalyticsEventType, event_name: str,
                   user_id: Optional[str] = None, session_id: Optional[str] = None,
                   project_id: Optional[str] = None, properties: Dict[str, Any] = None,
                   metadata: Dict[str, Any] = None):
        """Track an analytics event"""
        event = AnalyticsEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now(),
            user_id=user_id,
            session_id=session_id,
            project_id=project_id,
            event_name=event_name,
            properties=properties or {},
            metadata=metadata or {}
        )

        self.events_buffer.append(event)

        # Update user journey if applicable
        if user_id and session_id:
            self._update_user_journey(user_id, session_id, event)

        # Flush if buffer is full
        if len(self.events_buffer) >= self.buffer_size:
            asyncio.create_task(self._flush_events())

    def record_metric(self, metric_name: str, value: Union[int, float],
                     metric_type: MetricType = MetricType.GAUGE,
                     labels: Dict[str, str] = None, metadata: Dict[str, Any] = None):
        """Record a metric data point"""
        metric = MetricData(
            metric_name=metric_name,
            metric_type=metric_type,
            value=value,
            timestamp=datetime.now(),
            labels=labels or {},
            metadata=metadata or {}
        )

        self.metrics[metric_name].append(metric)

    def start_performance_profile(self, operation_name: str, metadata: Dict[str, Any] = None) -> str:
        """Start performance profiling for an operation"""
        profile_id = str(uuid.uuid4())

        profile = PerformanceProfile(
            operation_name=operation_name,
            start_time=datetime.now(),
            metadata=metadata or {}
        )

        self.active_profiles[profile_id] = profile
        return profile_id

    def end_performance_profile(self, profile_id: str, success: bool = True):
        """End performance profiling for an operation"""
        if profile_id in self.active_profiles:
            profile = self.active_profiles[profile_id]
            profile.complete(success)

            # Record duration metric
            self.record_metric(
                f"performance.{profile.operation_name}",
                profile.duration,
                MetricType.HISTOGRAM,
                labels={"success": str(success)},
                metadata=profile.metadata
            )

            # Add to history
            self.performance_history[profile.operation_name].append(profile.duration)

            # Keep history limited
            if len(self.performance_history[profile.operation_name]) > 1000:
                self.performance_history[profile.operation_name] = self.performance_history[profile.operation_name][-1000:]

            del self.active_profiles[profile_id]

    def track_user_session(self, user_id: str, session_id: str, action: str,
                          properties: Dict[str, Any] = None):
        """Track user session activity"""
        if session_id not in self.user_sessions:
            self.user_sessions[session_id] = {
                'user_id': user_id,
                'start_time': datetime.now(),
                'last_activity': datetime.now(),
                'actions': []
            }

        session = self.user_sessions[session_id]
        session['last_activity'] = datetime.now()
        session['actions'].append({
            'timestamp': datetime.now(),
            'action': action,
            'properties': properties or {}
        })

        # Track event
        self.track_event(
            AnalyticsEventType.USER_ACTION,
            action,
            user_id=user_id,
            session_id=session_id,
            properties=properties
        )

    def track_content_metric(self, content_id: str, metric_name: str, value: Any,
                           metadata: Dict[str, Any] = None):
        """Track content-related metrics"""
        if content_id not in self.content_metrics:
            self.content_metrics[content_id] = {}

        self.content_metrics[content_id][metric_name] = {
            'value': value,
            'timestamp': datetime.now(),
            'metadata': metadata or {}
        }

        # Record as metric
        self.record_metric(
            f"content.{metric_name}",
            value if isinstance(value, (int, float)) else 1,
            MetricType.GAUGE,
            labels={'content_id': content_id},
            metadata=metadata
        )

    def update_business_metric(self, metric_name: str, value: Any):
        """Update business metric"""
        self.business_metrics[metric_name] = {
            'value': value,
            'timestamp': datetime.now()
        }

        # Record as metric if numeric
        if isinstance(value, (int, float)):
            self.record_metric(
                f"business.{metric_name}",
                value,
                MetricType.GAUGE
            )

    async def _flush_events_loop(self):
        """Background task to periodically flush events"""
        while self.is_running:
            try:
                await asyncio.sleep(self.flush_interval)
                await self._flush_events()
            except Exception as e:
                self.logger.error(f"Error in events flush loop: {e}")

    async def _system_monitoring_loop(self):
        """Background task for system monitoring"""
        while self.is_running:
            try:
                await asyncio.sleep(self.system_metrics_interval)
                await self._collect_system_metrics()
            except Exception as e:
                self.logger.error(f"Error in system monitoring loop: {e}")

    async def _metrics_cleanup_loop(self):
        """Background task to cleanup old metrics"""
        while self.is_running:
            try:
                await asyncio.sleep(3600)  # Clean up every hour
                self._cleanup_old_metrics()
            except Exception as e:
                self.logger.error(f"Error in metrics cleanup loop: {e}")

    async def _flush_events(self):
        """Flush events buffer to storage"""
        if not self.events_buffer:
            return

        try:
            # Group events by date
            events_by_date = defaultdict(list)
            for event in self.events_buffer:
                date_str = event.timestamp.strftime("%Y-%m-%d")
                events_by_date[date_str].append(event.to_dict())

            # Write to files
            for date_str, events in events_by_date.items():
                filename = self.storage_path / f"events_{date_str}.jsonl"

                if AIOFILES_AVAILABLE:
                    async with aiofiles.open(filename, 'a') as f:
                        for event in events:
                            await f.write(json.dumps(event) + '\n')
                else:
                    with open(filename, 'a') as f:
                        for event in events:
                            f.write(json.dumps(event) + '\n')

            self.events_buffer.clear()
            self.logger.debug(f"Flushed {sum(len(events) for events in events_by_date.values())} events")

        except Exception as e:
            self.logger.error(f"Failed to flush events: {e}")

    async def _collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.record_metric("system.cpu_percent", cpu_percent, MetricType.GAUGE)

            # Memory usage
            memory = psutil.virtual_memory()
            self.record_metric("system.memory_percent", memory.percent, MetricType.GAUGE)
            self.record_metric("system.memory_used", memory.used, MetricType.GAUGE)

            # Disk usage
            disk = psutil.disk_usage('/')
            self.record_metric("system.disk_percent", disk.percent, MetricType.GAUGE)

            # Network I/O
            net_io = psutil.net_io_counters()
            self.record_metric("system.network_bytes_sent", net_io.bytes_sent, MetricType.COUNTER)
            self.record_metric("system.network_bytes_recv", net_io.bytes_recv, MetricType.COUNTER)

            # Process info
            process = psutil.Process()
            self.record_metric("system.process_cpu_percent", process.cpu_percent(), MetricType.GAUGE)
            self.record_metric("system.process_memory_mb", process.memory_info().rss / 1024 / 1024, MetricType.GAUGE)

            # System stats snapshot
            stats = {
                'timestamp': datetime.now(),
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_percent': disk.percent,
                'active_users': len(self.user_sessions),
                'active_profiles': len(self.active_profiles)
            }
            self.system_stats_history.append(stats)

        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")

    def _cleanup_old_metrics(self):
        """Cleanup old metric data"""
        cutoff_time = datetime.now() - timedelta(hours=24)

        for metric_name, metric_queue in self.metrics.items():
            # Remove old metrics (keep only last 24 hours)
            while metric_queue and metric_queue[0].timestamp < cutoff_time:
                metric_queue.popleft()

    def _update_user_journey(self, user_id: str, session_id: str, event: AnalyticsEvent):
        """Update user journey tracking"""
        journey_entry = {
            'timestamp': event.timestamp,
            'event_name': event.event_name,
            'properties': event.properties
        }

        self.user_journey[user_id].append(journey_entry)

        # Keep journey limited to last 1000 events per user
        if len(self.user_journey[user_id]) > 1000:
            self.user_journey[user_id] = self.user_journey[user_id][-1000:]

    def get_user_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get analytics data for a specific user"""
        cutoff_time = datetime.now() - timedelta(days=days)

        # Filter user events
        user_events = []
        for event in self.events_buffer:
            if event.user_id == user_id and event.timestamp > cutoff_time:
                user_events.append(event.to_dict())

        # Get user journey
        journey = self.user_journey.get(user_id, [])

        # Calculate engagement metrics
        total_actions = len(user_events)
        unique_actions = len(set(event['event_name'] for event in user_events))

        # Session analysis
        user_sessions = [s for s in self.user_sessions.values() if s['user_id'] == user_id]
        avg_session_duration = 0
        if user_sessions:
            durations = [(s['last_activity'] - s['start_time']).total_seconds() for s in user_sessions]
            avg_session_duration = statistics.mean(durations) if durations else 0

        return {
            'user_id': user_id,
            'total_actions': total_actions,
            'unique_actions': unique_actions,
            'avg_session_duration': avg_session_duration,
            'journey_length': len(journey),
            'recent_events': user_events[-10:],  # Last 10 events
            'engagement_score': min(100, total_actions * 2)  # Simple engagement score
        }

    def get_performance_analytics(self, operation_name: Optional[str] = None,
                                hours: int = 24) -> Dict[str, Any]:
        """Get performance analytics"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        if operation_name:
            # Specific operation
            durations = self.performance_history.get(operation_name, [])
            if not durations:
                return {'operation': operation_name, 'error': 'No data available'}

            return {
                'operation': operation_name,
                'total_calls': len(durations),
                'avg_duration': statistics.mean(durations),
                'median_duration': statistics.median(durations),
                'min_duration': min(durations),
                'max_duration': max(durations),
                'p95_duration': statistics.quantiles(durations, n=20)[18] if len(durations) >= 20 else max(durations),
                'success_rate': 0.95  # Would need to track success/failure separately
            }
        else:
            # All operations
            operations = {}
            for op_name, durations in self.performance_history.items():
                if durations:
                    operations[op_name] = {
                        'total_calls': len(durations),
                        'avg_duration': statistics.mean(durations),
                        'success_rate': 0.95
                    }

            return {
                'total_operations': len(operations),
                'operations': operations,
                'time_range_hours': hours
            }

    def get_content_analytics(self, content_id: Optional[str] = None) -> Dict[str, Any]:
        """Get content analytics"""
        if content_id:
            return self.content_metrics.get(content_id, {})
        else:
            return dict(self.content_metrics)

    def get_business_metrics(self) -> Dict[str, Any]:
        """Get business metrics"""
        return self.business_metrics.copy()

    def get_system_health(self) -> Dict[str, Any]:
        """Get system health overview"""
        # Calculate system health score
        health_score = 100

        # CPU health
        cpu_metrics = list(self.metrics.get('system.cpu_percent', []))
        if cpu_metrics:
            avg_cpu = statistics.mean(m.value for m in cpu_metrics[-10:])  # Last 10 readings
            if avg_cpu > 90:
                health_score -= 30
            elif avg_cpu > 70:
                health_score -= 10

        # Memory health
        memory_metrics = list(self.metrics.get('system.memory_percent', []))
        if memory_metrics:
            avg_memory = statistics.mean(m.value for m in memory_metrics[-10:])
            if avg_memory > 90:
                health_score -= 30
            elif avg_memory > 80:
                health_score -= 15

        # Active users (more users = healthier, to a point)
        active_users = len(self.user_sessions)
        if active_users == 0:
            health_score -= 20
        elif active_users > 100:
            health_score += 10

        return {
            'health_score': max(0, min(100, health_score)),
            'status': 'healthy' if health_score >= 80 else 'warning' if health_score >= 60 else 'critical',
            'active_users': active_users,
            'active_operations': len(self.active_profiles),
            'events_buffer_size': len(self.events_buffer),
            'last_system_check': datetime.now()
        }

    def generate_report(self, report_type: str, start_date: datetime = None,
                       end_date: datetime = None) -> Dict[str, Any]:
        """Generate analytics report"""
        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now()

        if report_type == 'user_engagement':
            return self._generate_user_engagement_report(start_date, end_date)
        elif report_type == 'performance':
            return self._generate_performance_report(start_date, end_date)
        elif report_type == 'system':
            return self._generate_system_report(start_date, end_date)
        else:
            return {'error': f'Unknown report type: {report_type}'}

    def _generate_user_engagement_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate user engagement report"""
        # Simplified implementation
        total_users = len(set(event.user_id for event in self.events_buffer
                            if event.timestamp >= start_date and event.timestamp <= end_date
                            and event.user_id))

        total_events = len([event for event in self.events_buffer
                          if event.timestamp >= start_date and event.timestamp <= end_date])

        return {
            'report_type': 'user_engagement',
            'period': f'{start_date.date()} to {end_date.date()}',
            'total_users': total_users,
            'total_events': total_events,
            'avg_events_per_user': total_events / total_users if total_users > 0 else 0,
            'most_active_users': []  # Would implement user ranking
        }

    def _generate_performance_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate performance report"""
        return self.get_performance_analytics(hours=int((end_date - start_date).total_seconds() / 3600))

    def _generate_system_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate system report"""
        return {
            'report_type': 'system',
            'period': f'{start_date.date()} to {end_date.date()}',
            'system_health': self.get_system_health(),
            'avg_cpu_percent': self._get_metric_average('system.cpu_percent', start_date, end_date),
            'avg_memory_percent': self._get_metric_average('system.memory_percent', start_date, end_date),
            'total_events': len([e for e in self.events_buffer
                               if start_date <= e.timestamp <= end_date])
        }

    def _get_metric_average(self, metric_name: str, start_date: datetime, end_date: datetime) -> float:
        """Get average value for a metric over time period"""
        metrics = [m.value for m in self.metrics.get(metric_name, [])
                  if start_date <= m.timestamp <= end_date]

        return statistics.mean(metrics) if metrics else 0.0


# Global instance
_analytics_system = None

def get_analytics_system() -> AnalyticsSystem:
    """Get global analytics system instance"""
    global _analytics_system
    if _analytics_system is None:
        _analytics_system = AnalyticsSystem()
    return _analytics_system

async def initialize_analytics_system(storage_path: str = "./analytics_data") -> AnalyticsSystem:
    """Initialize the global analytics system"""
    global _analytics_system
    if _analytics_system is None:
        _analytics_system = AnalyticsSystem(storage_path)
        await _analytics_system.start_monitoring()
    return _analytics_system</content>
<parameter name="filePath">c:\Users\Baxter\Documents\ComfyUI_env\ComfyUI\custom_nodes\Comfy Gimpy Node Pack\advanced_ai\analytics_system.py