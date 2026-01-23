"""
Brand Kit Validation Module.

Provides comprehensive validation for brand kit structures and components.
"""

import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from .kit import BrandKit, ColorPalette, Color, FontSpec, StylePreset, WorkflowPreset

logger = logging.getLogger(__name__)


class BrandKitValidationError(Exception):
    """Exception raised when brand kit validation fails."""
    pass


def validate_brandkit(kit: BrandKit, strict: bool = False) -> List[str]:
    """
    Validate a complete brand kit.

    Args:
        kit: BrandKit instance to validate
        strict: Whether to use strict validation rules

    Returns:
        List of validation error messages (empty if valid)

    Raises:
        BrandKitValidationError: If validation fails in strict mode
    """
    errors = []

    # Validate metadata
    errors.extend(validate_brand_metadata(kit.metadata))

    # Validate color palettes
    for palette in kit.color_palettes:
        errors.extend(validate_color_palette(palette))

    # Validate fonts
    for font_name, font_spec in kit.fonts.items():
        errors.extend(validate_font_spec(font_spec, font_name))

    # Validate style presets
    for preset in kit.style_presets:
        errors.extend(validate_style_preset(preset))

    # Validate workflow presets
    for preset in kit.workflow_presets:
        errors.extend(validate_workflow_preset(preset))

    # Validate logo paths
    errors.extend(validate_logo_paths(kit.logo_paths))

    # Validate layout preferences
    errors.extend(validate_layout_preferences(kit.layout_preferences))

    if strict and errors:
        raise BrandKitValidationError(f"Brand kit validation failed: {'; '.join(errors)}")

    return errors


def validate_brand_metadata(metadata) -> List[str]:
    """Validate brand metadata."""
    errors = []

    if not metadata.name or not metadata.name.strip():
        errors.append("Brand name is required")

    if len(metadata.name) > 100:
        errors.append("Brand name must be 100 characters or less")

    if not re.match(r'^[a-zA-Z0-9\s\-_]+$', metadata.name):
        errors.append("Brand name contains invalid characters")

    if not metadata.version or not re.match(r'^\d+\.\d+\.\d+$', metadata.version):
        errors.append("Version must be in format x.y.z")

    if len(metadata.description) > 500:
        errors.append("Description must be 500 characters or less")

    return errors


def validate_color_palette(palette: ColorPalette) -> List[str]:
    """Validate a color palette."""
    errors = []

    if not palette.name or not palette.name.strip():
        errors.append(f"Color palette name is required")

    if len(palette.name) > 50:
        errors.append(f"Color palette name '{palette.name}' must be 50 characters or less")

    total_colors = len(palette.primary_colors) + len(palette.secondary_colors) + \
                   len(palette.accent_colors) + len(palette.neutral_colors)

    if total_colors == 0:
        errors.append(f"Color palette '{palette.name}' must contain at least one color")

    if total_colors > 20:
        errors.append(f"Color palette '{palette.name}' contains too many colors (max 20)")

    # Validate individual colors
    all_colors = palette.primary_colors + palette.secondary_colors + \
                 palette.accent_colors + palette.neutral_colors

    for color in all_colors:
        errors.extend(validate_color(color))

    return errors


def validate_color(color: Color) -> List[str]:
    """Validate a single color."""
    errors = []

    if not color.name or not color.name.strip():
        errors.append("Color name is required")

    if not color.hex_value or not re.match(r'^#[0-9A-Fa-f]{6}$', color.hex_value):
        errors.append(f"Color '{color.name}' has invalid hex value '{color.hex_value}'")

    if color.rgb:
        if not all(0 <= c <= 255 for c in color.rgb):
            errors.append(f"Color '{color.name}' has invalid RGB values")

    if color.hsl:
        h, s, l = color.hsl
        if not (0 <= h <= 360 and 0 <= s <= 100 and 0 <= l <= 100):
            errors.append(f"Color '{color.name}' has invalid HSL values")

    if color.cmyk:
        if not all(0 <= c <= 100 for c in color.cmyk):
            errors.append(f"Color '{color.name}' has invalid CMYK values")

    return errors


def validate_font_spec(font_spec: FontSpec, font_name: str = "") -> List[str]:
    """Validate a font specification."""
    errors = []

    if not font_spec.family or not font_spec.family.strip():
        errors.append(f"Font family is required for '{font_name}'")

    valid_weights = ['normal', 'bold', 'lighter', 'bolder', '100', '200', '300', '400', '500', '600', '700', '800', '900']
    if font_spec.weight not in valid_weights:
        errors.append(f"Invalid font weight '{font_spec.weight}' for '{font_name}'")

    valid_styles = ['normal', 'italic', 'oblique']
    if font_spec.style not in valid_styles:
        errors.append(f"Invalid font style '{font_spec.style}' for '{font_name}'")

    if font_spec.size and (font_spec.size < 8 or font_spec.size > 200):
        errors.append(f"Font size {font_spec.size} out of range (8-200) for '{font_name}'")

    if len(font_spec.fallback_fonts) > 5:
        errors.append(f"Too many fallback fonts for '{font_name}' (max 5)")

    return errors


def validate_style_preset(preset: StylePreset) -> List[str]:
    """Validate a style preset."""
    errors = []

    if not preset.name or not preset.name.strip():
        errors.append("Style preset name is required")

    if len(preset.name) > 50:
        errors.append(f"Style preset name '{preset.name}' too long (max 50)")

    if not preset.loras:
        errors.append(f"Style preset '{preset.name}' must contain at least one LoRA")

    for lora_name, weight in preset.loras.items():
        if not isinstance(weight, (int, float)) or not (-2.0 <= weight <= 2.0):
            errors.append(f"Invalid LoRA weight {weight} for '{lora_name}' in preset '{preset.name}'")

    if len(preset.description) > 200:
        errors.append(f"Style preset description too long for '{preset.name}' (max 200)")

    return errors


def validate_workflow_preset(preset: WorkflowPreset) -> List[str]:
    """Validate a workflow preset."""
    errors = []

    if not preset.name or not preset.name.strip():
        errors.append("Workflow preset name is required")

    if len(preset.name) > 50:
        errors.append(f"Workflow preset name '{preset.name}' too long (max 50)")

    if not preset.workflow_path or not preset.workflow_path.strip():
        errors.append(f"Workflow path required for preset '{preset.name}'")

    # Check if workflow file exists (if it's a relative path)
    if preset.workflow_path and not Path(preset.workflow_path).is_absolute():
        # This would need context about the workflow directory
        pass

    if len(preset.description) > 200:
        errors.append(f"Workflow preset description too long for '{preset.name}' (max 200)")

    return errors


def validate_logo_paths(logo_paths: List[str]) -> List[str]:
    """Validate logo file paths."""
    errors = []

    if len(logo_paths) > 10:
        errors.append("Too many logo paths (max 10)")

    for path in logo_paths:
        if not path or not path.strip():
            errors.append("Empty logo path found")
            continue

        path_obj = Path(path)
        if path_obj.is_absolute() and not path_obj.exists():
            errors.append(f"Logo file does not exist: {path}")

        # Check file extension
        if path_obj.suffix.lower() not in ['.png', '.jpg', '.jpeg', '.svg', '.webp']:
            errors.append(f"Unsupported logo format: {path}")

    return errors


def validate_layout_preferences(preferences) -> List[str]:
    """Validate layout preferences."""
    errors = []

    # Validate aspect ratios
    for ratio in preferences.aspect_ratios:
        if not re.match(r'^\d+:\d+$', ratio):
            errors.append(f"Invalid aspect ratio format: {ratio}")

    # Validate preferred sizes
    for size in preferences.preferred_sizes:
        if not re.match(r'^\d+x\d+$', size):
            errors.append(f"Invalid size format: {size}")

    return errors


def validate_brandkit_json(json_data: Dict[str, Any]) -> List[str]:
    """
    Validate brand kit data from JSON/dict format.

    Args:
        json_data: Brand kit data as dictionary

    Returns:
        List of validation errors
    """
    errors = []

    required_keys = ['metadata', 'color_palettes', 'fonts', 'style_presets', 'workflow_presets']
    for key in required_keys:
        if key not in json_data:
            errors.append(f"Missing required key: {key}")

    if 'metadata' in json_data:
        # Basic metadata validation
        metadata = json_data['metadata']
        if not isinstance(metadata, dict):
            errors.append("Metadata must be a dictionary")
        elif 'name' not in metadata:
            errors.append("Metadata must contain 'name' field")

    return errors


def sanitize_brandkit_name(name: str) -> str:
    """
    Sanitize a brand kit name for safe file system usage.

    Args:
        name: Original name

    Returns:
        Sanitized name
    """
    # Remove invalid characters and replace with underscores
    sanitized = re.sub(r'[^\w\-_\s]', '_', name)
    # Replace spaces with underscores
    sanitized = re.sub(r'\s+', '_', sanitized)
    # Remove multiple underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Trim underscores from ends
    sanitized = sanitized.strip('_')
    # Ensure not empty
    if not sanitized:
        sanitized = "brand_kit"
    return sanitized.lower()


def check_brandkit_compatibility(kit: BrandKit, target_system: str) -> List[str]:
    """
    Check brand kit compatibility with a target system.

    Args:
        kit: BrandKit to check
        target_system: Target system identifier

    Returns:
        List of compatibility warnings/issues
    """
    warnings = []

    # Check for system-specific requirements
    if target_system == "gimp_plugin":
        # GIMP-specific checks
        if len(kit.color_palettes) > 5:
            warnings.append("GIMP plugin supports max 5 color palettes")

        for preset in kit.style_presets:
            if len(preset.loras) > 10:
                warnings.append(f"Style preset '{preset.name}' has too many LoRAs for GIMP plugin (max 10)")

    elif target_system == "web_interface":
        # Web interface checks
        for logo_path in kit.logo_paths:
            if not logo_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                warnings.append(f"Logo '{logo_path}' may not display properly in web interface")

    return warnings</content>
<parameter name="filePath">c:\Users\Baxter\Documents\ComfyUI_env\ComfyUI\custom_nodes\Comfy Gimpy Node Pack\gimp_comfy_bridge\brandkit\validator.py