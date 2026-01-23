"""
Sync Manager.

Orchestrates synchronization operations across multiple providers with conflict resolution.
"""

import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from .provider import SyncProvider, SyncResult
from .local_provider import LocalSyncProvider
from .http_provider import HttpSyncProvider
from ..shared.config import ConfigManager
from ..shared.types import SyncConfig, SyncStatus

logger = logging.getLogger(__name__)


class ConflictResolution(Enum):
    """Conflict resolution strategies."""
    LOCAL_WINS = "local_wins"
    REMOTE_WINS = "remote_wins"
    NEWER_WINS = "newer_wins"
    MANUAL = "manual"
    MERGE = "merge"


@dataclass
class SyncJob:
    """Represents a sync job."""
    job_id: str
    local_path: str
    remote_path: str
    provider_name: str
    direction: str = "bidirectional"
    exclude_patterns: List[str] = field(default_factory=list)
    conflict_resolution: ConflictResolution = ConflictResolution.NEWER_WINS
    scheduled_time: Optional[datetime] = None
    status: str = "pending"
    result: Optional[SyncResult] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class SyncConflict:
    """Represents a sync conflict."""
    local_path: str
    remote_path: str
    local_modified: datetime
    remote_modified: datetime
    local_size: int
    remote_size: int
    resolution: Optional[ConflictResolution] = None


class SyncManager:
    """
    Manages synchronization operations across multiple storage providers.

    Handles provider management, job scheduling, conflict resolution,
    and sync orchestration.
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the sync manager.

        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.providers: Dict[str, SyncProvider] = {}
        self.jobs: Dict[str, SyncJob] = {}
        self.active_jobs: Dict[str, asyncio.Task] = {}
        self.conflicts: List[SyncConflict] = []

        # Load configuration
        self.sync_config = self.config_manager.get_sync_config()

        # Initialize providers
        self._initialize_providers()

        # Start background tasks
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None

    def _initialize_providers(self):
        """Initialize configured sync providers."""
        for provider_config in self.sync_config.providers:
            try:
                provider = self._create_provider(provider_config)
                if provider:
                    self.providers[provider_config.name] = provider
                    logger.info(f"Initialized sync provider: {provider_config.name}")
            except Exception as e:
                logger.error(f"Failed to initialize provider {provider_config.name}: {e}")

    def _create_provider(self, config: SyncConfig.ProviderConfig) -> Optional[SyncProvider]:
        """
        Create a sync provider instance.

        Args:
            config: Provider configuration

        Returns:
            Provider instance or None if creation failed
        """
        provider_type = config.type.lower()

        if provider_type == "local":
            return LocalSyncProvider(config.settings)
        elif provider_type == "http":
            return HttpSyncProvider(config.settings)
        else:
            logger.error(f"Unknown provider type: {provider_type}")
            return None

    async def start(self):
        """Start the sync manager."""
        if self._running:
            return

        self._running = True

        # Connect to providers
        await self._connect_providers()

        # Start scheduler
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

        logger.info("Sync manager started")

    async def stop(self):
        """Stop the sync manager."""
        if not self._running:
            return

        self._running = False

        # Cancel scheduler
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        # Cancel active jobs
        for job_id, task in self.active_jobs.items():
            task.cancel()
        self.active_jobs.clear()

        # Disconnect providers
        await self._disconnect_providers()

        logger.info("Sync manager stopped")

    async def _connect_providers(self):
        """Connect to all configured providers."""
        for name, provider in self.providers.items():
            try:
                connected = await provider.connect()
                if not connected:
                    logger.warning(f"Failed to connect to provider: {name}")
            except Exception as e:
                logger.error(f"Error connecting to provider {name}: {e}")

    async def _disconnect_providers(self):
        """Disconnect from all providers."""
        for name, provider in self.providers.items():
            try:
                await provider.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting from provider {name}: {e}")

    async def _scheduler_loop(self):
        """Background scheduler loop."""
        while self._running:
            try:
                await self._process_scheduled_jobs()
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)

    async def _process_scheduled_jobs(self):
        """Process scheduled sync jobs."""
        now = datetime.now()

        for job in self.jobs.values():
            if (job.status == "scheduled" and
                job.scheduled_time and
                job.scheduled_time <= now):

                await self._execute_job(job.job_id)

    async def sync_now(self,
                      local_path: str,
                      provider_name: str,
                      remote_path: str = "",
                      direction: str = "bidirectional",
                      exclude_patterns: Optional[List[str]] = None,
                      conflict_resolution: ConflictResolution = ConflictResolution.NEWER_WINS) -> str:
        """
        Start an immediate sync operation.

        Args:
            local_path: Local directory path
            provider_name: Name of the sync provider
            remote_path: Remote path (empty for root)
            direction: Sync direction
            exclude_patterns: File patterns to exclude
            conflict_resolution: Conflict resolution strategy

        Returns:
            Job ID for tracking
        """
        job_id = f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{provider_name}"

        job = SyncJob(
            job_id=job_id,
            local_path=local_path,
            remote_path=remote_path,
            provider_name=provider_name,
            direction=direction,
            exclude_patterns=exclude_patterns or [],
            conflict_resolution=conflict_resolution,
            status="pending"
        )

        self.jobs[job_id] = job

        # Execute immediately
        task = asyncio.create_task(self._execute_job(job_id))
        self.active_jobs[job_id] = task

        return job_id

    async def schedule_sync(self,
                           local_path: str,
                           provider_name: str,
                           remote_path: str = "",
                           schedule_time: datetime = None,
                           interval_minutes: int = None,
                           direction: str = "bidirectional",
                           exclude_patterns: Optional[List[str]] = None,
                           conflict_resolution: ConflictResolution = ConflictResolution.NEWER_WINS) -> str:
        """
        Schedule a sync operation.

        Args:
            local_path: Local directory path
            provider_name: Name of the sync provider
            remote_path: Remote path
            schedule_time: Specific time to run (optional)
            interval_minutes: Repeat interval in minutes (optional)
            direction: Sync direction
            exclude_patterns: File patterns to exclude
            conflict_resolution: Conflict resolution strategy

        Returns:
            Job ID for tracking
        """
        job_id = f"scheduled_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{provider_name}"

        if schedule_time is None and interval_minutes:
            schedule_time = datetime.now() + timedelta(minutes=interval_minutes)

        job = SyncJob(
            job_id=job_id,
            local_path=local_path,
            remote_path=remote_path,
            provider_name=provider_name,
            direction=direction,
            exclude_patterns=exclude_patterns or [],
            conflict_resolution=conflict_resolution,
            scheduled_time=schedule_time,
            status="scheduled"
        )

        self.jobs[job_id] = job

        logger.info(f"Scheduled sync job: {job_id} at {schedule_time}")
        return job_id

    async def _execute_job(self, job_id: str):
        """
        Execute a sync job.

        Args:
            job_id: Job identifier
        """
        job = self.jobs.get(job_id)
        if not job:
            return

        try:
            job.status = "running"
            job.started_at = datetime.now()

            provider = self.providers.get(job.provider_name)
            if not provider:
                raise ValueError(f"Provider not found: {job.provider_name}")

            # Execute sync
            result = await provider.sync_directory(
                local_dir=job.local_path,
                remote_dir=job.remote_path,
                direction=job.direction,
                exclude_patterns=job.exclude_patterns
            )

            job.result = result
            job.completed_at = datetime.now()

            if result.success:
                job.status = "completed"
                logger.info(f"Sync job {job_id} completed successfully")
            else:
                job.status = "failed"
                logger.error(f"Sync job {job_id} failed: {result.errors}")

        except Exception as e:
            job.status = "failed"
            job.completed_at = datetime.now()
            logger.error(f"Sync job {job_id} error: {e}")

        finally:
            # Clean up active job
            self.active_jobs.pop(job_id, None)

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a sync job.

        Args:
            job_id: Job identifier

        Returns:
            Job status information or None if not found
        """
        job = self.jobs.get(job_id)
        if not job:
            return None

        return {
            'job_id': job.job_id,
            'status': job.status,
            'progress': self._calculate_progress(job),
            'result': job.result.__dict__ if job.result else None,
            'created_at': job.created_at.isoformat(),
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None
        }

    def _calculate_progress(self, job: SyncJob) -> float:
        """
        Calculate job progress percentage.

        Args:
            job: Sync job

        Returns:
            Progress percentage (0-100)
        """
        if job.status == "completed":
            return 100.0
        elif job.status == "running":
            # Estimate progress based on time (simple heuristic)
            if job.started_at:
                elapsed = (datetime.now() - job.started_at).total_seconds()
                # Assume average sync takes 30 seconds
                return min(90.0, elapsed / 30.0 * 100.0)
        return 0.0

    def list_jobs(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List sync jobs.

        Args:
            status_filter: Filter by status (optional)

        Returns:
            List of job information
        """
        jobs = []
        for job in self.jobs.values():
            if status_filter and job.status != status_filter:
                continue

            jobs.append(self.get_job_status(job.job_id))

        return jobs

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running sync job.

        Args:
            job_id: Job identifier

        Returns:
            True if cancelled successfully
        """
        task = self.active_jobs.get(job_id)
        if task and not task.done():
            task.cancel()
            job = self.jobs.get(job_id)
            if job:
                job.status = "cancelled"
            return True

        return False

    async def resolve_conflict(self,
                              conflict: SyncConflict,
                              resolution: ConflictResolution) -> bool:
        """
        Resolve a sync conflict.

        Args:
            conflict: Conflict to resolve
            resolution: Resolution strategy

        Returns:
            True if resolved successfully
        """
        try:
            # Implement conflict resolution logic
            if resolution == ConflictResolution.LOCAL_WINS:
                # Keep local version (already handled by sync)
                pass
            elif resolution == ConflictResolution.REMOTE_WINS:
                # Download remote version
                pass
            elif resolution == ConflictResolution.NEWER_WINS:
                # Already handled by sync logic
                pass
            elif resolution == ConflictResolution.MANUAL:
                # Wait for manual resolution
                return False
            elif resolution == ConflictResolution.MERGE:
                # Implement merge logic (complex, may not be supported)
                logger.warning("Merge resolution not implemented")
                return False

            # Remove from conflicts list
            self.conflicts = [c for c in self.conflicts if c != conflict]
            return True

        except Exception as e:
            logger.error(f"Failed to resolve conflict: {e}")
            return False

    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get information about all providers.

        Returns:
            Provider information
        """
        info = {}
        for name, provider in self.providers.items():
            info[name] = provider.get_provider_info()

        return info

    def add_provider(self, config: SyncConfig.ProviderConfig) -> bool:
        """
        Add a new sync provider.

        Args:
            config: Provider configuration

        Returns:
            True if added successfully
        """
        try:
            provider = self._create_provider(config)
            if provider:
                self.providers[config.name] = provider
                # Save to config
                self.sync_config.providers.append(config)
                self.config_manager.save_sync_config(self.sync_config)
                logger.info(f"Added sync provider: {config.name}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to add provider {config.name}: {e}")
            return False

    def remove_provider(self, name: str) -> bool:
        """
        Remove a sync provider.

        Args:
            name: Provider name

        Returns:
            True if removed successfully
        """
        try:
            if name in self.providers:
                provider = self.providers[name]
                asyncio.create_task(provider.disconnect())
                del self.providers[name]

                # Remove from config
                self.sync_config.providers = [
                    p for p in self.sync_config.providers if p.name != name
                ]
                self.config_manager.save_sync_config(self.sync_config)

                logger.info(f"Removed sync provider: {name}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to remove provider {name}: {e}")
            return False

    async def test_provider(self, name: str) -> Dict[str, Any]:
        """
        Test a sync provider connection.

        Args:
            name: Provider name

        Returns:
            Test results
        """
        provider = self.providers.get(name)
        if not provider:
            return {'success': False, 'error': 'Provider not found'}

        try:
            connected = await provider.connect()
            if connected:
                # Try a simple operation
                test_result = await provider.list_files()
                await provider.disconnect()

                return {
                    'success': True,
                    'files_count': len(test_result)
                }
            else:
                return {'success': False, 'error': 'Connection failed'}

        except Exception as e:
            return {'success': False, 'error': str(e)}