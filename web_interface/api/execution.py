"""
Execution API endpoints for ComfyUI workflow execution.
Phase 9 - Real ComfyUI Integration
"""

import logging
from typing import Dict, Any, Optional, List
import json

from gimp_plugin.plugin import (
    execute_comfyui_workflow,
    execute_fusion_variants,
    get_execution_status,
    cancel_execution_job,
    get_execution_system_status,
    get_execution_performance_report,
    process_execution_output
)

logger = logging.getLogger(__name__)


# Handler functions for aiohttp server
async def execute_workflow_handler(request):
    """Handle workflow execution request."""
    try:
        data = await request.json()
        if 'workflow_data' not in data:
            return json_response({
                'success': False,
                'error': 'Missing workflow_data in request body'
            }, status=400)

        workflow_data = data['workflow_data']
        options = data.get('options', {})

        result = execute_comfyui_workflow(workflow_data, options)

        if result['success']:
            return json_response(result)
        else:
            return json_response(result, status=500)

    except Exception as e:
        logger.error(f"Execute workflow API error: {e}")
        return json_response({
            'success': False,
            'error': str(e)
        }, status=500)


async def execute_fusion_handler(request):
    """Handle fusion execution request."""
    try:
        data = await request.json()
        if 'fusion_result' not in data:
            return json_response({
                'success': False,
                'error': 'Missing fusion_result in request body'
            }, status=400)

        fusion_result = data['fusion_result']
        template_id = data.get('template_id')
        style_id = data.get('style_id')
        options = data.get('options', {})

        if not template_id:
            return json_response({
                'success': False,
                'error': 'Missing template_id'
            }, status=400)

        result = execute_fusion_variants(fusion_result, template_id, style_id, options)

        if result['success']:
            return json_response(result)
        else:
            return json_response(result, status=500)

    except Exception as e:
        logger.error(f"Execute fusion API error: {e}")
        return json_response({
            'success': False,
            'error': str(e)
        }, status=500)


async def get_job_status_handler(request):
    """Handle get job status request."""
    try:
        job_id = request.match_info.get('job_id')
        result = get_execution_status(job_id)

        if result['success']:
            return json_response(result)
        else:
            return json_response(result, status=404)

    except Exception as e:
        logger.error(f"Get job status API error: {e}")
        return json_response({
            'success': False,
            'error': str(e)
        }, status=500)


async def cancel_job_handler(request):
    """Handle cancel job request."""
    try:
        job_id = request.match_info.get('job_id')
        result = cancel_execution_job(job_id)

        if result['success']:
            return json_response(result)
        else:
            return json_response(result, status=400)

    except Exception as e:
        logger.error(f"Cancel job API error: {e}")
        return json_response({
            'success': False,
            'error': str(e)
        }, status=500)


async def get_system_status_handler(request):
    """Handle get system status request."""
    try:
        result = get_execution_system_status()

        if result['success']:
            return json_response(result)
        else:
            return json_response(result, status=500)

    except Exception as e:
        logger.error(f"Get system status API error: {e}")
        return json_response({
            'success': False,
            'error': str(e)
        }, status=500)


async def get_performance_handler(request):
    """Handle get performance request."""
    try:
        result = get_execution_performance_report()

        if result['success']:
            return json_response(result)
        else:
            return json_response(result, status=500)

    except Exception as e:
        logger.error(f"Get performance API error: {e}")
        return json_response({
            'success': False,
            'error': str(e)
        }, status=500)


async def process_output_handler(request):
    """Handle process output request."""
    try:
        job_id = request.match_info.get('job_id')
        data = await request.json()
        options = data.get('options', {}) if data else {}

        result = process_execution_output(job_id, options)

        if result['success']:
            return json_response(result)
        else:
            return json_response(result, status=400)

    except Exception as e:
        logger.error(f"Process output API error: {e}")
        return json_response({
            'success': False,
            'error': str(e)
        }, status=500)


async def list_jobs_handler(request):
    """Handle list jobs request."""
    try:
        from gimp_plugin.plugin import _execution_engine

        if not _execution_engine:
            return json_response({
                'success': True,
                'jobs': []
            })

        # Get query parameters
        status_filter = request.query.get('status')
        limit = int(request.query.get('limit', 50))

        # Filter jobs
        jobs = []
        for job in list(_execution_engine.active_jobs.values())[:limit]:
            job_info = {
                'job_id': job.job_id,
                'status': job.status.value,
                'progress': job.progress,
                'start_time': job.start_time,
                'end_time': job.end_time,
                'workflow_template': getattr(job.workflow_data, 'template_id', None),
                'workflow_style': getattr(job.workflow_data, 'style_id', None),
                'fusion_result': job.fusion_result.id if job.fusion_result else None
            }

            if not status_filter or job.status.value == status_filter:
                jobs.append(job_info)

        return json_response({
            'success': True,
            'jobs': jobs,
            'total_count': len(jobs)
        })

    except Exception as e:
        logger.error(f"List jobs API error: {e}")
        return json_response({
            'success': False,
            'error': str(e)
        }, status=500)


async def batch_status_handler(request):
    """Handle batch status request."""
    try:
        data = await request.json()
        if 'job_ids' not in data:
            return json_response({
                'success': False,
                'error': 'Missing job_ids in request body'
            }, status=400)

        job_ids = data['job_ids']
        results = {}

        for job_id in job_ids:
            result = get_execution_status(job_id)
            results[job_id] = result

        return json_response({
            'success': True,
            'results': results
        })

    except Exception as e:
        logger.error(f"Batch status API error: {e}")
        return json_response({
            'success': False,
            'error': str(e)
        }, status=500)


def json_response(data: Dict[str, Any], status: int = 200):
    """Create a JSON response."""
    try:
        from aiohttp import web
        return web.json_response(data, status=status)
    except ImportError:
        # Fallback for when aiohttp is not available
        import json
        from flask import jsonify
        response = jsonify(data)
        response.status_code = status
        return response