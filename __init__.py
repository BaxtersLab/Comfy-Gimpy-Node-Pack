# Comfy Gimpy Studio — ComfyUI custom node entry point
#
# NOTE: This repository is primarily a standalone GIMP-ComfyUI bridge application.
# No ComfyUI node classes have been implemented yet. The ComfyUI node layer
# is documented as future work in DEVNOTES.md.
#
# The pack loads cleanly with empty mappings so it does not crash ComfyUI on startup.

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
