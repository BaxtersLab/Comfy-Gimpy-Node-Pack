"""
Server endpoints for ComfyUI extension.
"""

import logging
from flask import Flask, request, jsonify
import uuid
from io_handlers import save_uploaded_image, save_uploaded_mask, load_result_image
from workflow_loader import load_workflow_template, list_available_workflows

logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/gimp_bridge/ping', methods=['POST'])
def ping():
    """
    Ping endpoint.

    Returns:
        JSON: Ping response.
    """
    try:
        logger.info("Ping received")
        return jsonify({
            "status": "ok",
            "comfyui_version": "1.0.0",  # Placeholder
            "models_available": ["model1", "model2"]
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
        params = request.form.get('params')
        
        image_file = request.files.get('image')
        mask_file = request.files.get('mask')
        
        # Save uploaded files
        image_path = None
        if image_file:
            image_path = save_uploaded_image(image_file.read(), app.config.get('TEMP_DIR', '/tmp'))
        
        mask_path = None
        if mask_file:
            mask_path = save_uploaded_mask(mask_file.read(), app.config.get('TEMP_DIR', '/tmp'))
        
        # Load workflow template (placeholder)
        workflow = load_workflow_template(workflow_name)
        
        # Placeholder: return a blank PNG
        import io
        blank_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        result_image = load_result_image(blank_png)  # Placeholder
        
        logger.info(f"Workflow {workflow_name} executed")
        return jsonify({
            "status": "completed",
            "task_id": str(uuid.uuid4()),
            "result": {
                "image_base64": result_image.decode('latin-1'),  # Placeholder
                "mime_type": "image/png"
            }
        })
    except Exception as e:
        logger.error(f"Run workflow failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/gimp_bridge/workflows', methods=['GET'])
def get_workflows():
    """
    Get workflows endpoint.

    Returns:
        JSON: Workflows response.
    """
    try:
        workflows = list_available_workflows()
        logger.info(f"Returned {len(workflows)} workflows")
        return jsonify({"workflows": workflows})
    except Exception as e:
        logger.error(f"Get workflows failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='localhost', port=8188)