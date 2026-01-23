"""
Pack registry for managing installed packs and metadata.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import json
import sqlite3
from datetime import datetime
import threading

logger = logging.getLogger(__name__)


class PackRegistry:
    """Registry for managing installed packs and their metadata."""

    def __init__(self, registry_path: Optional[Path] = None):
        self.registry_path = registry_path or Path("data/pack_registry.db")
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_database()

    def _init_database(self):
        """Initialize the SQLite database."""
        with self._lock:
            with sqlite3.connect(self.registry_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS packs (
                        id TEXT PRIMARY KEY,
                        type TEXT NOT NULL,
                        name TEXT NOT NULL,
                        version TEXT NOT NULL,
                        installed_at TEXT NOT NULL,
                        manifest TEXT NOT NULL,
                        status TEXT DEFAULT 'active'
                    )
                ''')

                conn.execute('''
                    CREATE TABLE IF NOT EXISTS pack_files (
                        pack_id TEXT,
                        file_path TEXT,
                        file_type TEXT,
                        checksum TEXT,
                        FOREIGN KEY (pack_id) REFERENCES packs (id)
                    )
                ''')

                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_pack_type ON packs (type)
                ''')

                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_pack_name ON packs (name)
                ''')

                conn.commit()

    def register_pack(self, manifest: Dict[str, Any], install_path: Optional[Path] = None) -> bool:
        """
        Register a pack in the registry.

        Args:
            manifest: Pack manifest
            install_path: Installation path (optional)

        Returns:
            True if registered successfully
        """
        pack_id = manifest["id"]

        with self._lock:
            try:
                with sqlite3.connect(self.registry_path) as conn:
                    # Check if pack already exists
                    existing = conn.execute(
                        "SELECT id FROM packs WHERE id = ?",
                        (pack_id,)
                    ).fetchone()

                    if existing:
                        logger.warning(f"Pack already registered: {pack_id}")
                        return False

                    # Insert pack
                    conn.execute('''
                        INSERT INTO packs (id, type, name, version, installed_at, manifest, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        pack_id,
                        manifest["type"],
                        manifest["name"],
                        manifest["version"],
                        datetime.now().isoformat(),
                        json.dumps(manifest),
                        "active"
                    ))

                    # Register files if install_path provided
                    if install_path:
                        self._register_pack_files(conn, pack_id, manifest, install_path)

                    conn.commit()

                logger.info(f"Pack registered: {pack_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to register pack {pack_id}: {e}")
                return False

    def unregister_pack(self, pack_id: str) -> bool:
        """
        Unregister a pack from the registry.

        Args:
            pack_id: Pack ID to unregister

        Returns:
            True if unregistered successfully
        """
        with self._lock:
            try:
                with sqlite3.connect(self.registry_path) as conn:
                    # Mark as inactive instead of deleting
                    conn.execute(
                        "UPDATE packs SET status = 'inactive' WHERE id = ?",
                        (pack_id,)
                    )
                    conn.commit()

                logger.info(f"Pack unregistered: {pack_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to unregister pack {pack_id}: {e}")
                return False

    def get_pack(self, pack_id: str) -> Optional[Dict[str, Any]]:
        """
        Get pack information by ID.

        Args:
            pack_id: Pack ID

        Returns:
            Pack information or None if not found
        """
        with self._lock:
            try:
                with sqlite3.connect(self.registry_path) as conn:
                    row = conn.execute(
                        "SELECT * FROM packs WHERE id = ? AND status = 'active'",
                        (pack_id,)
                    ).fetchone()

                    if row:
                        pack_info = {
                            "id": row[0],
                            "type": row[1],
                            "name": row[2],
                            "version": row[3],
                            "installed_at": row[4],
                            "manifest": json.loads(row[5]),
                            "status": row[6]
                        }
                        return pack_info

            except Exception as e:
                logger.error(f"Failed to get pack {pack_id}: {e}")

        return None

    def list_packs(self,
                  pack_type: Optional[str] = None,
                  status: str = "active") -> List[Dict[str, Any]]:
        """
        List packs with optional filtering.

        Args:
            pack_type: Filter by pack type (optional)
            status: Filter by status (default: "active")

        Returns:
            List of pack information
        """
        packs = []

        with self._lock:
            try:
                with sqlite3.connect(self.registry_path) as conn:
                    query = "SELECT * FROM packs WHERE status = ?"
                    params = [status]

                    if pack_type:
                        query += " AND type = ?"
                        params.append(pack_type)

                    rows = conn.execute(query, params).fetchall()

                    for row in rows:
                        pack_info = {
                            "id": row[0],
                            "type": row[1],
                            "name": row[2],
                            "version": row[3],
                            "installed_at": row[4],
                            "manifest": json.loads(row[5]),
                            "status": row[6]
                        }
                        packs.append(pack_info)

            except Exception as e:
                logger.error(f"Failed to list packs: {e}")

        return packs

    def search_packs(self,
                    query: str,
                    pack_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search packs by name or description.

        Args:
            query: Search query
            pack_type: Filter by pack type (optional)

        Returns:
            List of matching packs
        """
        packs = []
        query_lower = query.lower()

        with self._lock:
            try:
                with sqlite3.connect(self.registry_path) as conn:
                    sql_query = """
                        SELECT * FROM packs
                        WHERE status = 'active'
                        AND (LOWER(name) LIKE ? OR LOWER(json_extract(manifest, '$.description')) LIKE ?)
                    """
                    params = [f"%{query_lower}%", f"%{query_lower}%"]

                    if pack_type:
                        sql_query += " AND type = ?"
                        params.append(pack_type)

                    rows = conn.execute(sql_query, params).fetchall()

                    for row in rows:
                        pack_info = {
                            "id": row[0],
                            "type": row[1],
                            "name": row[2],
                            "version": row[3],
                            "installed_at": row[4],
                            "manifest": json.loads(row[5]),
                            "status": row[6]
                        }
                        packs.append(pack_info)

            except Exception as e:
                logger.error(f"Failed to search packs: {e}")

        return packs

    def get_pack_dependencies(self, pack_id: str) -> List[Dict[str, Any]]:
        """
        Get dependencies for a pack.

        Args:
            pack_id: Pack ID

        Returns:
            List of dependencies
        """
        pack = self.get_pack(pack_id)
        if pack:
            manifest = pack["manifest"]
            return manifest.get("dependencies", [])
        return []

    def check_dependency_satisfaction(self, pack_id: str) -> Dict[str, Any]:
        """
        Check if a pack's dependencies are satisfied.

        Args:
            pack_id: Pack ID

        Returns:
            Dependency satisfaction status
        """
        dependencies = self.get_pack_dependencies(pack_id)
        satisfied = []
        missing = []

        for dep in dependencies:
            dep_name = dep["name"]
            dep_version = dep["version"]

            # Check if dependency is installed
            installed_packs = self.list_packs(pack_type=dep.get("type"))
            found = False

            for pack in installed_packs:
                if pack["name"] == dep_name and pack["version"] == dep_version:
                    satisfied.append(dep)
                    found = True
                    break

            if not found:
                missing.append(dep)

        return {
            "satisfied": satisfied,
            "missing": missing,
            "all_satisfied": len(missing) == 0
        }

    def get_pack_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            Statistics about registered packs
        """
        stats = {
            "total_packs": 0,
            "packs_by_type": {},
            "total_size": 0,
            "last_updated": None
        }

        with self._lock:
            try:
                with sqlite3.connect(self.registry_path) as conn:
                    # Count packs by type
                    rows = conn.execute(
                        "SELECT type, COUNT(*) FROM packs WHERE status = 'active' GROUP BY type"
                    ).fetchall()

                    for row in rows:
                        pack_type, count = row
                        stats["packs_by_type"][pack_type] = count
                        stats["total_packs"] += count

                    # Get last update time
                    row = conn.execute(
                        "SELECT MAX(installed_at) FROM packs WHERE status = 'active'"
                    ).fetchone()

                    if row and row[0]:
                        stats["last_updated"] = row[0]

            except Exception as e:
                logger.error(f"Failed to get pack stats: {e}")

        return stats

    def _register_pack_files(self,
                           conn: sqlite3.Connection,
                           pack_id: str,
                           manifest: Dict[str, Any],
                           install_path: Path):
        """Register pack files in the database."""
        try:
            # Register content files
            content = manifest.get("content", {})
            if isinstance(content, dict) and "files" in content:
                for file_info in content["files"]:
                    file_path = file_info.get("path")
                    if file_path:
                        conn.execute('''
                            INSERT INTO pack_files (pack_id, file_path, file_type, checksum)
                            VALUES (?, ?, ?, ?)
                        ''', (
                            pack_id,
                            file_path,
                            "content",
                            file_info.get("checksum", "")
                        ))

            # Register preview files
            for preview in manifest.get("previews", []):
                conn.execute('''
                    INSERT INTO pack_files (pack_id, file_path, file_type, checksum)
                    VALUES (?, ?, ?, ?)
                ''', (
                    pack_id,
                    f"previews/{preview['filename']}",
                    "preview",
                    preview.get("checksum", "")
                ))

        except Exception as e:
            logger.warning(f"Failed to register pack files for {pack_id}: {e}")


# Global registry instance
_pack_registry: Optional[PackRegistry] = None


def get_pack_registry() -> PackRegistry:
    """Get the global pack registry instance."""
    global _pack_registry
    if _pack_registry is None:
        _pack_registry = PackRegistry()
    return _pack_registry