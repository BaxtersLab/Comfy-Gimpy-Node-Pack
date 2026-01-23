# GIMP-ComfyUI Bridge

This project provides a bridge between GIMP (GNU Image Manipulation Program) and ComfyUI (Stable Diffusion workflow engine) for AI-powered image editing workflows.

## Modules

- `gimp_plugin/`: GIMP plugin components
  - `api_client.py`: Handles HTTP communication with ComfyUI backend
  - `plugin.py`: Main plugin logic for workflow execution and undo/redo
  - `utils.py`: Utility functions for image/mask export and layer insertion
  - `ui_panel.py`: UI stubs for status updates and error display
- `comfy_extension/`: ComfyUI extension components
  - `server_endpoints.py`: Flask server endpoints for ping, run_workflow, and get_workflows
  - `io_handlers.py`: Handles saving/loading of uploaded images and masks
  - `workflow_loader.py`: Loads workflow templates and lists available workflows
- `shared/`: Shared utilities and types
  - `config.py`: Configuration management with validation
  - `protocol.py`: Protocol definitions and validation for requests/responses
  - `types.py`: Type definitions for metadata and parameters
  - `history.py`: History management for undo/redo operations
- `examples/`: Example workflows
- `temp/`: Temporary files and session data

## Setup

1. **Install ComfyUI Extension**:
   - Copy the `comfy_extension/` directory to your ComfyUI custom nodes folder
   - Run the server: `python server_endpoints.py`

2. **Install GIMP Plugin**:
   - Copy the `gimp_plugin/` directory to your GIMP plugins folder
   - Ensure Python support is enabled in GIMP

3. **Configure Connection**:
   - Set environment variables:
     - `COMFY_HOST`: Host address (default: localhost)
     - `COMFY_PORT`: Port number (default: 8188)
     - `COMFY_WORKFLOWS_DIR`: Path to workflow templates
     - `COMFY_TEMP_DIR`: Path for temporary files
     - `COMFY_LOG_LEVEL`: Logging level (default: INFO)

## Running the ComfyUI Extension

1. Navigate to the `comfy_extension/` directory
2. Run `python server_endpoints.py`
3. The server will start on localhost:8188

## Enabling Logging

Logging is controlled by the `COMFY_LOG_LEVEL` environment variable. Set it to DEBUG for detailed logs.

## History System

The history system maintains file-based snapshots of each AI operation:
- Input images and masks
- Parameters (JSON)
- Output images
- Metadata (timestamps, workflow info)

Sessions are stored in `temp/sessions/<session_id>/step_XXXX/`

## Workflow Templates

Workflow templates are JSON files in `examples/workflows/`. Each template defines a ComfyUI workflow for different modes (inpaint, upscale, etc.).

## Supported Workflows

- **Inpaint**: Requires image + mask
- **Outpaint**: Image + auto-generated mask
- **Upscale**: Image only
- **Txt2Img**: Prompt only
- **Img2Img**: Image + strength
- **ControlNet**: Image + control type