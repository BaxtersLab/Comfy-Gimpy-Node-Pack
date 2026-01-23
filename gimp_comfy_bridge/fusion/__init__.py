"""
Style-Template Fusion Engine for Comfy Gimpy Studio.

This module provides capabilities for fusing templates, styles, and user prompts
to create consistent visual identities with multi-LoRA blending and brand kits.
"""

from .engine import FusionEngine, fuse, initialize_fusion_engine
from .blender import LoRABlender, StyleMixer
from .brandkits import BrandKit, BrandKitManager
from .variants import VariantGenerator
from .preview import PreviewGenerator

__all__ = [
    'FusionEngine',
    'fuse',
    'initialize_fusion_engine',
    'LoRABlender',
    'StyleMixer',
    'BrandKit',
    'BrandKitManager',
    'VariantGenerator',
    'PreviewGenerator'
]