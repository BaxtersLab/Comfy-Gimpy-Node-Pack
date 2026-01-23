"""
Conflict Resolution Strategies.

Provides various strategies for resolving sync conflicts between local and remote files.
"""

import logging
import difflib
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ConflictType(Enum):
    """Types of sync conflicts."""
    MODIFIED_BOTH = "modified_both"
    DELETED_LOCALLY = "deleted_locally"
    DELETED_REMOTELY = "deleted_remotely"
    TYPE_CHANGED = "type_changed"


@dataclass
class ConflictItem:
    """Represents a conflicting item in sync."""
    path: str
    local_info: Optional[Dict[str, Any]] = None
    remote_info: Optional[Dict[str, Any]] = None
    conflict_type: ConflictType = ConflictType.MODIFIED_BOTH
    detected_at: datetime = None

    def __post_init__(self):
        if self.detected_at is None:
            self.detected_at = datetime.now()


class ConflictResolver:
    """
    Handles conflict resolution for sync operations.

    Provides multiple strategies for resolving conflicts between
    local and remote versions of files.
    """

    def __init__(self):
        """Initialize the conflict resolver."""
        self.resolvers = {
            'local_wins': self._resolve_local_wins,
            'remote_wins': self._resolve_remote_wins,
            'newer_wins': self._resolve_newer_wins,
            'manual': self._resolve_manual,
            'merge': self._resolve_merge,
            'backup_local': self._resolve_backup_local,
            'backup_remote': self._resolve_backup_remote
        }

    def resolve_conflict(self,
                        conflict: ConflictItem,
                        strategy: str,
                        **kwargs) -> Dict[str, Any]:
        """
        Resolve a sync conflict using the specified strategy.

        Args:
            conflict: Conflict to resolve
            strategy: Resolution strategy name
            **kwargs: Additional parameters for resolution

        Returns:
            Resolution result with action and details
        """
        resolver = self.resolvers.get(strategy)
        if not resolver:
            raise ValueError(f"Unknown conflict resolution strategy: {strategy}")

        try:
            return resolver(conflict, **kwargs)
        except Exception as e:
            logger.error(f"Error resolving conflict with strategy {strategy}: {e}")
            return {
                'action': 'error',
                'error': str(e),
                'strategy': strategy
            }

    def _resolve_local_wins(self, conflict: ConflictItem, **kwargs) -> Dict[str, Any]:
        """
        Resolve conflict by keeping the local version.

        Args:
            conflict: Conflict item

        Returns:
            Resolution result
        """
        return {
            'action': 'use_local',
            'strategy': 'local_wins',
            'reason': 'Local version preferred'
        }

    def _resolve_remote_wins(self, conflict: ConflictItem, **kwargs) -> Dict[str, Any]:
        """
        Resolve conflict by keeping the remote version.

        Args:
            conflict: Conflict item

        Returns:
            Resolution result
        """
        return {
            'action': 'use_remote',
            'strategy': 'remote_wins',
            'reason': 'Remote version preferred'
        }

    def _resolve_newer_wins(self, conflict: ConflictItem, **kwargs) -> Dict[str, Any]:
        """
        Resolve conflict by keeping the newer version.

        Args:
            conflict: Conflict item

        Returns:
            Resolution result
        """
        if not conflict.local_info or not conflict.remote_info:
            # If one side is missing, use the other
            if conflict.local_info:
                return self._resolve_local_wins(conflict)
            else:
                return self._resolve_remote_wins(conflict)

        local_time = conflict.local_info.get('modified_time')
        remote_time = conflict.remote_info.get('modified_time')

        if isinstance(local_time, str):
            local_time = datetime.fromisoformat(local_time.replace('Z', '+00:00'))
        if isinstance(remote_time, str):
            remote_time = datetime.fromisoformat(remote_time.replace('Z', '+00:00'))

        if local_time > remote_time:
            return {
                'action': 'use_local',
                'strategy': 'newer_wins',
                'reason': f'Local version is newer ({local_time} > {remote_time})'
            }
        else:
            return {
                'action': 'use_remote',
                'strategy': 'newer_wins',
                'reason': f'Remote version is newer ({remote_time} > {local_time})'
            }

    def _resolve_manual(self, conflict: ConflictItem, **kwargs) -> Dict[str, Any]:
        """
        Require manual resolution of the conflict.

        Args:
            conflict: Conflict item

        Returns:
            Resolution result requiring manual intervention
        """
        return {
            'action': 'manual_required',
            'strategy': 'manual',
            'reason': 'Manual resolution required',
            'conflict_details': {
                'path': conflict.path,
                'type': conflict.conflict_type.value,
                'local_info': conflict.local_info,
                'remote_info': conflict.remote_info
            }
        }

    def _resolve_merge(self, conflict: ConflictItem, **kwargs) -> Dict[str, Any]:
        """
        Attempt to merge conflicting versions.

        Args:
            conflict: Conflict item

        Returns:
            Resolution result with merged content
        """
        if conflict.conflict_type != ConflictType.MODIFIED_BOTH:
            # Only merge modified files
            return self._resolve_newer_wins(conflict)

        # Check if files are text-based and can be merged
        local_path = kwargs.get('local_path')
        remote_path = kwargs.get('remote_path')

        if not local_path or not remote_path:
            logger.warning("Cannot merge without file paths")
            return self._resolve_manual(conflict)

        try:
            # Attempt text merge
            merged_content = self._merge_text_files(local_path, remote_path)
            if merged_content is not None:
                return {
                    'action': 'merge',
                    'strategy': 'merge',
                    'reason': 'Files successfully merged',
                    'merged_content': merged_content
                }
            else:
                # Merge failed, fall back to manual
                return self._resolve_manual(conflict)

        except Exception as e:
            logger.error(f"Merge failed: {e}")
            return self._resolve_manual(conflict)

    def _resolve_backup_local(self, conflict: ConflictItem, **kwargs) -> Dict[str, Any]:
        """
        Backup local version and use remote.

        Args:
            conflict: Conflict item

        Returns:
            Resolution result with backup action
        """
        backup_path = kwargs.get('backup_path', f"{conflict.path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}")

        return {
            'action': 'backup_local_use_remote',
            'strategy': 'backup_local',
            'reason': 'Local version backed up, using remote',
            'backup_path': backup_path
        }

    def _resolve_backup_remote(self, conflict: ConflictItem, **kwargs) -> Dict[str, Any]:
        """
        Backup remote version and use local.

        Args:
            conflict: Conflict item

        Returns:
            Resolution result with backup action
        """
        backup_path = kwargs.get('backup_path', f"{conflict.path}.remote_backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}")

        return {
            'action': 'backup_remote_use_local',
            'strategy': 'backup_remote',
            'reason': 'Remote version backed up, using local',
            'backup_path': backup_path
        }

    def _merge_text_files(self, local_path: str, remote_path: str) -> Optional[str]:
        """
        Attempt to merge two text files.

        Args:
            local_path: Local file path
            remote_path: Remote file path

        Returns:
            Merged content or None if merge failed
        """
        try:
            # Read both files
            with open(local_path, 'r', encoding='utf-8') as f:
                local_content = f.read()
            with open(remote_path, 'r', encoding='utf-8') as f:
                remote_content = f.read()

            # Split into lines
            local_lines = local_content.splitlines(keepends=True)
            remote_lines = remote_content.splitlines(keepends=True)

            # Use difflib for merging
            merger = difflib.unified_diff(local_lines, remote_lines,
                                        fromfile='local', tofile='remote',
                                        lineterm='', n=0)

            # Check if there are conflicts (lines starting with + or -)
            diff_lines = list(merger)
            has_conflicts = any(line.startswith(('+', '-')) for line in diff_lines)

            if has_conflicts:
                # Cannot auto-merge, return None
                return None

            # Simple merge: combine non-conflicting changes
            # This is a basic implementation - real merge would be more complex
            merged_lines = []
            local_idx = remote_idx = 0

            while local_idx < len(local_lines) and remote_idx < len(remote_lines):
                if local_lines[local_idx] == remote_lines[remote_idx]:
                    merged_lines.append(local_lines[local_idx])
                    local_idx += 1
                    remote_idx += 1
                elif local_lines[local_idx] < remote_lines[remote_idx]:
                    merged_lines.append(local_lines[local_idx])
                    local_idx += 1
                else:
                    merged_lines.append(remote_lines[remote_idx])
                    remote_idx += 1

            # Add remaining lines
            merged_lines.extend(local_lines[local_idx:])
            merged_lines.extend(remote_lines[remote_idx:])

            return ''.join(merged_lines)

        except Exception as e:
            logger.error(f"Text merge failed: {e}")
            return None

    def detect_conflicts(self,
                        local_items: List[Dict[str, Any]],
                        remote_items: List[Dict[str, Any]]) -> List[ConflictItem]:
        """
        Detect conflicts between local and remote item lists.

        Args:
            local_items: List of local items
            remote_items: List of remote items

        Returns:
            List of detected conflicts
        """
        conflicts = []

        # Create lookup dictionaries
        local_lookup = {item['path']: item for item in local_items}
        remote_lookup = {item['path']: item for item in remote_items}

        # Find all unique paths
        all_paths = set(local_lookup.keys()) | set(remote_lookup.keys())

        for path in all_paths:
            local_info = local_lookup.get(path)
            remote_info = remote_lookup.get(path)

            conflict_type = self._determine_conflict_type(local_info, remote_info)
            if conflict_type:
                conflict = ConflictItem(
                    path=path,
                    local_info=local_info,
                    remote_info=remote_info,
                    conflict_type=conflict_type
                )
                conflicts.append(conflict)

        return conflicts

    def _determine_conflict_type(self,
                                local_info: Optional[Dict[str, Any]],
                                remote_info: Optional[Dict[str, Any]]) -> Optional[ConflictType]:
        """
        Determine the type of conflict between local and remote items.

        Args:
            local_info: Local item information
            remote_info: Remote item information

        Returns:
            Conflict type or None if no conflict
        """
        if local_info and remote_info:
            # Both exist - check for modifications
            local_modified = local_info.get('modified_time')
            remote_modified = remote_info.get('modified_time')

            if isinstance(local_modified, str):
                local_modified = datetime.fromisoformat(local_modified.replace('Z', '+00:00'))
            if isinstance(remote_modified, str):
                remote_modified = datetime.fromisoformat(remote_modified.replace('Z', '+00:00'))

            # If both have been modified since last sync, it's a conflict
            if local_modified and remote_modified:
                # This is a simplified check - in practice, you'd need last sync time
                if abs((local_modified - remote_modified).total_seconds()) > 1:  # 1 second tolerance
                    return ConflictType.MODIFIED_BOTH

            # Check if types changed
            local_is_dir = local_info.get('is_directory', False)
            remote_is_dir = remote_info.get('is_directory', False)
            if local_is_dir != remote_is_dir:
                return ConflictType.TYPE_CHANGED

        elif local_info and not remote_info:
            # Exists locally but not remotely - check if it was deleted remotely
            return ConflictType.DELETED_REMOTELY

        elif not local_info and remote_info:
            # Exists remotely but not locally - check if it was deleted locally
            return ConflictType.DELETED_LOCALLY

        return None

    def get_available_strategies(self) -> List[str]:
        """
        Get list of available conflict resolution strategies.

        Returns:
            List of strategy names
        """
        return list(self.resolvers.keys())

    def validate_strategy(self, strategy: str) -> bool:
        """
        Validate if a conflict resolution strategy is available.

        Args:
            strategy: Strategy name

        Returns:
            True if strategy is valid
        """
        return strategy in self.resolvers