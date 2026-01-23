"""
Server endpoints for ComfyUI extension.
"""

import json
import logging
import asyncio
import threading
from flask import Flask, request, jsonify
import uuid
from io_handlers import save_uploaded_image, save_uploaded_mask, load_result_image
from workflow_loader import load_workflow_template, list_available_workflows
from workflow_engine import WorkflowExecutionEngine, WorkflowStatus
from shared.protocol import WorkflowRequest, WorkflowResponse

logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global workflow engine instance
workflow_engine = WorkflowExecutionEngine()
engine_thread = None

def start_workflow_engine():
    """Start the workflow engine in a background thread."""
    global engine_thread
    if engine_thread is None or not engine_thread.is_alive():
        workflow_engine.start()
        engine_thread = threading.Thread(target=lambda: asyncio.run(workflow_engine.process_queue()))
        engine_thread.daemon = True
        engine_thread.start()
        logger.info("Workflow engine started in background thread")

# Start engine when module is imported
start_workflow_engine()

@app.route('/gimp_bridge/ping', methods=['POST'])
def ping():
    """
    Ping endpoint.

    Returns:
        JSON: Ping response.
    """
    try:
        logger.info("Ping received")

        # Get queue status
        active_count = len([e for e in workflow_engine.active_executions.values()
                           if e.status == WorkflowStatus.RUNNING])
        queue_size = len(workflow_engine.execution_queue)

        return jsonify({
            "status": "ok",
            "comfyui_version": "1.0.0",
            "models_available": ["model1", "model2"],  # Placeholder
            "active_executions": active_count,
            "queue_size": queue_size,
            "engine_running": workflow_engine._running
        })
    except Exception as e:
        logger.error(f"Ping failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/gimp_bridge/run_workflow', methods=['POST'])
def run_workflow():
    """
    Run workflow endpoint.

    Returns:
        JSON: Workflow response.
    """
    try:
        mode = request.form.get('mode')
        workflow_name = request.form.get('workflow_name')
        params_str = request.form.get('params', '{}')

        # Parse parameters
        try:
            params = json.loads(params_str) if params_str else {}
        except json.JSONDecodeError:
            params = {}

        # Handle file uploads
        image_data = None
        mask_data = None

        image_file = request.files.get('image')
        if image_file:
            image_data = image_file.read()

        mask_file = request.files.get('mask')
        if mask_file:
            mask_data = mask_file.read()

        # Create workflow request
        workflow_request = WorkflowRequest(
            mode=mode,
            workflow_name=workflow_name,
            params=params,
            image=image_data,
            mask=mask_data
        )

        # Submit to workflow engine
        task_id = workflow_engine.submit_workflow(workflow_request)

        logger.info(f"Workflow {workflow_name} submitted with task ID: {task_id}")
        return jsonify({
            "status": "submitted",
            "task_id": task_id,
            "message": "Workflow submitted for execution"
        })

    except Exception as e:
        logger.error(f"Run workflow failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/gimp_bridge/workflow_status/<task_id>', methods=['GET'])
def get_workflow_status(task_id):
    """
    Get workflow execution status.

    Args:
        task_id: Task ID to check

    Returns:
        JSON: Status response
    """
    try:
        execution = workflow_engine.get_execution_status(task_id)
        if not execution:
            return jsonify({"status": "not_found", "message": "Task not found"}), 404

        response = {
            "task_id": execution.task_id,
            "status": execution.status.value,
            "progress": execution.progress,
            "current_node": execution.current_node,
            "start_time": execution.start_time,
            "end_time": execution.end_time
        }

        if execution.status == WorkflowStatus.COMPLETED and execution.result:
            response["result"] = execution.result
        elif execution.status == WorkflowStatus.FAILED:
            response["error"] = execution.error_message

        return jsonify(response)

    except Exception as e:
        logger.error(f"Get workflow status failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/gimp_bridge/queue_status', methods=['GET'])
def get_queue_status():
    """
    Get workflow queue status.

    Returns:
        JSON: Queue status response
    """
    try:
        active_executions = []
        for execution in workflow_engine.active_executions.values():
            active_executions.append({
                "task_id": execution.task_id,
                "workflow_name": execution.request.workflow_name,
                "status": execution.status.value,
                "progress": execution.progress,
                "current_node": execution.current_node,
                "start_time": execution.start_time
            })

        queued_workflows = []
        for execution in workflow_engine.execution_queue:
            queued_workflows.append({
                "task_id": execution.task_id,
                "workflow_name": execution.request.workflow_name,
                "mode": execution.request.mode
            })

        return jsonify({
            "active_executions": active_executions,
            "queued_workflows": queued_workflows,
            "total_active": len(active_executions),
            "total_queued": len(queued_workflows)
        })

    except Exception as e:
        logger.error(f"Get queue status failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='localhost', port=8188)