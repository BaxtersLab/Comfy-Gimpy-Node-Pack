"""
UI panel for the GIMP plugin.
"""

import logging
from typing import List, Dict, Any, Optional

# Try to import GIMP modules
try:
    import gimp
    from gimpfu import *
    from gimpenums import *
    GIMP_AVAILABLE = True
except ImportError:
    GIMP_AVAILABLE = False

logger = logging.getLogger(__name__)

class ComfyUIPanel:
    """Main UI panel for ComfyUI Bridge."""

    def __init__(self):
        self.workflows = []
        self.current_task_id = None
        self.status_callback = None

    def update_workflows(self, workflows: List[Dict[str, Any]]):
        """Update available workflows."""
        self.workflows = workflows
        logger.info(f"Updated workflows: {len(workflows)} available")

    def show_main_dialog(self):
        """Show the main ComfyUI Bridge dialog."""
        if not GIMP_AVAILABLE:
            logger.warning("GIMP not available, cannot show dialog")
            return

        # Create dialog fields
        fields = [
            (PF_OPTION, "workflow_type", "Workflow Type", 0, self._get_workflow_options()),
            (PF_STRING, "prompt", "Prompt", "beautiful landscape"),
            (PF_STRING, "negative_prompt", "Negative Prompt", "blurry, low quality"),
            (PF_INT, "width", "Width", 1024),
            (PF_INT, "height", "Height", 1024),
            (PF_FLOAT, "strength", "Strength/Denoise", 0.6),
            (PF_FLOAT, "upscale_factor", "Upscale Factor", 2.0),
            (PF_OPTION, "control_type", "Control Type", 0, ["canny", "depth", "pose", "normal"]),
            (PF_BOOL, "use_selection", "Use Selection as Mask", True),
            (PF_BOOL, "show_advanced", "Show Advanced Options", False)
        ]

        # Show dialog
        result = gimpfu.pdb.gimp_procedural_db_proc_call(
            "gimp_procedural_db_temp_procedural_db_set_data",
            "comfyui_bridge_dialog",
            fields
        )

        if result:
            self._process_dialog_result(result)

    def _get_workflow_options(self) -> List[str]:
        """Get workflow options for dialog."""
        options = ["Text to Image", "Image to Image", "Inpainting", "Outpainting", "Upscaling", "ControlNet"]
        if self.workflows:
            # Add custom workflows
            for workflow in self.workflows:
                options.append(f"Custom: {workflow['name']}")
        return options

    def _process_dialog_result(self, result):
        """Process dialog result and execute workflow."""
        try:
            # Parse result and execute appropriate workflow
            workflow_type = result[0]
            params = {
                'prompt': result[1],
                'negative_prompt': result[2],
                'width': result[3],
                'height': result[4],
                'strength': result[5],
                'upscale_factor': result[6],
                'control_type': ['canny', 'depth', 'pose', 'normal'][result[7]],
                'use_selection': result[8]
            }

            # Execute based on workflow type
            if workflow_type == 0:  # Text to Image
                self._execute_text_to_image(params)
            elif workflow_type == 1:  # Image to Image
                self._execute_image_to_image(params)
            elif workflow_type == 2:  # Inpainting
                self._execute_inpainting(params)
            elif workflow_type == 3:  # Outpainting
                self._execute_outpainting(params)
            elif workflow_type == 4:  # Upscaling
                self._execute_upscaling(params)
            elif workflow_type == 5:  # ControlNet
                self._execute_controlnet(params)
            else:
                # Custom workflow
                custom_index = workflow_type - 6
                if custom_index < len(self.workflows):
                    self._execute_custom_workflow(self.workflows[custom_index], params)

        except Exception as e:
            logger.error(f"Dialog processing failed: {e}")
            self.show_error(f"Operation failed: {e}")

    def _execute_text_to_image(self, params):
        """Execute text to image workflow."""
        try:
            from gimp_plugin.plugin import generate_from_text
            generate_from_text(
                params['prompt'],
                params['negative_prompt'],
                params['width'],
                params['height']
            )
        except ValueError as e:
            self.show_error(f"Invalid parameters: {e}")
        except Exception as e:
            self.show_error(f"Text to image failed: {e}")

    def _execute_image_to_image(self, params):
        """Execute image to image workflow."""
        try:
            from gimp_plugin.plugin import send_current_layer_for_img2img
            send_current_layer_for_img2img(params['prompt'], params['strength'])
        except ValueError as e:
            self.show_error(f"Invalid parameters: {e}")
        except Exception as e:
            self.show_error(f"Image to image failed: {e}")

    def _execute_inpainting(self, params):
        """Execute inpainting workflow."""
        try:
            from gimp_plugin.plugin import send_current_layer_for_inpaint
            send_current_layer_for_inpaint(params['prompt'], params['negative_prompt'])
        except ValueError as e:
            self.show_error(f"Invalid parameters: {e}")
        except Exception as e:
            self.show_error(f"Inpainting failed: {e}")

    def _execute_outpainting(self, params):
        """Execute outpainting workflow."""
        try:
            from gimp_plugin.plugin import send_current_layer_for_outpaint
            send_current_layer_for_outpaint(params['prompt'], params['negative_prompt'])
        except ValueError as e:
            self.show_error(f"Invalid parameters: {e}")
        except Exception as e:
            self.show_error(f"Outpainting failed: {e}")

    def _execute_upscaling(self, params):
        """Execute upscaling workflow."""
        try:
            from gimp_plugin.plugin import send_current_layer_for_upscale
            send_current_layer_for_upscale(params['upscale_factor'])
        except ValueError as e:
            self.show_error(f"Invalid parameters: {e}")
        except Exception as e:
            self.show_error(f"Upscaling failed: {e}")

    def _execute_controlnet(self, params):
        """Execute ControlNet workflow."""
        try:
            from gimp_plugin.plugin import send_current_layer_for_controlnet
            send_current_layer_for_controlnet(params['prompt'], params['control_type'])
        except ValueError as e:
            self.show_error(f"Invalid parameters: {e}")
        except Exception as e:
            self.show_error(f"ControlNet failed: {e}")

    def _execute_custom_workflow(self, workflow, params):
        """Execute custom workflow."""
        from gimp_plugin.plugin import _execute_workflow
        workflow_params = {
            "mode": workflow.get('mode', 'custom'),
            "workflow_name": workflow['name'],
            **params
        }
        _execute_workflow(workflow['mode'], workflow['name'], workflow_params,
                         export_image=True, export_mask=params.get('use_selection', False))

    def show_progress_dialog(self, task_id: str):
        """Show progress dialog for running workflow."""
        if not GIMP_AVAILABLE:
            return

        self.current_task_id = task_id

        # Create progress dialog
        progress_dialog = gimpfu.pdb.gimp_progress_init("ComfyUI Bridge Processing...")

        # Start monitoring progress
        self._monitor_progress()

        gimpfu.pdb.gimp_progress_end()

    def _monitor_progress(self):
        """Monitor workflow progress."""
        if not self.current_task_id:
            return

        try:
            from gimp_plugin.api_client import get_workflow_status

            while True:
                status = get_workflow_status(self.current_task_id)

                if status['status'] in ['completed', 'failed', 'cancelled']:
                    break

                # Update progress
                progress = status.get('progress', 0.0)
                current_node = status.get('current_node', '')

                if GIMP_AVAILABLE:
                    gimpfu.pdb.gimp_progress_set_text(f"Processing: {current_node}")
                    gimpfu.pdb.gimp_progress_update(progress)

                # Small delay
                import time
                time.sleep(0.5)

        except Exception as e:
            logger.error(f"Progress monitoring failed: {e}")

def update_status(message: str):
    """
    Update status message.

    Args:
        message (str): Status message.
    """
    if GIMP_AVAILABLE:
        try:
            gimp.message(message)
        except:
            pass
    logger.info(f"Status: {message}")

def show_error(message: str):
    """
    Show error message.

    Args:
        message (str): Error message.
    """
    if GIMP_AVAILABLE:
        try:
            gimp.message(f"ComfyUI Bridge Error: {message}")
        except:
            pass
    logger.error(f"Error: {message}")

def update_progress(progress: float, message: str = ""):
    """Update progress display."""
    if not GIMP_AVAILABLE:
        return

    try:
        if GIMP_AVAILABLE:
            gimpfu.pdb.gimp_progress_set_text(message or "Processing...")
            gimpfu.pdb.gimp_progress_update(progress)
    except Exception as e:
        logger.error(f"Failed to update progress: {e}")

def show_workflow_options(workflows: List[Dict[str, Any]]):
    """
    Show workflow options.

    Args:
        workflows (list): List of workflows.
    """
    if not GIMP_AVAILABLE:
        return

    # This would show a dialog with workflow options
    # For now, just log
    logger.info(f"Available workflows: {[w['name'] for w in workflows]}")