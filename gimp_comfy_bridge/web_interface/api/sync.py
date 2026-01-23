"""
Web API endpoints for cloud sync management.
"""

import logging
from typing import Dict, Any, List, Optional
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

# Import sync components (will be available after sync module is integrated)
try:
    from ...sync import SyncManager
    _sync_manager: Optional[SyncManager] = None
    _SYNC_AVAILABLE = True
except ImportError:
    _sync_manager = None
    _SYNC_AVAILABLE = False
    logger.warning("Sync components not available")

# Create blueprint
sync_bp = Blueprint('sync', __name__, url_prefix='/api/sync')


def initialize_sync_manager(config_manager):
    """
    Initialize the sync manager for the API.

    Args:
        config_manager: Configuration manager instance
    """
    global _sync_manager
    if _SYNC_AVAILABLE and config_manager:
        try:
            _sync_manager = SyncManager(config_manager)
            _sync_manager.start()
            logger.info("Sync manager initialized for web API")
        except Exception as e:
            logger.error(f"Failed to initialize sync manager: {e}")
            _sync_manager = None


@sync_bp.route('/status', methods=['GET'])
def get_sync_status():
    """
    Get overall sync status.

    Returns:
        JSON response with sync status
    """
    try:
        if not _sync_manager:
            return jsonify({
                'success': False,
                'error': 'Sync manager not available',
                'status': 'unavailable'
            }), 503

        provider_info = _sync_manager.get_provider_info()
        jobs = _sync_manager.list_jobs()

        return jsonify({
            'success': True,
            'status': 'available',
            'providers': provider_info,
            'active_jobs': len([j for j in jobs if j.get('status') == 'running']),
            'total_jobs': len(jobs)
        })

    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'status': 'error'
        }), 500


@sync_bp.route('/providers', methods=['GET'])
def list_providers():
    """
    Get list of configured sync providers.

    Returns:
        JSON response with provider information
    """
    try:
        if not _sync_manager:
            return jsonify({
                'success': False,
                'error': 'Sync manager not available',
                'providers': []
            }), 503

        provider_info = _sync_manager.get_provider_info()
        return jsonify({
            'success': True,
            'providers': provider_info,
            'count': len(provider_info)
        })

    except Exception as e:
        logger.error(f"Error listing sync providers: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'providers': []
        }), 500


@sync_bp.route('/providers/<provider_name>/test', methods=['POST'])
def test_provider(provider_name: str):
    """
    Test a sync provider connection.

    Args:
        provider_name: Name of the provider to test

    Returns:
        JSON response with test results
    """
    try:
        if not _sync_manager:
            return jsonify({
                'success': False,
                'error': 'Sync manager not available'
            }), 503

        test_result = _sync_manager.test_provider(provider_name)
        return jsonify(test_result)

    except Exception as e:
        logger.error(f"Error testing provider {provider_name}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sync_bp.route('/jobs', methods=['GET'])
def list_jobs():
    """
    Get list of sync jobs.

    Query parameters:
        status: Filter by job status
        limit: Maximum number of jobs to return
        offset: Number of jobs to skip

    Returns:
        JSON response with job list
    """
    try:
        if not _sync_manager:
            return jsonify({
                'success': False,
                'error': 'Sync manager not available',
                'jobs': []
            }), 503

        status_filter = request.args.get('status')
        limit = request.args.get('limit')
        if limit:
            try:
                limit = int(limit)
            except ValueError:
                limit = None
        offset = request.args.get('offset', 0)
        try:
            offset = int(offset)
        except ValueError:
            offset = 0

        jobs = _sync_manager.list_jobs(status_filter=status_filter)

        # Apply pagination
        total_count = len(jobs)
        if limit:
            jobs = jobs[offset:offset + limit]
        else:
            jobs = jobs[offset:]

        return jsonify({
            'success': True,
            'jobs': jobs,
            'total_count': total_count,
            'returned_count': len(jobs),
            'offset': offset,
            'limit': limit
        })

    except Exception as e:
        logger.error(f"Error listing sync jobs: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'jobs': []
        }), 500


@sync_bp.route('/jobs/<job_id>', methods=['GET'])
def get_job(job_id: str):
    """
    Get detailed information about a sync job.

    Args:
        job_id: Job identifier

    Returns:
        JSON response with job details
    """
    try:
        if not _sync_manager:
            return jsonify({
                'success': False,
                'error': 'Sync manager not available'
            }), 503

        job_info = _sync_manager.get_job_status(job_id)
        if job_info is None:
            return jsonify({
                'success': False,
                'error': f'Job not found: {job_id}'
            }), 404

        return jsonify({
            'success': True,
            'job': job_info
        })

    except Exception as e:
        logger.error(f"Error getting job {job_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sync_bp.route('/sync', methods=['POST'])
def start_sync():
    """
    Start a new sync operation.

    Request JSON:
        {
            "local_path": "string",
            "provider_name": "string",
            "remote_path": "string",
            "direction": "bidirectional",
            "exclude_patterns": ["string"],
            "conflict_resolution": "newer_wins"
        }

    Returns:
        JSON response with job information
    """
    try:
        if not _sync_manager:
            return jsonify({
                'success': False,
                'error': 'Sync manager not available'
            }), 503

        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Missing JSON request body'
            }), 400

        # Validate required fields
        local_path = data.get('local_path')
        provider_name = data.get('provider_name')

        if not local_path or not provider_name:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: local_path and provider_name'
            }), 400

        # Optional fields
        remote_path = data.get('remote_path', '')
        direction = data.get('direction', 'bidirectional')
        exclude_patterns = data.get('exclude_patterns', [])
        conflict_resolution = data.get('conflict_resolution', 'newer_wins')

        # Start sync
        job_id = _sync_manager.sync_now(
            local_path=local_path,
            provider_name=provider_name,
            remote_path=remote_path,
            direction=direction,
            exclude_patterns=exclude_patterns,
            conflict_resolution=conflict_resolution
        )

        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Sync job started'
        })

    except Exception as e:
        logger.error(f"Error starting sync: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sync_bp.route('/jobs/<job_id>/cancel', methods=['POST'])
def cancel_job(job_id: str):
    """
    Cancel a running sync job.

    Args:
        job_id: Job identifier

    Returns:
        JSON response with cancellation status
    """
    try:
        if not _sync_manager:
            return jsonify({
                'success': False,
                'error': 'Sync manager not available'
            }), 503

        cancelled = _sync_manager.cancel_job(job_id)
        if cancelled:
            return jsonify({
                'success': True,
                'message': f'Job {job_id} cancelled'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Could not cancel job {job_id}'
            }), 400

    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sync_bp.route('/schedule', methods=['POST'])
def schedule_sync():
    """
    Schedule a recurring sync operation.

    Request JSON:
        {
            "local_path": "string",
            "provider_name": "string",
            "remote_path": "string",
            "schedule_time": "ISO datetime string",
            "interval_minutes": 60,
            "direction": "bidirectional",
            "exclude_patterns": ["string"],
            "conflict_resolution": "newer_wins"
        }

    Returns:
        JSON response with job information
    """
    try:
        if not _sync_manager:
            return jsonify({
                'success': False,
                'error': 'Sync manager not available'
            }), 503

        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Missing JSON request body'
            }), 400

        # Validate required fields
        local_path = data.get('local_path')
        provider_name = data.get('provider_name')

        if not local_path or not provider_name:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: local_path and provider_name'
            }), 400

        # Optional fields
        remote_path = data.get('remote_path', '')
        schedule_time_str = data.get('schedule_time')
        interval_minutes = data.get('interval_minutes')
        direction = data.get('direction', 'bidirectional')
        exclude_patterns = data.get('exclude_patterns', [])
        conflict_resolution = data.get('conflict_resolution', 'newer_wins')

        # Parse schedule time
        schedule_time = None
        if schedule_time_str:
            from datetime import datetime
            try:
                schedule_time = datetime.fromisoformat(schedule_time_str.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': f'Invalid schedule_time format: {schedule_time_str}'
                }), 400

        # Schedule sync
        job_id = _sync_manager.schedule_sync(
            local_path=local_path,
            provider_name=provider_name,
            remote_path=remote_path,
            schedule_time=schedule_time,
            interval_minutes=interval_minutes,
            direction=direction,
            exclude_patterns=exclude_patterns,
            conflict_resolution=conflict_resolution
        )

        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Sync job scheduled'
        })

    except Exception as e:
        logger.error(f"Error scheduling sync: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500