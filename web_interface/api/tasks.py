"""
Web API endpoints for task management.
"""

import logging
from typing import Dict, Any, Optional
from flask import Blueprint, request, jsonify

from gimp_comfy_bridge.async_engine import (
    submit_task,
    get_task_status,
    cancel_task,
    list_tasks,
    get_queue_stats
)
from gimp_comfy_bridge.async_engine.task import TaskPriority, TaskState

logger = logging.getLogger(__name__)

# Create blueprint
tasks_bp = Blueprint('tasks', __name__, url_prefix='/api/tasks')


@tasks_bp.route('/', methods=['GET'])
def get_tasks():
    """
    Get list of tasks.

    Query parameters:
        state: Filter by task state (optional)
        limit: Maximum number of tasks to return (optional)
        offset: Number of tasks to skip (optional)
    """
    try:
        state = request.args.get('state')
        if state:
            try:
                state = TaskState(state)
            except ValueError:
                return jsonify({"error": f"Invalid state: {state}"}), 400

        limit = request.args.get('limit')
        if limit:
            try:
                limit = int(limit)
            except ValueError:
                return jsonify({"error": f"Invalid limit: {limit}"}), 400

        offset = request.args.get('offset', 0)
        try:
            offset = int(offset)
        except ValueError:
            return jsonify({"error": f"Invalid offset: {offset}"}), 400

        result = list_tasks(state=state, limit=limit, offset=offset)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        return jsonify({"error": str(e)}), 500


@tasks_bp.route('/', methods=['POST'])
def create_task():
    """
    Submit a new task.

    Request body:
        operation: Operation type (required)
        parameters: Operation parameters (optional)
        priority: Task priority (optional, default: "normal")
        timeout_seconds: Task timeout (optional)
        callback_url: Webhook URL for completion (optional)
        metadata: Additional metadata (optional)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400

        operation = data.get('operation')
        if not operation:
            return jsonify({"error": "operation field is required"}), 400

        # Parse priority
        priority_str = data.get('priority', 'normal')
        try:
            priority = TaskPriority(priority_str.lower())
        except ValueError:
            return jsonify({"error": f"Invalid priority: {priority_str}"}), 400

        # Submit task
        task_id = submit_task(
            operation=operation,
            parameters=data.get('parameters', {}),
            priority=priority,
            timeout_seconds=data.get('timeout_seconds'),
            callback_url=data.get('callback_url'),
            metadata=data.get('metadata', {})
        )

        logger.info(f"Task submitted via API: {task_id}")
        return jsonify({"task_id": task_id}), 201

    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return jsonify({"error": str(e)}), 500


@tasks_bp.route('/<task_id>', methods=['GET'])
def get_task(task_id: str):
    """
    Get status of a specific task.
    """
    try:
        task_status = get_task_status(task_id)
        if task_status is None:
            return jsonify({"error": f"Task {task_id} not found"}), 404

        return jsonify(task_status)

    except Exception as e:
        logger.error(f"Error getting task {task_id}: {e}")
        return jsonify({"error": str(e)}), 500


@tasks_bp.route('/<task_id>/cancel', methods=['POST'])
def cancel_task_endpoint(task_id: str):
    """
    Cancel a specific task.
    """
    try:
        cancelled = cancel_task(task_id)
        if not cancelled:
            return jsonify({"error": f"Task {task_id} could not be cancelled"}), 400

        logger.info(f"Task cancelled via API: {task_id}")
        return jsonify({"message": f"Task {task_id} cancelled successfully"})

    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}")
        return jsonify({"error": str(e)}), 500


@tasks_bp.route('/stats', methods=['GET'])
def get_stats():
    """
    Get queue statistics.
    """
    try:
        stats = get_queue_stats()
        return jsonify(stats)

    except Exception as e:
        logger.error(f"Error getting queue stats: {e}")
        return jsonify({"error": str(e)}), 500


@tasks_bp.route('/batch', methods=['POST'])
def create_batch_tasks():
    """
    Submit multiple tasks in a batch.

    Request body:
        tasks: List of task objects (same format as single task)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400

        tasks = data.get('tasks', [])
        if not tasks:
            return jsonify({"error": "tasks list is required"}), 400

        task_ids = []
        for task_data in tasks:
            operation = task_data.get('operation')
            if not operation:
                return jsonify({"error": "operation field is required for all tasks"}), 400

            # Parse priority
            priority_str = task_data.get('priority', 'normal')
            try:
                priority = TaskPriority(priority_str.lower())
            except ValueError:
                return jsonify({"error": f"Invalid priority: {priority_str}"}), 400

            # Submit task
            task_id = submit_task(
                operation=operation,
                parameters=task_data.get('parameters', {}),
                priority=priority,
                timeout_seconds=task_data.get('timeout_seconds'),
                callback_url=task_data.get('callback_url'),
                metadata=task_data.get('metadata', {})
            )
            task_ids.append(task_id)

        logger.info(f"Batch tasks submitted via API: {len(task_ids)} tasks")
        return jsonify({"task_ids": task_ids}), 201

    except Exception as e:
        logger.error(f"Error creating batch tasks: {e}")
        return jsonify({"error": str(e)}), 500