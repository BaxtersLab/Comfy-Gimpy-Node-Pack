"""
Task storage implementation using SQLite.
"""

import sqlite3
import json
import threading
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from .task import Task


class TaskStorage:
    """
    SQLite-based persistent storage for tasks.

    Handles task persistence, recovery, and querying.
    """

    def __init__(self, db_path: Path):
        """
        Initialize task storage.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper cleanup."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    parameters TEXT NOT NULL,  -- JSON
                    progress TEXT NOT NULL,    -- JSON
                    result TEXT,               -- JSON, nullable
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    timeout_seconds INTEGER,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 3,
                    dependencies TEXT NOT NULL,  -- JSON array
                    metadata TEXT NOT NULL      -- JSON
                )
            ''')

            # Create indexes for performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_state ON tasks(state)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at)')

            conn.commit()

    def save_task(self, task: Task):
        """
        Save a task to storage.

        Args:
            task: Task to save
        """
        with self._lock:
            with self._get_connection() as conn:
                task_dict = task.to_dict()

                conn.execute('''
                    INSERT OR REPLACE INTO tasks (
                        id, type, priority, state, parameters, progress, result,
                        created_at, started_at, completed_at, timeout_seconds,
                        retry_count, max_retries, dependencies, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task_dict['id'],
                    task_dict['type'],
                    task_dict['priority'],
                    task_dict['state'],
                    json.dumps(task_dict['parameters']),
                    json.dumps(task_dict['progress']),
                    json.dumps(task_dict['result']) if task_dict['result'] else None,
                    task_dict['created_at'],
                    task_dict['started_at'],
                    task_dict['completed_at'],
                    task_dict['timeout_seconds'],
                    task_dict['retry_count'],
                    task_dict['max_retries'],
                    json.dumps(task_dict['dependencies']),
                    json.dumps(task_dict['metadata'])
                ))

                conn.commit()

    def load_task(self, task_id: str) -> Optional[Task]:
        """
        Load a task from storage.

        Args:
            task_id: Task ID to load

        Returns:
            Task if found, None otherwise
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
                row = cursor.fetchone()

                if not row:
                    return None

                return self._row_to_task(row)

    def load_all_tasks(self) -> List[Task]:
        """
        Load all tasks from storage.

        Returns:
            List of all tasks
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute('SELECT * FROM tasks ORDER BY created_at DESC')
                rows = cursor.fetchall()

                return [self._row_to_task(row) for row in rows]

    def load_tasks_by_state(self, state: str) -> List[Task]:
        """
        Load tasks by state.

        Args:
            state: Task state to filter by

        Returns:
            List of tasks in the specified state
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute('SELECT * FROM tasks WHERE state = ? ORDER BY created_at DESC', (state,))
                rows = cursor.fetchall()

                return [self._row_to_task(row) for row in rows]

    def load_tasks_by_type(self, task_type: str) -> List[Task]:
        """
        Load tasks by type.

        Args:
            task_type: Task type to filter by

        Returns:
            List of tasks of the specified type
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute('SELECT * FROM tasks WHERE type = ? ORDER BY created_at DESC', (task_type,))
                rows = cursor.fetchall()

                return [self._row_to_task(row) for row in rows]

    def delete_task(self, task_id: str) -> bool:
        """
        Delete a task from storage.

        Args:
            task_id: Task ID to delete

        Returns:
            True if task was deleted, False if not found
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
                conn.commit()

                return cursor.rowcount > 0

    def delete_completed_tasks(self, older_than_days: int = 30) -> int:
        """
        Delete completed tasks older than specified days.

        Args:
            older_than_days: Delete tasks older than this many days

        Returns:
            Number of tasks deleted
        """
        with self._lock:
            with self._get_connection() as conn:
                # Calculate cutoff date
                import datetime
                cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=older_than_days)).isoformat()

                cursor = conn.execute('''
                    DELETE FROM tasks
                    WHERE state IN ('completed', 'failed', 'cancelled', 'timeout')
                    AND completed_at < ?
                ''', (cutoff_date,))

                conn.commit()

                return cursor.rowcount

    def get_task_stats(self) -> Dict[str, Any]:
        """
        Get task statistics.

        Returns:
            Dictionary with task statistics
        """
        with self._lock:
            with self._get_connection() as conn:
                # Count by state
                cursor = conn.execute('SELECT state, COUNT(*) FROM tasks GROUP BY state')
                state_counts = {row[0]: row[1] for row in cursor.fetchall()}

                # Count by type
                cursor = conn.execute('SELECT type, COUNT(*) FROM tasks GROUP BY type')
                type_counts = {row[0]: row[1] for row in cursor.fetchall()}

                # Total count
                cursor = conn.execute('SELECT COUNT(*) FROM tasks')
                total_count = cursor.fetchone()[0]

                return {
                    'total': total_count,
                    'by_state': state_counts,
                    'by_type': type_counts
                }

    def _row_to_task(self, row) -> Task:
        """
        Convert database row to Task object.

        Args:
            row: Database row

        Returns:
            Task object
        """
        (task_id, task_type, priority, state, parameters_json, progress_json,
         result_json, created_at, started_at, completed_at, timeout_seconds,
         retry_count, max_retries, dependencies_json, metadata_json) = row

        # Parse JSON fields
        parameters = json.loads(parameters_json)
        progress = json.loads(progress_json)
        result = json.loads(result_json) if result_json else None
        dependencies = json.loads(dependencies_json)
        metadata = json.loads(metadata_json)

        # Build task dict
        task_dict = {
            'id': task_id,
            'type': task_type,
            'priority': priority,
            'state': state,
            'parameters': parameters,
            'progress': progress,
            'result': result,
            'created_at': created_at,
            'started_at': started_at,
            'completed_at': completed_at,
            'timeout_seconds': timeout_seconds,
            'retry_count': retry_count,
            'max_retries': max_retries,
            'dependencies': dependencies,
            'metadata': metadata
        }

        return Task.from_dict(task_dict)