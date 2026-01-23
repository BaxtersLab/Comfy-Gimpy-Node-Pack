"""
Web API endpoints for remote node management.
"""

import logging
from typing import Dict, Any, List, Optional
from flask import Blueprint, request, jsonify

from ...async_engine.api import (
    get_remote_nodes,
    get_remote_node_status,
    refresh_remote_nodes,
    is_remote_available,
    submit_remote_task
)

logger = logging.getLogger(__name__)

# Create blueprint
nodes_bp = Blueprint('nodes', __name__, url_prefix='/api/nodes')


@nodes_bp.route('/', methods=['GET'])
def list_nodes():
    """
    Get list of available remote nodes.

    Returns:
        JSON response with node information
    """
    try:
        if not is_remote_available():
            return jsonify({
                'success': False,
                'error': 'Remote execution not available',
                'nodes': []
            }), 503

        nodes = get_remote_nodes()
        return jsonify({
            'success': True,
            'nodes': nodes,
            'count': len(nodes)
        })

    except Exception as e:
        logger.error(f"Error listing remote nodes: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'nodes': []
        }), 500


@nodes_bp.route('/<node_id>', methods=['GET'])
def get_node(node_id: str):
    """
    Get detailed information about a specific remote node.

    Args:
        node_id: Remote node identifier

    Returns:
        JSON response with node details
    """
    try:
        if not is_remote_available():
            return jsonify({
                'success': False,
                'error': 'Remote execution not available'
            }), 503

        node_info = get_remote_node_status(node_id)
        if node_info is None:
            return jsonify({
                'success': False,
                'error': f'Node not found: {node_id}'
            }), 404

        return jsonify({
            'success': True,
            'node': node_info
        })

    except Exception as e:
        logger.error(f"Error getting node {node_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@nodes_bp.route('/refresh', methods=['POST'])
def refresh_nodes():
    """
    Refresh the status of all remote nodes.

    Returns:
        JSON response with refresh status
    """
    try:
        if not is_remote_available():
            return jsonify({
                'success': False,
                'error': 'Remote execution not available'
            }), 503

        refresh_remote_nodes()
        nodes = get_remote_nodes()

        return jsonify({
            'success': True,
            'message': 'Remote nodes refreshed',
            'nodes': nodes,
            'count': len(nodes)
        })

    except Exception as e:
        logger.error(f"Error refreshing remote nodes: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@nodes_bp.route('/<node_id>/execute', methods=['POST'])
def execute_on_node(node_id: str):
    """
    Execute a task on a specific remote node.

    Args:
        node_id: Remote node identifier

    Request JSON:
        {
            "operation": "string",
            "parameters": {},
            "priority": "normal",
            "timeout_seconds": 300,
            "callback_url": "string",
            "metadata": {}
        }

    Returns:
        JSON response with task information
    """
    try:
        if not is_remote_available():
            return jsonify({
                'success': False,
                'error': 'Remote execution not available'
            }), 503

        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Missing JSON request body'
            }), 400

        # Validate required fields
        operation = data.get('operation')
        if not operation:
            return jsonify({
                'success': False,
                'error': 'Missing required field: operation'
            }), 400

        parameters = data.get('parameters', {})
        priority = data.get('priority', 'normal')
        timeout_seconds = data.get('timeout_seconds')
        callback_url = data.get('callback_url')
        metadata = data.get('metadata', {})

        # Submit remote task
        task_id = submit_remote_task(
            operation=operation,
            parameters=parameters,
            node_id=node_id,
            priority=priority,
            timeout_seconds=timeout_seconds,
            callback_url=callback_url,
            metadata=metadata
        )

        return jsonify({
            'success': True,
            'task_id': task_id,
            'node_id': node_id,
            'message': f'Task submitted to remote node {node_id}'
        })

    except Exception as e:
        logger.error(f"Error executing task on node {node_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@nodes_bp.route('/capabilities', methods=['GET'])
def get_node_capabilities():
    """
    Get capabilities of all remote nodes.

    Returns:
        JSON response with node capabilities
    """
    try:
        if not is_remote_available():
            return jsonify({
                'success': False,
                'error': 'Remote execution not available',
                'capabilities': {}
            }), 503

        nodes = get_remote_nodes()
        capabilities = {}

        for node in nodes:
            node_id = node['id']
            node_status = get_remote_node_status(node_id)
            if node_status and node_status.get('capabilities'):
                capabilities[node_id] = node_status['capabilities']

        return jsonify({
            'success': True,
            'capabilities': capabilities,
            'node_count': len(capabilities)
        })

    except Exception as e:
        logger.error(f"Error getting node capabilities: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'capabilities': {}
        }), 500


@nodes_bp.route('/health', methods=['GET'])
def get_nodes_health():
    """
    Get health status of all remote nodes.

    Returns:
        JSON response with node health information
    """
    try:
        if not is_remote_available():
            return jsonify({
                'success': False,
                'error': 'Remote execution not available',
                'health': {}
            }), 503

        nodes = get_remote_nodes()
        health = {}

        for node in nodes:
            node_id = node['id']
            node_status = get_remote_node_status(node_id)
            if node_status:
                health[node_id] = {
                    'status': node_status.get('status'),
                    'response_time': node_status.get('response_time'),
                    'error_count': node_status.get('error_count'),
                    'uptime': node_status.get('uptime'),
                    'last_seen': node_status.get('last_seen')
                }

        return jsonify({
            'success': True,
            'health': health,
            'node_count': len(health)
        })

    except Exception as e:
        logger.error(f"Error getting nodes health: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'health': {}
        }), 500