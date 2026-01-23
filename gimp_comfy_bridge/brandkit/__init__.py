"""
Full Branding Kit System.

Provides comprehensive brand identity management for Comfy Gimpy Studio,
enabling users to define, save, load, sync, and apply brand identities
across all templates, styles, workflows, and AI generations.
"""

from .kit import BrandKit, ColorPalette, FontSpec, StylePreset, WorkflowPreset, LayoutPreferences, BrandMetadata
from .loader import load_brandkit, load_brandkit_from_path, list_brandkits
from .saver import save_brandkit, save_brandkit_to_path, create_brandkit_backup
from .validator import validate_brandkit, BrandKitValidationError, validate_color_palette, validate_font_spec
from .applier import BrandKitApplier, apply_brandkit_to_template, apply_brandkit_to_style, apply_brandkit_to_workflow
from .palette import ColorPaletteManager, harmonize_palette, extract_palette_from_image
from .fonts import FontManager, load_font, get_font_fallbacks
from .styles import StyleManager, blend_style_presets, create_brand_style_variant
from .preview import BrandKitPreviewGenerator, generate_brandkit_preview, generate_variant_previews

__all__ = [
    # Core brand kit classes
    'BrandKit',
    'ColorPalette',
    'FontSpec',
    'StylePreset',
    'WorkflowPreset',
    'LayoutPreferences',
    'BrandMetadata',

    # Loading and saving
    'load_brandkit',
    'load_brandkit_from_path',
    'list_brandkits',
    'save_brandkit',
    'save_brandkit_to_path',
    'create_brandkit_backup',

    # Validation
    'validate_brandkit',
    'BrandKitValidationError',
    'validate_color_palette',
    'validate_font_spec',

    # Application
    'BrandKitApplier',
    'apply_brandkit_to_template',
    'apply_brandkit_to_style',
    'apply_brandkit_to_workflow',

    # Color palette management
    'ColorPaletteManager',
    'harmonize_palette',
    'extract_palette_from_image',

    # Font management
    'FontManager',
    'load_font',
    'get_font_fallbacks',

    # Style management
    'StyleManager',
    'blend_style_presets',
    'create_brand_style_variant',

    # Preview generation
    'BrandKitPreviewGenerator',
    'generate_brandkit_preview',
    'generate_variant_previews',
]</content>
<parameter name="filePath">c:\Users\Baxter\Documents\ComfyUI_env\ComfyUI\custom_nodes\Comfy Gimpy Node Pack\gimp_comfy_bridge\brandkit\__init__.py