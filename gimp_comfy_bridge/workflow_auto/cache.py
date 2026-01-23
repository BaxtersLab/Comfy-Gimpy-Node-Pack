"""
Workflow Cache for ComfyUI workflow caching and versioning.

This module provides intelligent caching of generated workflows to improve
performance and enable workflow versioning.
"""

import asyncio
import hashlib
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import time
import sqlite3
from contextlib import contextmanager

from ..shared.config import Config
from ..shared.types import WorkflowGraph

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry for workflow."""
    key: str
    workflow: WorkflowGraph
    created_at: float
    accessed_at: float
    access_count: int = 0
    size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheStats:
    """Cache statistics."""
    total_entries: int = 0
    total_size_bytes: int = 0
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    hit_rate: float = 0.0


class WorkflowCache:
    """
    Intelligent cache for ComfyUI workflows.

    This class provides caching with versioning, size limits, and automatic
    cleanup to optimize workflow generation performance.
    """

    def __init__(self, config: Config):
        """
        Initialize workflow cache.

        Args:
            config: Application configuration
        """
        self.config = config
        self.max_size_bytes = config.get("workflow_cache_max_size", 100 * 1024 * 1024)  # 100MB
        self.max_entries = config.get("workflow_cache_max_entries", 1000)
        self.ttl_seconds = config.get("workflow_cache_ttl", 7 * 24 * 3600)  # 7 days

        self.cache_dir = config.data_dir / "workflow_cache"
        self.cache_dir.mkdir(exist_ok=True)

        self.db_path = self.cache_dir / "cache.db"
        self._init_db()

        self.memory_cache: Dict[str, CacheEntry] = {}
        self.stats = CacheStats()

        # Start cleanup task
        asyncio.create_task(self._periodic_cleanup())

    def _init_db(self):
        """Initialize SQLite database for persistent caching."""
        with self._get_db_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    workflow_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    accessed_at REAL NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    size_bytes INTEGER DEFAULT 0,
                    metadata TEXT
                )
            ''')

            # Create indexes for performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_accessed_at ON cache_entries(accessed_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON cache_entries(created_at)')

            conn.commit()

    @contextmanager
    def _get_db_connection(self):
        """Get database connection with proper cleanup."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    async def get(self, key: str) -> Optional[WorkflowGraph]:
        """
        Get workflow from cache.

        Args:
            key: Cache key

        Returns:
            WorkflowGraph if found, None otherwise
        """
        # Check memory cache first
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            entry.accessed_at = time.time()
            entry.access_count += 1
            self.stats.hits += 1
            await self._update_db_entry(entry)
            return entry.workflow

        # Check persistent cache
        entry = await self._get_db_entry(key)
        if entry:
            # Add to memory cache
            self.memory_cache[key] = entry
            self.stats.hits += 1
            return entry.workflow

        self.stats.misses += 1
        return None

    async def set(self, key: str, workflow: WorkflowGraph, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Store workflow in cache.

        Args:
            key: Cache key
            workflow: Workflow to cache
            metadata: Optional metadata
        """
        # Calculate size
        workflow_json = json.dumps(workflow.dict() if hasattr(workflow, 'dict') else workflow)
        size_bytes = len(workflow_json.encode('utf-8'))

        # Create cache entry
        entry = CacheEntry(
            key=key,
            workflow=workflow,
            created_at=time.time(),
            accessed_at=time.time(),
            access_count=1,
            size_bytes=size_bytes,
            metadata=metadata or {}
        )

        # Store in memory cache
        self.memory_cache[key] = entry

        # Store in persistent cache
        await self._set_db_entry(entry)

        # Check size limits and cleanup if needed
        await self._enforce_limits()

    async def delete(self, key: str) -> bool:
        """
        Delete workflow from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        deleted = False

        # Remove from memory cache
        if key in self.memory_cache:
            del self.memory_cache[key]
            deleted = True

        # Remove from persistent cache
        if await self._delete_db_entry(key):
            deleted = True

        return deleted

    async def clear(self) -> None:
        """Clear all cache entries."""
        self.memory_cache.clear()
        await self._clear_db()
        self.stats = CacheStats()
        logger.info("Cache cleared")

    async def list_keys(self) -> List[str]:
        """
        List all cache keys.

        Returns:
            List of cache keys
        """
        keys = set(self.memory_cache.keys())

        # Add keys from persistent cache
        with self._get_db_connection() as conn:
            cursor = conn.execute('SELECT key FROM cache_entries')
            for row in cursor:
                keys.add(row[0])

        return list(keys)

    async def get_stats(self) -> CacheStats:
        """
        Get cache statistics.

        Returns:
            CacheStats object
        """
        # Update stats from database
        with self._get_db_connection() as conn:
            cursor = conn.execute('SELECT COUNT(*), SUM(size_bytes) FROM cache_entries')
            row = cursor.fetchone()
            self.stats.total_entries = row[0] or 0
            self.stats.total_size_bytes = row[1] or 0

        # Add memory cache stats
        self.stats.total_entries += len(self.memory_cache)
        for entry in self.memory_cache.values():
            self.stats.total_size_bytes += entry.size_bytes

        # Calculate hit rate
        total_requests = self.stats.hits + self.stats.misses
        if total_requests > 0:
            self.stats.hit_rate = self.stats.hits / total_requests

        return self.stats

    async def _get_db_entry(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry from database."""
        with self._get_db_connection() as conn:
            cursor = conn.execute(
                'SELECT workflow_json, created_at, accessed_at, access_count, size_bytes, metadata FROM cache_entries WHERE key = ?',
                (key,)
            )
            row = cursor.fetchone()

            if row:
                workflow_data = json.loads(row[0])
                # Convert dict back to WorkflowGraph
                workflow = WorkflowGraph(**workflow_data)

                entry = CacheEntry(
                    key=key,
                    workflow=workflow,
                    created_at=row[1],
                    accessed_at=row[2],
                    access_count=row[3],
                    size_bytes=row[4],
                    metadata=json.loads(row[5]) if row[5] else {}
                )

                # Update access time
                conn.execute(
                    'UPDATE cache_entries SET accessed_at = ?, access_count = access_count + 1 WHERE key = ?',
                    (time.time(), key)
                )
                conn.commit()

                return entry

        return None

    async def _set_db_entry(self, entry: CacheEntry) -> None:
        """Store cache entry in database."""
        workflow_json = json.dumps(entry.workflow.dict() if hasattr(entry.workflow, 'dict') else entry.workflow)
        metadata_json = json.dumps(entry.metadata)

        with self._get_db_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO cache_entries
                (key, workflow_json, created_at, accessed_at, access_count, size_bytes, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                entry.key, workflow_json, entry.created_at, entry.accessed_at,
                entry.access_count, entry.size_bytes, metadata_json
            ))
            conn.commit()

    async def _update_db_entry(self, entry: CacheEntry) -> None:
        """Update cache entry in database."""
        with self._get_db_connection() as conn:
            conn.execute('''
                UPDATE cache_entries
                SET accessed_at = ?, access_count = ?
                WHERE key = ?
            ''', (entry.accessed_at, entry.access_count, entry.key))
            conn.commit()

    async def _delete_db_entry(self, key: str) -> bool:
        """Delete cache entry from database."""
        with self._get_db_connection() as conn:
            cursor = conn.execute('DELETE FROM cache_entries WHERE key = ?', (key,))
            conn.commit()
            return cursor.rowcount > 0

    async def _clear_db(self) -> None:
        """Clear all entries from database."""
        with self._get_db_connection() as conn:
            conn.execute('DELETE FROM cache_entries')
            conn.commit()

    async def _enforce_limits(self) -> None:
        """Enforce cache size and entry limits."""
        # Check size limit
        stats = await self.get_stats()
        if stats.total_size_bytes > self.max_size_bytes:
            await self._cleanup_by_size()

        # Check entry limit
        if stats.total_entries > self.max_entries:
            await self._cleanup_by_count()

    async def _cleanup_by_size(self) -> None:
        """Clean up cache by removing oldest entries until under size limit."""
        target_size = self.max_size_bytes * 0.8  # Target 80% of max size

        with self._get_db_connection() as conn:
            # Get entries sorted by access time (oldest first)
            cursor = conn.execute('''
                SELECT key, size_bytes FROM cache_entries
                ORDER BY accessed_at ASC
            ''')

            to_delete = []
            current_size = self.stats.total_size_bytes

            for row in cursor:
                if current_size <= target_size:
                    break
                to_delete.append(row[0])
                current_size -= row[1]

            # Delete entries
            if to_delete:
                placeholders = ','.join('?' * len(to_delete))
                conn.execute(f'DELETE FROM cache_entries WHERE key IN ({placeholders})', to_delete)
                conn.commit()

                self.stats.evictions += len(to_delete)
                logger.info(f"Evicted {len(to_delete)} cache entries by size")

    async def _cleanup_by_count(self) -> None:
        """Clean up cache by removing oldest entries until under count limit."""
        target_count = int(self.max_entries * 0.8)  # Target 80% of max entries

        with self._get_db_connection() as conn:
            # Get entries to delete (oldest first)
            cursor = conn.execute('''
                SELECT key FROM cache_entries
                ORDER BY accessed_at ASC
                LIMIT ?
            ''', (self.stats.total_entries - target_count,))

            to_delete = [row[0] for row in cursor]

            # Delete entries
            if to_delete:
                placeholders = ','.join('?' * len(to_delete))
                conn.execute(f'DELETE FROM cache_entries WHERE key IN ({placeholders})', to_delete)
                conn.commit()

                self.stats.evictions += len(to_delete)
                logger.info(f"Evicted {len(to_delete)} cache entries by count")

    async def _cleanup_expired(self) -> None:
        """Clean up expired cache entries."""
        cutoff_time = time.time() - self.ttl_seconds

        with self._get_db_connection() as conn:
            cursor = conn.execute('DELETE FROM cache_entries WHERE created_at < ?', (cutoff_time,))
            deleted_count = cursor.rowcount
            conn.commit()

            if deleted_count > 0:
                self.stats.evictions += deleted_count
                logger.info(f"Cleaned up {deleted_count} expired cache entries")

    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup task."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                await self._cleanup_expired()
                await self._enforce_limits()
            except Exception as e:
                logger.error(f"Error in periodic cache cleanup: {e}")

    def generate_cache_key(self, *args, **kwargs) -> str:
        """
        Generate a cache key from arguments.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Cache key string
        """
        # Create a deterministic string representation
        key_parts = []

        for arg in args:
            if hasattr(arg, 'dict'):
                key_parts.append(json.dumps(arg.dict(), sort_keys=True))
            else:
                key_parts.append(str(arg))

        for k, v in sorted(kwargs.items()):
            if hasattr(v, 'dict'):
                key_parts.append(f"{k}:{json.dumps(v.dict(), sort_keys=True)}")
            else:
                key_parts.append(f"{k}:{v}")

        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    async def preload_cache(self, keys: List[str]) -> None:
        """
        Preload cache entries into memory.

        Args:
            keys: List of cache keys to preload
        """
        for key in keys:
            if key not in self.memory_cache:
                entry = await self._get_db_entry(key)
                if entry:
                    self.memory_cache[key] = entry

    async def export_cache(self, filepath: Path) -> None:
        """
        Export cache to file.

        Args:
            filepath: Export file path
        """
        cache_data = {
            "version": "1.0",
            "exported_at": time.time(),
            "entries": []
        }

        with self._get_db_connection() as conn:
            cursor = conn.execute('SELECT * FROM cache_entries')
            for row in cursor:
                cache_data["entries"].append({
                    "key": row[0],
                    "workflow_json": row[1],
                    "created_at": row[2],
                    "accessed_at": row[3],
                    "access_count": row[4],
                    "size_bytes": row[5],
                    "metadata": json.loads(row[6]) if row[6] else {}
                })

        with open(filepath, 'w') as f:
            json.dump(cache_data, f, indent=2)

        logger.info(f"Exported {len(cache_data['entries'])} cache entries to {filepath}")

    async def import_cache(self, filepath: Path) -> None:
        """
        Import cache from file.

        Args:
            filepath: Import file path
        """
        with open(filepath, 'r') as f:
            cache_data = json.load(f)

        imported_count = 0
        with self._get_db_connection() as conn:
            for entry_data in cache_data.get("entries", []):
                try:
                    conn.execute('''
                        INSERT OR IGNORE INTO cache_entries
                        (key, workflow_json, created_at, accessed_at, access_count, size_bytes, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        entry_data["key"],
                        entry_data["workflow_json"],
                        entry_data["created_at"],
                        entry_data["accessed_at"],
                        entry_data["access_count"],
                        entry_data["size_bytes"],
                        json.dumps(entry_data["metadata"])
                    ))
                    imported_count += 1
                except Exception as e:
                    logger.warning(f"Failed to import cache entry {entry_data['key']}: {e}")

            conn.commit()

        logger.info(f"Imported {imported_count} cache entries from {filepath}")