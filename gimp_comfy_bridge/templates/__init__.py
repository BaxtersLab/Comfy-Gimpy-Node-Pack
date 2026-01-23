"""
Template Engine for Comfy Gimpy Studio.

This module provides a complete template system for loading, managing, and
integrating templates with GIMP and ComfyUI workflows.
"""

from .registry import TemplateRegistry
from .loader import TemplateLoader
from .metadata import TemplateMetadata, load_metadata, validate_metadata
from .preview import load_preview

__all__ = [
    'TemplateRegistry',
    'TemplateLoader',
    'TemplateMetadata',
    'load_metadata',
    'validate_metadata',
    'load_preview'
]