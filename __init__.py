"""
Comfy Gimpy Studio — ComfyUI custom node entry point.
"""

try:
	from .comfy_nodes import (
		CGP_VGG19StyleTransfer,
		CGP_LoRABlend,
		CGP_WorkflowFileLoader,
		CGP_GimpBridgeStatus,
	)
	_NODES_LOADED = True
except Exception as e:
	import logging
	logging.getLogger(__name__).error(f"comfy_nodes import failed: {e}")
	_NODES_LOADED = False

if _NODES_LOADED:
	NODE_CLASS_MAPPINGS = {
		"CGP_VGG19StyleTransfer": CGP_VGG19StyleTransfer,
		"CGP_LoRABlend": CGP_LoRABlend,
		"CGP_WorkflowFileLoader": CGP_WorkflowFileLoader,
		"CGP_GimpBridgeStatus": CGP_GimpBridgeStatus,
	}
	NODE_DISPLAY_NAME_MAPPINGS = {
		"CGP_VGG19StyleTransfer": "VGG19 Style Transfer",
		"CGP_LoRABlend": "LoRA Blend",
		"CGP_WorkflowFileLoader": "Workflow File Loader",
		"CGP_GimpBridgeStatus": "Gimpy Bridge Status",
	}
else:
	NODE_CLASS_MAPPINGS = {}
	NODE_DISPLAY_NAME_MAPPINGS = {}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
