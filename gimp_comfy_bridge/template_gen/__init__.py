"""
AI-Assisted Template Generation for Comfy Gimpy Studio (Phase 12)

This module provides automatic generation of design templates using AI,
integrating with workflow auto-generation, style fusion, and async processing.
"""

from .generator import TemplateGenerator, GenerationOptions
from .layout_builder import LayoutBuilder, LayoutElement
from .metadata_builder import MetadataBuilder, TemplateMetadata
from .preview_builder import PreviewBuilder
from .variants import VariantGenerator
from .save import TemplateSaver

__all__ = [
    'TemplateGenerator',
    'GenerationOptions',
    'LayoutBuilder',
    'LayoutElement',
    'MetadataBuilder',
    'TemplateMetadata',
    'PreviewBuilder',
    'VariantGenerator',
    'TemplateSaver'
]