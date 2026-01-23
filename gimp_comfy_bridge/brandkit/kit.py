"""
Brand Kit Definition Module.

Defines the core data structures for brand identity management.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from enum import Enum


class ColorFormat(Enum):
    """Supported color formats."""
    HEX = "hex"
    RGB = "rgb"
    HSL = "hsl"
    CMYK = "cmyk"


@dataclass
class Color:
    """Represents a single color with multiple format support."""
    name: str
    hex_value: str
    rgb: Optional[tuple[int, int, int]] = None
    hsl: Optional[tuple[float, float, float]] = None
    cmyk: Optional[tuple[float, float, float, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert color to dictionary representation."""
        return {
            'name': self.name,
            'hex_value': self.hex_value,
            'rgb': list(self.rgb) if self.rgb else None,
            'hsl': list(self.hsl) if self.hsl else None,
            'cmyk': list(self.cmyk) if self.cmyk else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Color':
        """Create color from dictionary representation."""
        return cls(
            name=data['name'],
            hex_value=data['hex_value'],
            rgb=tuple(data['rgb']) if data.get('rgb') else None,
            hsl=tuple(data['hsl']) if data.get('hsl') else None,
            cmyk=tuple(data['cmyk']) if data.get('cmyk') else None,
        )


@dataclass
class ColorPalette:
    """Represents a color palette with primary, secondary, and accent colors."""
    name: str
    primary_colors: List[Color] = field(default_factory=list)
    secondary_colors: List[Color] = field(default_factory=list)
    accent_colors: List[Color] = field(default_factory=list)
    neutral_colors: List[Color] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert palette to dictionary representation."""
        return {
            'name': self.name,
            'primary_colors': [color.to_dict() for color in self.primary_colors],
            'secondary_colors': [color.to_dict() for color in self.secondary_colors],
            'accent_colors': [color.to_dict() for color in self.accent_colors],
            'neutral_colors': [color.to_dict() for color in self.neutral_colors],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ColorPalette':
        """Create palette from dictionary representation."""
        return cls(
            name=data['name'],
            primary_colors=[Color.from_dict(c) for c in data.get('primary_colors', [])],
            secondary_colors=[Color.from_dict(c) for c in data.get('secondary_colors', [])],
            accent_colors=[Color.from_dict(c) for c in data.get('accent_colors', [])],
            neutral_colors=[Color.from_dict(c) for c in data.get('neutral_colors', [])],
        )


@dataclass
class FontSpec:
    """Represents a font specification."""
    family: str
    weight: str = "normal"
    style: str = "normal"
    size: Optional[int] = None
    fallback_fonts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert font spec to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FontSpec':
        """Create font spec from dictionary representation."""
        return cls(**data)


@dataclass
class StylePreset:
    """Represents a style preset with LoRAs and weights."""
    name: str
    loras: Dict[str, float] = field(default_factory=dict)  # LoRA name -> weight
    description: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert style preset to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StylePreset':
        """Create style preset from dictionary representation."""
        return cls(**data)


@dataclass
class WorkflowPreset:
    """Represents a workflow preset."""
    name: str
    workflow_path: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert workflow preset to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowPreset':
        """Create workflow preset from dictionary representation."""
        return cls(**data)


@dataclass
class LayoutPreferences:
    """Represents layout preferences for brand consistency."""
    aspect_ratios: List[str] = field(default_factory=lambda: ["16:9", "1:1", "4:3"])
    preferred_sizes: List[str] = field(default_factory=lambda: ["1024x1024", "512x512", "1024x512"])
    composition_rules: Dict[str, Any] = field(default_factory=dict)
    spacing_guidelines: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert layout preferences to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LayoutPreferences':
        """Create layout preferences from dictionary representation."""
        return cls(**data)


@dataclass
class BrandMetadata:
    """Represents brand metadata."""
    name: str
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    license: str = ""
    website: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary representation."""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BrandMetadata':
        """Create metadata from dictionary representation."""
        data_copy = data.copy()
        data_copy['created_at'] = datetime.fromisoformat(data['created_at'])
        data_copy['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data_copy)


@dataclass
class BrandKit:
    """Complete brand kit definition."""
    metadata: BrandMetadata

    # Visual assets
    logo_paths: List[str] = field(default_factory=list)
    color_palettes: List[ColorPalette] = field(default_factory=list)

    # Typography
    fonts: Dict[str, FontSpec] = field(default_factory=dict)  # font_name -> FontSpec

    # Style presets
    style_presets: List[StylePreset] = field(default_factory=list)

    # Workflow presets
    workflow_presets: List[WorkflowPreset] = field(default_factory=list)

    # Layout preferences
    layout_preferences: LayoutPreferences = field(default_factory=LayoutPreferences)

    # Additional custom data
    custom_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert brand kit to dictionary representation."""
        return {
            'metadata': self.metadata.to_dict(),
            'logo_paths': self.logo_paths,
            'color_palettes': [palette.to_dict() for palette in self.color_palettes],
            'fonts': {name: font.to_dict() for name, font in self.fonts.items()},
            'style_presets': [preset.to_dict() for preset in self.style_presets],
            'workflow_presets': [preset.to_dict() for preset in self.workflow_presets],
            'layout_preferences': self.layout_preferences.to_dict(),
            'custom_data': self.custom_data,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BrandKit':
        """Create brand kit from dictionary representation."""
        return cls(
            metadata=BrandMetadata.from_dict(data['metadata']),
            logo_paths=data.get('logo_paths', []),
            color_palettes=[ColorPalette.from_dict(p) for p in data.get('color_palettes', [])],
            fonts={name: FontSpec.from_dict(f) for name, f in data.get('fonts', {}).items()},
            style_presets=[StylePreset.from_dict(p) for p in data.get('style_presets', [])],
            workflow_presets=[WorkflowPreset.from_dict(p) for p in data.get('workflow_presets', [])],
            layout_preferences=LayoutPreferences.from_dict(data.get('layout_preferences', {})),
            custom_data=data.get('custom_data', {}),
        )

    def to_json(self, indent: int = 2) -> str:
        """Convert brand kit to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> 'BrandKit':
        """Create brand kit from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def save_to_file(self, path: Union[str, Path]) -> None:
        """Save brand kit to JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding='utf-8')

    @classmethod
    def load_from_file(cls, path: Union[str, Path]) -> 'BrandKit':
        """Load brand kit from JSON file."""
        path = Path(path)
        return cls.from_json(path.read_text(encoding='utf-8'))

    @property
    def primary_palette(self) -> Optional[ColorPalette]:
        """Get the primary color palette."""
        return self.color_palettes[0] if self.color_palettes else None

    @property
    def primary_font(self) -> Optional[FontSpec]:
        """Get the primary font."""
        return self.fonts.get('primary') or self.fonts.get('heading')

    def get_style_preset(self, name: str) -> Optional[StylePreset]:
        """Get a style preset by name."""
        for preset in self.style_presets:
            if preset.name == name:
                return preset
        return None

    def get_workflow_preset(self, name: str) -> Optional[WorkflowPreset]:
        """Get a workflow preset by name."""
        for preset in self.workflow_presets:
            if preset.name == name:
                return preset
        return None</content>
<parameter name="filePath">c:\Users\Baxter\Documents\ComfyUI_env\ComfyUI\custom_nodes\Comfy Gimpy Node Pack\gimp_comfy_bridge\brandkit\kit.py