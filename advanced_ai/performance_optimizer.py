"""
Performance Optimization System
Advanced caching, rate limiting, and scalable processing pipelines
"""

import asyncio
import logging
import time
import hashlib
import json
import pickle
from typing import Dict, List, Any, Optional, Callable, Union, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import threading
import functools
import statistics
from collections import defaultdict, OrderedDict
import lru_cache
import redis
import psutil
import gc

try:
    import aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


T = TypeVar('T')


class CacheStrategy(Enum):
    """Cache eviction strategies"""
    LRU = "lru"
    LFU = "lfu"
    TTL = "ttl"
    SIZE_BASED = "size_based"


class CacheLevel(Enum):
    """Cache levels"""
    L1_MEMORY = "l1_memory"  # Fast in-memory cache
    L2_REDIS = "l2_redis"    # Distributed Redis cache
    L3_DISK = "l3_disk"      # Disk-based persistent cache


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    size_bytes: int = 0
    ttl: Optional[int] = None  # Time to live in seconds
    tags: List[str] = field(default_factory=list)

    def is_expired(self) -> bool:
        """Check if entry is expired"""
        if self.ttl is None:
            return False
        return (datetime.now() - self.created_at).total_seconds() > self.ttl

    def touch(self):
        """Update access metadata"""
        self.accessed_at = datetime.now()
        self.access_count += 1


@dataclass
class CacheStats:
    """Cache performance statistics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    sets: int = 0
    deletes: int = 0
    total_size_bytes: int = 0
    entry_count: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0


class MultiLevelCache:
    """Multi-level caching system with L1 memory, L2 Redis, L3 disk"""

    def __init__(self, max_memory_entries: int = 1000, redis_url: Optional[str] = None,
                 disk_cache_dir: Optional[str] = None):
        self.logger = logging.getLogger(__name__)

        # L1: In-memory LRU cache
        self.l1_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.l1_max_entries = max_memory_entries
        self.l1_stats = CacheStats()

        # L2: Redis cache
        self.redis_client = None
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
                self.l2_stats = CacheStats()
            except Exception as e:
                self.logger.warning(f"Failed to connect to Redis: {e}")

        # L3: Disk cache
        self.disk_cache_dir = disk_cache_dir
        self.l3_stats = CacheStats()

        # Cache warming
        self.warmup_data: Dict[str, Any] = {}

        # Lock for thread safety
        self._lock = threading.RLock()

    def get(self, key: str, level: CacheLevel = CacheLevel.L1_MEMORY) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            # Try L1 first
            if level in [CacheLevel.L1_MEMORY, CacheLevel.L2_REDIS, CacheLevel.L3_DISK]:
                entry = self.l1_cache.get(key)
                if entry and not entry.is_expired():
                    entry.touch()
                    self.l1_stats.hits += 1
                    return entry.value
                elif entry:
                    # Expired, remove it
                    del self.l1_cache[key]
                    self.l1_stats.evictions += 1

            # Try L2
            if level in [CacheLevel.L2_REDIS, CacheLevel.L3_DISK] and self.redis_client:
                try:
                    data = self.redis_client.get(f"cache:{key}")
                    if data:
                        entry = pickle.loads(data)
                        if not entry.is_expired():
                            # Promote to L1
                            self._set_l1(entry)
                            self.l2_stats.hits += 1
                            return entry.value
                        else:
                            self.redis_client.delete(f"cache:{key}")
                            self.l2_stats.evictions += 1
                except Exception as e:
                    self.logger.error(f"Redis get error: {e}")

            # Try L3
            if level == CacheLevel.L3_DISK and self.disk_cache_dir:
                try:
                    entry = self._get_disk(key)
                    if entry and not entry.is_expired():
                        # Promote to higher levels
                        self._set_l1(entry)
                        if self.redis_client:
                            self._set_l2(entry)
                        self.l3_stats.hits += 1
                        return entry.value
                    elif entry:
                        self._delete_disk(key)
                        self.l3_stats.evictions += 1
                except Exception as e:
                    self.logger.error(f"Disk get error: {e}")

            # Cache miss
            self._record_miss(level)
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None,
            tags: Optional[List[str]] = None, level: CacheLevel = CacheLevel.L1_MEMORY):
        """Set value in cache"""
        with self._lock:
            size_bytes = self._calculate_size(value)
            entry = CacheEntry(
                key=key,
                value=value,
                size_bytes=size_bytes,
                ttl=ttl,
                tags=tags or []
            )

            # Set in L1
            if level in [CacheLevel.L1_MEMORY, CacheLevel.L2_REDIS, CacheLevel.L3_DISK]:
                self._set_l1(entry)
                self.l1_stats.sets += 1

            # Set in L2
            if level in [CacheLevel.L2_REDIS, CacheLevel.L3_DISK] and self.redis_client:
                self._set_l2(entry)
                self.l2_stats.sets += 1

            # Set in L3
            if level == CacheLevel.L3_DISK and self.disk_cache_dir:
                self._set_disk(entry)
                self.l3_stats.sets += 1

    def delete(self, key: str, level: CacheLevel = CacheLevel.L1_MEMORY):
        """Delete from cache"""
        with self._lock:
            deleted = False

            if level in [CacheLevel.L1_MEMORY, CacheLevel.L2_REDIS, CacheLevel.L3_DISK]:
                if key in self.l1_cache:
                    del self.l1_cache[key]
                    self.l1_stats.deletes += 1
                    deleted = True

            if level in [CacheLevel.L2_REDIS, CacheLevel.L3_DISK] and self.redis_client:
                try:
                    if self.redis_client.delete(f"cache:{key}"):
                        self.l2_stats.deletes += 1
                        deleted = True
                except Exception as e:
                    self.logger.error(f"Redis delete error: {e}")

            if level == CacheLevel.L3_DISK and self.disk_cache_dir:
                if self._delete_disk(key):
                    self.l3_stats.deletes += 1
                    deleted = True

            return deleted

    def clear(self, tags: Optional[List[str]] = None, level: CacheLevel = CacheLevel.L1_MEMORY):
        """Clear cache entries"""
        with self._lock:
            if tags:
                # Clear by tags
                self._clear_by_tags(tags, level)
            else:
                # Clear all
                if level in [CacheLevel.L1_MEMORY, CacheLevel.L2_REDIS, CacheLevel.L3_DISK]:
                    self.l1_cache.clear()
                    self.l1_stats = CacheStats()

                if level in [CacheLevel.L2_REDIS, CacheLevel.L3_DISK] and self.redis_client:
                    try:
                        self.redis_client.flushdb()
                        self.l2_stats = CacheStats()
                    except Exception as e:
                        self.logger.error(f"Redis clear error: {e}")

                if level == CacheLevel.L3_DISK and self.disk_cache_dir:
                    self._clear_disk()
                    self.l3_stats = CacheStats()

    def warmup(self, data: Dict[str, Any]):
        """Warm up cache with data"""
        self.warmup_data.update(data)
        for key, value in data.items():
            self.set(key, value)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'l1_memory': {
                'entries': len(self.l1_cache),
                'max_entries': self.l1_max_entries,
                'hit_rate': self.l1_stats.hit_rate,
                'total_size_bytes': sum(e.size_bytes for e in self.l1_cache.values()),
                **self.l1_stats.__dict__
            },
            'l2_redis': self.l2_stats.__dict__ if self.redis_client else None,
            'l3_disk': self.l3_stats.__dict__ if self.disk_cache_dir else None
        }

    def _set_l1(self, entry: CacheEntry):
        """Set entry in L1 cache"""
        # Remove if exists
        if entry.key in self.l1_cache:
            del self.l1_cache[entry.key]

        # Add to end (most recently used)
        self.l1_cache[entry.key] = entry

        # Evict if over limit
        while len(self.l1_cache) > self.l1_max_entries:
            evicted_key, evicted_entry = self.l1_cache.popitem(last=False)  # Remove oldest
            self.l1_stats.evictions += 1
            self.l1_stats.total_size_bytes -= evicted_entry.size_bytes

        self.l1_stats.total_size_bytes += entry.size_bytes
        self.l1_stats.entry_count = len(self.l1_cache)

    def _set_l2(self, entry: CacheEntry):
        """Set entry in L2 Redis cache"""
        try:
            data = pickle.dumps(entry)
            ttl = entry.ttl if entry.ttl else 3600  # Default 1 hour
            self.redis_client.setex(f"cache:{entry.key}", ttl, data)
        except Exception as e:
            self.logger.error(f"Redis set error: {e}")

    def _set_disk(self, entry: CacheEntry):
        """Set entry in L3 disk cache"""
        try:
            import os
            cache_file = os.path.join(self.disk_cache_dir, f"{hashlib.md5(entry.key.encode()).hexdigest()}.cache")
            with open(cache_file, 'wb') as f:
                pickle.dump(entry, f)
        except Exception as e:
            self.logger.error(f"Disk set error: {e}")

    def _get_disk(self, key: str) -> Optional[CacheEntry]:
        """Get entry from L3 disk cache"""
        try:
            import os
            cache_file = os.path.join(self.disk_cache_dir, f"{hashlib.md5(key.encode()).hexdigest()}.cache")
            if os.path.exists(cache_file):
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            self.logger.error(f"Disk get error: {e}")
        return None

    def _delete_disk(self, key: str) -> bool:
        """Delete entry from L3 disk cache"""
        try:
            import os
            cache_file = os.path.join(self.disk_cache_dir, f"{hashlib.md5(key.encode()).hexdigest()}.cache")
            if os.path.exists(cache_file):
                os.remove(cache_file)
                return True
        except Exception as e:
            self.logger.error(f"Disk delete error: {e}")
        return False

    def _clear_disk(self):
        """Clear all disk cache"""
        try:
            import os
            if os.path.exists(self.disk_cache_dir):
                for file in os.listdir(self.disk_cache_dir):
                    if file.endswith('.cache'):
                        os.remove(os.path.join(self.disk_cache_dir, file))
        except Exception as e:
            self.logger.error(f"Disk clear error: {e}")

    def _clear_by_tags(self, tags: List[str], level: CacheLevel):
        """Clear cache entries by tags"""
        # This is a simplified implementation
        # In practice, you'd maintain tag-to-key mappings
        pass

    def _calculate_size(self, obj: Any) -> int:
        """Calculate approximate size of object in bytes"""
        try:
            return len(pickle.dumps(obj))
        except:
            return 1024  # Default estimate

    def _record_miss(self, level: CacheLevel):
        """Record cache miss"""
        if level == CacheLevel.L1_MEMORY:
            self.l1_stats.misses += 1
        elif level == CacheLevel.L2_REDIS and self.redis_client:
            self.l2_stats.misses += 1
        elif level == CacheLevel.L3_DISK and self.disk_cache_dir:
            self.l3_stats.misses += 1


class RateLimiter:
    """Advanced rate limiter with multiple algorithms"""

    def __init__(self, requests_per_minute: int = 60, burst_limit: int = 10):
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit

        # Token bucket algorithm
        self.tokens = burst_limit
        self.last_refill = time.time()
        self.refill_rate = requests_per_minute / 60.0  # tokens per second

        # Request history for sliding window
        self.request_times: deque = deque(maxlen=requests_per_minute)

        # Lock for thread safety
        self._lock = threading.Lock()

    def allow_request(self, key: str = "default") -> bool:
        """Check if request is allowed"""
        with self._lock:
            current_time = time.time()

            # Refill tokens (token bucket)
            time_passed = current_time - self.last_refill
            tokens_to_add = time_passed * self.refill_rate
            self.tokens = min(self.burst_limit, self.tokens + tokens_to_add)
            self.last_refill = current_time

            # Check sliding window (last minute)
            # Remove old requests
            cutoff_time = current_time - 60
            while self.request_times and self.request_times[0] < cutoff_time:
                self.request_times.popleft()

            # Check limits
            if len(self.request_times) >= self.requests_per_minute:
                return False

            if self.tokens < 1:
                return False

            # Allow request
            self.tokens -= 1
            self.request_times.append(current_time)
            return True

    def get_remaining_requests(self) -> int:
        """Get remaining requests in current window"""
        with self._lock:
            current_time = time.time()
            cutoff_time = current_time - 60
            while self.request_times and self.request_times[0] < cutoff_time:
                self.request_times.popleft()

            return max(0, self.requests_per_minute - len(self.request_times))

    def reset(self):
        """Reset rate limiter"""
        with self._lock:
            self.tokens = self.burst_limit
            self.request_times.clear()
            self.last_refill = time.time()


class ProcessingPipeline:
    """Scalable processing pipeline with worker pools"""

    def __init__(self, max_workers: int = 4, queue_size: int = 100):
        self.max_workers = max_workers
        self.queue_size = queue_size

        # Processing queue
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=queue_size)

        # Worker tasks
        self.workers: List[asyncio.Task] = []
        self.is_running = False

        # Processing stats
        self.processed_count = 0
        self.failed_count = 0
        self.avg_processing_time = 0
        self.processing_times: deque = deque(maxlen=1000)

        # Middleware
        self.middleware: List[Callable] = []

    async def start(self):
        """Start processing pipeline"""
        self.is_running = True

        # Start workers
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker_loop(i))
            self.workers.append(worker)

        self.logger.info(f"Started processing pipeline with {self.max_workers} workers")

    async def stop(self):
        """Stop processing pipeline"""
        self.is_running = False

        # Cancel workers
        for worker in self.workers:
            worker.cancel()

        # Wait for completion
        await asyncio.gather(*self.workers, return_exceptions=True)

        self.logger.info("Stopped processing pipeline")

    async def submit_task(self, task_func: Callable, *args, **kwargs) -> asyncio.Future:
        """Submit task to processing pipeline"""
        if self.queue.full():
            raise RuntimeError("Processing queue is full")

        future = asyncio.Future()
        await self.queue.put((task_func, args, kwargs, future))
        return future

    async def _worker_loop(self, worker_id: int):
        """Worker processing loop"""
        self.logger = logging.getLogger(f"{__name__}.worker.{worker_id}")

        while self.is_running:
            try:
                # Get task from queue
                task_data = await self.queue.get()

                if not self.is_running:
                    break

                task_func, args, kwargs, future = task_data

                # Process task
                start_time = time.time()
                try:
                    # Apply middleware
                    for middleware_func in self.middleware:
                        task_func = middleware_func(task_func)

                    # Execute task
                    result = await task_func(*args, **kwargs)
                    future.set_result(result)

                    processing_time = time.time() - start_time
                    self.processing_times.append(processing_time)
                    self.processed_count += 1

                    # Update average processing time
                    if len(self.processing_times) > 0:
                        self.avg_processing_time = statistics.mean(self.processing_times)

                except Exception as e:
                    future.set_exception(e)
                    self.failed_count += 1
                    self.logger.error(f"Task processing error: {e}")

                finally:
                    self.queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Worker error: {e}")
                await asyncio.sleep(1)

    def add_middleware(self, middleware_func: Callable):
        """Add processing middleware"""
        self.middleware.append(middleware_func)

    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            'queue_size': self.queue.qsize(),
            'max_queue_size': self.queue_size,
            'active_workers': len([w for w in self.workers if not w.done()]),
            'total_workers': self.max_workers,
            'processed_count': self.processed_count,
            'failed_count': self.failed_count,
            'success_rate': (self.processed_count / (self.processed_count + self.failed_count) * 100) if (self.processed_count + self.failed_count) > 0 else 0,
            'avg_processing_time': self.avg_processing_time,
            'is_running': self.is_running
        }


class PerformanceOptimizer:
    """Main performance optimization system"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Multi-level cache
        self.cache = MultiLevelCache()

        # Rate limiter
        self.rate_limiter = RateLimiter()

        # Processing pipeline
        self.pipeline = ProcessingPipeline()

        # System monitoring
        self.monitoring_active = False
        self.monitoring_task: Optional[asyncio.Task] = None

        # Performance metrics
        self.metrics = {
            'cpu_usage': [],
            'memory_usage': [],
            'cache_performance': {},
            'api_response_times': [],
            'generation_times': [],
            'system_load': []
        }

    async def initialize(self):
        """Initialize performance optimization system"""
        self.logger.info("Initializing performance optimization system")

        # Start processing pipeline
        await self.pipeline.start()

        # Start monitoring
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())

        self.logger.info("Performance optimization system initialized")

    async def shutdown(self):
        """Shutdown performance optimization system"""
        self.logger.info("Shutting down performance optimization system")

        # Stop monitoring
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        # Stop pipeline
        await self.pipeline.stop()

        self.logger.info("Performance optimization system shutdown complete")

    def cached(self, ttl: Optional[int] = None, key_func: Optional[Callable] = None):
        """Decorator for caching function results"""
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    # Default key generation
                    key_data = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
                    cache_key = hashlib.md5(key_data.encode()).hexdigest()

                # Try cache first
                cached_result = self.cache.get(cache_key)
                if cached_result is not None:
                    return cached_result

                # Execute function
                result = await func(*args, **kwargs)

                # Cache result
                self.cache.set(cache_key, result, ttl=ttl)

                return result

            return wrapper
        return decorator

    def rate_limited(self, requests_per_minute: int = 60):
        """Decorator for rate limiting"""
        limiter = RateLimiter(requests_per_minute)

        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                if not limiter.allow_request():
                    raise RuntimeError("Rate limit exceeded")

                return await func(*args, **kwargs)

            return wrapper
        return decorator

    async def submit_task(self, task_func: Callable, *args, **kwargs) -> Any:
        """Submit task to processing pipeline"""
        return await self.pipeline.submit_task(task_func, *args, **kwargs)

    async def _monitoring_loop(self):
        """System monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()

                self.metrics['cpu_usage'].append(cpu_percent)
                self.metrics['memory_usage'].append(memory.percent)
                self.metrics['system_load'].append(psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0)

                # Keep only recent metrics
                for key in self.metrics:
                    if len(self.metrics[key]) > 100:
                        self.metrics[key] = self.metrics[key][-100:]

                # Update cache performance metrics
                self.metrics['cache_performance'] = self.cache.get_stats()

                # Memory management
                if memory.percent > 85:
                    gc.collect()  # Force garbage collection
                    self.logger.warning("High memory usage, triggered garbage collection")

                await asyncio.sleep(30)  # Monitor every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(5)

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        cache_stats = self.cache.get_stats()
        pipeline_stats = self.pipeline.get_stats()

        # Calculate averages
        avg_cpu = statistics.mean(self.metrics['cpu_usage']) if self.metrics['cpu_usage'] else 0
        avg_memory = statistics.mean(self.metrics['memory_usage']) if self.metrics['memory_usage'] else 0
        avg_load = statistics.mean(self.metrics['system_load']) if self.metrics['system_load'] else 0

        return {
            'system_metrics': {
                'avg_cpu_usage': round(avg_cpu, 2),
                'avg_memory_usage': round(avg_memory, 2),
                'avg_system_load': round(avg_load, 2),
                'current_cpu': psutil.cpu_percent(),
                'current_memory': psutil.virtual_memory().percent
            },
            'cache_performance': cache_stats,
            'processing_pipeline': pipeline_stats,
            'rate_limiting': {
                'remaining_requests': self.rate_limiter.get_remaining_requests()
            },
            'memory_info': {
                'gc_stats': gc.get_stats(),
                'object_counts': len(gc.get_objects())
            }
        }

    def optimize_memory(self):
        """Perform memory optimization"""
        # Clear expired cache entries
        # This would be more sophisticated in practice
        gc.collect()

        # Clear old metrics
        cutoff = len(self.metrics['cpu_usage']) - 50  # Keep last 50
        for key in self.metrics:
            if len(self.metrics[key]) > 50:
                self.metrics[key] = self.metrics[key][cutoff:]

        self.logger.info("Memory optimization completed")


# Global instance
_performance_optimizer = None

def get_performance_optimizer() -> PerformanceOptimizer:
    """Get global performance optimizer instance"""
    global _performance_optimizer
    if _performance_optimizer is None:
        _performance_optimizer = PerformanceOptimizer()
    return _performance_optimizer

async def initialize_performance_optimizer() -> PerformanceOptimizer:
    """Initialize the global performance optimizer"""
    global _performance_optimizer
    if _performance_optimizer is None:
        _performance_optimizer = PerformanceOptimizer()
        await _performance_optimizer.initialize()
    return _performance_optimizer</content>
<parameter name="filePath">c:\Users\Baxter\Documents\ComfyUI_env\ComfyUI\custom_nodes\Comfy Gimpy Node Pack\advanced_ai\performance_optimizer.py