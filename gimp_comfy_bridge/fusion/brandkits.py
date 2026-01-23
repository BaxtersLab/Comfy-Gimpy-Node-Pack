"""
Brand kit management for consistent visual identity.
"""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass
import json
import yaml

logger = logging.getLogger(__name__)


@dataclass
class BrandKit:
    """A brand kit definition."""
    id: str
    name: str
    description: str
    version: str
    colors: Dict[str, str]  # Color palette
    fonts: Dict[str, Any]   # Font specifications
    logos: Dict[str, str]   # Logo paths/URLs
    guidelines: Dict[str, Any]  # Brand guidelines
    assets: Dict[str, str]  # Additional brand assets
    metadata: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BrandKit':
        """Create BrandKit from dictionary."""
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            description=data.get('description', ''),
            version=data.get('version', '1.0'),
            colors=data.get('colors', {}),
            fonts=data.get('fonts', {}),
            logos=data.get('logos', {}),
            guidelines=data.get('guidelines', {}),
            assets=data.get('assets', {}),
            metadata=data.get('metadata', {})
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'colors': self.colors,
            'fonts': self.fonts,
            'logos': self.logos,
            'guidelines': self.guidelines,
            'assets': self.assets,
            'metadata': self.metadata
        }


class BrandKitManager:
    """Manages brand kit loading and validation."""

    def __init__(self, kits_dir: Optional[Path] = None):
        self.kits_dir = kits_dir or Path("brand_kits")
        self.kits_dir.mkdir(parents=True, exist_ok=True)
        self._loaded_kits: Dict[str, BrandKit] = {}

    def load_brand_kit(self, kit_id: str) -> Optional[BrandKit]:
        """
        Load a brand kit by ID.

        Args:
            kit_id: Brand kit identifier

        Returns:
            BrandKit instance or None if not found
        """
        # Check cache first
        if kit_id in self._loaded_kits:
            return self._loaded_kits[kit_id]

        # Try to load from file
        kit_file = self.kits_dir / f"{kit_id}.json"
        if not kit_file.exists():
            kit_file = self.kits_dir / f"{kit_id}.yaml"
        if not kit_file.exists():
            kit_file = self.kits_dir / f"{kit_id}.yml"

        if kit_file.exists():
            try:
                kit_data = self._load_kit_file(kit_file)
                if kit_data:
                    kit = BrandKit.from_dict(kit_data)
                    self._validate_brand_kit(kit)
                    self._loaded_kits[kit_id] = kit
                    logger.info(f"Loaded brand kit: {kit_id}")
                    return kit
            except Exception as e:
                logger.error(f"Failed to load brand kit {kit_id}: {e}")

        logger.warning(f"Brand kit not found: {kit_id}")
        return None

    def _load_kit_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Load brand kit from file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix.lower() in ['.yaml', '.yml']:
                    return yaml.safe_load(f)
                else:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to parse brand kit file {file_path}: {e}")
            return None

    def _validate_brand_kit(self, kit: BrandKit) -> None:
        """Validate brand kit structure."""
        if not kit.id:
            raise ValueError("Brand kit must have an ID")
        if not kit.name:
            raise ValueError("Brand kit must have a name")

        # Validate colors (should be hex codes)
        for color_name, color_value in kit.colors.items():
            if not isinstance(color_value, str) or not color_value.startswith('#'):
                logger.warning(f"Invalid color format for {color_name}: {color_value}")

        # Validate required assets exist
        for asset_name, asset_path in kit.assets.items():
            if not Path(asset_path).exists():
                logger.warning(f"Brand kit asset not found: {asset_path}")

    def save_brand_kit(self, kit: BrandKit) -> bool:
        """
        Save a brand kit to disk.

        Args:
            kit: BrandKit to save

        Returns:
            True if saved successfully
        """
        try:
            kit_file = self.kits_dir / f"{kit.id}.json"
            with open(kit_file, 'w', encoding='utf-8') as f:
                json.dump(kit.to_dict(), f, indent=2, ensure_ascii=False)

            # Update cache
            self._loaded_kits[kit.id] = kit
            logger.info(f"Saved brand kit: {kit.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save brand kit {kit.id}: {e}")
            return False

    def list_brand_kits(self) -> List[Dict[str, Any]]:
        """List all available brand kits."""
        kits = []

        # Scan directory for kit files
        for kit_file in self.kits_dir.glob("*"):
            if kit_file.suffix.lower() in ['.json', '.yaml', '.yml']:
                try:
                    kit_data = self._load_kit_file(kit_file)
                    if kit_data and 'id' in kit_data:
                        kits.append({
                            'id': kit_data['id'],
                            'name': kit_data.get('name', kit_data['id']),
                            'description': kit_data.get('description', ''),
                            'version': kit_data.get('version', '1.0'),
                            'file': str(kit_file)
                        })
                except Exception as e:
                    logger.warning(f"Failed to read kit file {kit_file}: {e}")

        return kits

    def create_brand_kit_template(self,
                                kit_id: str,
                                name: str,
                                description: str = "") -> BrandKit:
        """
        Create a new brand kit template.

        Args:
            kit_id: Unique identifier for the kit
            name: Display name
            description: Optional description

        Returns:
            New BrandKit instance
        """
        kit = BrandKit(
            id=kit_id,
            name=name,
            description=description,
            version="1.0",
            colors={
                "primary": "#007ACC",
                "secondary": "#FF6B35",
                "accent": "#F7931E",
                "neutral": "#6B7280"
            },
            fonts={
                "heading": {
                    "family": "Arial",
                    "weight": "bold",
                    "size": 24
                },
                "body": {
                    "family": "Arial",
                    "weight": "normal",
                    "size": 14
                }
            },
            logos={},
            guidelines={
                "color_usage": "Use primary color for main elements",
                "typography": "Maintain consistent font hierarchy",
                "spacing": "Use 8px grid system"
            },
            assets={},
            metadata={
                "created_by": "Comfy Gimpy Studio",
                "template": True
            }
        )

        return kit

    def apply_brand_kit_to_prompt(self,
                                 prompt: str,
                                 kit: BrandKit) -> str:
        """
        Apply brand kit guidelines to a prompt.

        Args:
            prompt: Original prompt
            kit: Brand kit to apply

        Returns:
            Enhanced prompt with brand elements
        """
        enhanced_prompt = prompt

        # Add color descriptions if available
        if kit.colors:
            color_descriptions = []
            for color_name, color_hex in kit.colors.items():
                color_descriptions.append(f"{color_name} color: {color_hex}")
            if color_descriptions:
                enhanced_prompt += f", brand colors: {', '.join(color_descriptions)}"

        # Add typography hints
        if kit.fonts:
            font_styles = []
            for font_name, font_spec in kit.fonts.items():
                if isinstance(font_spec, dict):
                    family = font_spec.get('family', 'sans-serif')
                    weight = font_spec.get('weight', 'normal')
                    font_styles.append(f"{font_name} font: {family} {weight}")
            if font_styles:
                enhanced_prompt += f", typography: {', '.join(font_styles)}"

        return enhanced_prompt