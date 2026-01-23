"""
Brand Kit Saving Module.

Provides functionality to save brand kits to various destinations including
local filesystem and cloud sync providers with versioning support.
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Optional, Union
from datetime import datetime

from .kit import BrandKit
from ..shared.config import ConfigManager
from ..sync import SyncManager

logger = logging.getLogger(__name__)


class BrandKitSaveError(Exception):
    """Exception raised when brand kit saving fails."""
    pass


def save_brandkit(kit: BrandKit, name_or_path: Optional[str] = None,
                  config_manager: Optional[ConfigManager] = None,
                  create_backup: bool = True) -> str:
    """
    Save a brand kit to the specified location.

    Args:
        kit: BrandKit instance to save
        name_or_path: Optional name or path (uses kit name if not provided)
        config_manager: Optional config manager for path resolution
        create_backup: Whether to create a backup before saving

    Returns:
        Path where the brand kit was saved

    Raises:
        BrandKitSaveError: If saving fails
    """
    try:
        # Determine save path
        if name_or_path:
            path = Path(name_or_path)
            if path.is_dir():
                path = path / f"{kit.metadata.name}.json"
        else:
            if config_manager:
                brandkit_dir = Path(config_manager.get('brandkit.directory', 'brand_kits'))
                brandkit_dir.mkdir(parents=True, exist_ok=True)
                path = brandkit_dir / f"{kit.metadata.name}.json"
            else:
                path = Path(f"{kit.metadata.name}.json")

        # Create backup if requested
        if create_backup and path.exists():
            create_brandkit_backup(str(path))

        # Update metadata
        kit.metadata.updated_at = datetime.now()

        # Save to file
        kit.save_to_file(path)

        # Sync to cloud if available
        try:
            from ..sync import get_sync_manager
            sync_manager = get_sync_manager()
            if sync_manager and config_manager and config_manager.get('brandkit.sync_enabled', True):
                sync_brandkit_to_cloud(kit, sync_manager)
        except ImportError:
            logger.debug("Sync manager not available for brand kit saving")

        logger.info(f"Brand kit '{kit.metadata.name}' saved to '{path}'")
        return str(path)

    except Exception as e:
        logger.error(f"Failed to save brand kit '{kit.metadata.name}': {e}")
        raise BrandKitSaveError(f"Failed to save brand kit '{kit.metadata.name}': {e}") from e


def save_brandkit_to_path(kit: BrandKit, path: Union[str, Path]) -> None:
    """
    Save a brand kit to a specific file path.

    Args:
        kit: BrandKit instance to save
        path: File path to save to

    Raises:
        BrandKitSaveError: If saving fails
    """
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Update metadata
        kit.metadata.updated_at = datetime.now()

        kit.save_to_file(path)
        logger.info(f"Brand kit '{kit.metadata.name}' saved to '{path}'")

    except Exception as e:
        logger.error(f"Failed to save brand kit to path '{path}': {e}")
        raise BrandKitSaveError(f"Failed to save brand kit to path '{path}': {e}") from e


def sync_brandkit_to_cloud(kit: BrandKit, sync_manager: SyncManager) -> None:
    """
    Sync a brand kit to cloud storage.

    Args:
        kit: BrandKit instance to sync
        sync_manager: Sync manager instance

    Raises:
        BrandKitSaveError: If sync fails
    """
    try:
        # Convert to JSON
        json_content = kit.to_json()

        # Upload to sync provider
        sync_path = f"brandkits/{kit.metadata.name}.json"
        sync_manager.upload_file(sync_path, json_content)

        logger.info(f"Brand kit '{kit.metadata.name}' synced to cloud")

    except Exception as e:
        logger.error(f"Failed to sync brand kit '{kit.metadata.name}' to cloud: {e}")
        raise BrandKitSaveError(f"Failed to sync brand kit '{kit.metadata.name}' to cloud: {e}") from e


def create_brandkit_backup(kit_path: Union[str, Path]) -> Optional[str]:
    """
    Create a backup of an existing brand kit.

    Args:
        kit_path: Path to the brand kit file

    Returns:
        Path to the backup file, or None if backup failed
    """
    try:
        kit_path = Path(kit_path)
        if not kit_path.exists():
            return None

        # Load existing kit
        kit = BrandKit.load_from_file(kit_path)

        # Create backup directory
        backup_dir = kit_path.parent / "backups" / kit.metadata.name
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"{kit.metadata.name}_{kit.metadata.version}_{timestamp}.json"

        # Copy file
        shutil.copy2(kit_path, backup_path)

        logger.info(f"Backup created: '{backup_path}'")
        return str(backup_path)

    except Exception as e:
        logger.error(f"Failed to create backup for '{kit_path}': {e}")
        return None


def export_brandkit_for_packaging(kit: BrandKit, export_path: Union[str, Path],
                                  include_assets: bool = True) -> str:
    """
    Export a brand kit for packaging/distribution.

    Args:
        kit: BrandKit instance to export
        export_path: Directory to export to
        include_assets: Whether to include referenced assets

    Returns:
        Path to the exported brand kit

    Raises:
        BrandKitSaveError: If export fails
    """
    try:
        export_path = Path(export_path)
        export_path.mkdir(parents=True, exist_ok=True)

        # Create export kit (copy to avoid modifying original)
        export_kit = BrandKit.from_dict(kit.to_dict())

        # Handle asset references
        if include_assets:
            asset_paths = []
            for logo_path in kit.logo_paths:
                logo_file = Path(logo_path)
                if logo_file.exists():
                    # Copy asset to export directory
                    asset_dir = export_path / "assets"
                    asset_dir.mkdir(exist_ok=True)
                    shutil.copy2(logo_file, asset_dir / logo_file.name)
                    asset_paths.append(f"assets/{logo_file.name}")

            export_kit.logo_paths = asset_paths

        # Save exported kit
        kit_path = export_path / f"{kit.metadata.name}.json"
        export_kit.save_to_file(kit_path)

        # Create manifest
        manifest = {
            'name': kit.metadata.name,
            'version': kit.metadata.version,
            'description': kit.metadata.description,
            'type': 'brandkit',
            'exported_at': datetime.now().isoformat(),
            'includes_assets': include_assets,
        }

        manifest_path = export_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')

        logger.info(f"Brand kit '{kit.metadata.name}' exported to '{export_path}'")
        return str(kit_path)

    except Exception as e:
        logger.error(f"Failed to export brand kit '{kit.metadata.name}': {e}")
        raise BrandKitSaveError(f"Failed to export brand kit '{kit.metadata.name}': {e}") from e


def create_brandkit_from_template(template_name: str, config_manager: Optional[ConfigManager] = None) -> BrandKit:
    """
    Create a new brand kit from a template.

    Args:
        template_name: Name of the template to use
        config_manager: Optional config manager

    Returns:
        New BrandKit instance

    Raises:
        BrandKitSaveError: If template loading fails
    """
    try:
        # Load template (this would be implemented based on available templates)
        # For now, create a basic template
        from .kit import BrandMetadata, ColorPalette, Color, FontSpec, StylePreset

        metadata = BrandMetadata(
            name=template_name,
            description=f"Brand kit created from {template_name} template",
            author="Comfy Gimpy Studio",
        )

        # Basic color palette
        primary_palette = ColorPalette(
            name="Primary",
            primary_colors=[
                Color("Primary Blue", "#0066CC", (0, 102, 204)),
                Color("Primary Green", "#00CC66", (0, 204, 102)),
            ],
            secondary_colors=[
                Color("Secondary Gray", "#666666", (102, 102, 102)),
            ]
        )

        # Basic fonts
        fonts = {
            "heading": FontSpec("Arial", "bold", "normal", 24, ["Helvetica", "sans-serif"]),
            "body": FontSpec("Arial", "normal", "normal", 16, ["Helvetica", "sans-serif"]),
        }

        # Basic style preset
        style_preset = StylePreset(
            name="Default Style",
            loras={"brand_style_v1": 0.8},
            description="Default brand style preset",
            tags=["brand", "default"]
        )

        kit = BrandKit(
            metadata=metadata,
            color_palettes=[primary_palette],
            fonts=fonts,
            style_presets=[style_preset],
        )

        logger.info(f"Created brand kit from template '{template_name}'")
        return kit

    except Exception as e:
        logger.error(f"Failed to create brand kit from template '{template_name}': {e}")
        raise BrandKitSaveError(f"Failed to create brand kit from template '{template_name}': {e}") from e</content>
<parameter name="filePath">c:\Users\Baxter\Documents\ComfyUI_env\ComfyUI\custom_nodes\Comfy Gimpy Node Pack\gimp_comfy_bridge\brandkit\saver.py