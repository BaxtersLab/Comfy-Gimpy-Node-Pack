"""
Pack creation and export functionality.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import json
import zipfile
import hashlib
from datetime import datetime
import shutil

logger = logging.getLogger(__name__)


class Packager:
    """Handles creation and export of marketplace packs."""

    def __init__(self, packs_dir: Optional[Path] = None):
        self.packs_dir = packs_dir or Path("packs")
        self.packs_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path("temp/packaging")
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def create_pack(self,
                   pack_type: str,
                   name: str,
                   version: str,
                   content: Dict[str, Any],
                   metadata: Optional[Dict[str, Any]] = None,
                   previews: Optional[List[Path]] = None,
                   dependencies: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Create a pack from content and metadata.

        Args:
            pack_type: Type of pack ("template", "style", "workflow", "model")
            name: Pack name
            version: Version string
            content: Main pack content
            metadata: Additional metadata
            previews: List of preview image paths
            dependencies: List of dependencies

        Returns:
            Pack manifest dictionary
        """
        logger.info(f"Creating {pack_type} pack: {name} v{version}")

        # Generate pack ID
        pack_id = self._generate_pack_id(pack_type, name)

        # Create manifest
        manifest = {
            "id": pack_id,
            "type": pack_type,
            "name": name,
            "version": version,
            "created_at": datetime.now().isoformat(),
            "content": content,
            "metadata": metadata or {},
            "previews": [],
            "dependencies": dependencies or [],
            "license": metadata.get("license", "MIT") if metadata else "MIT",
            "author": metadata.get("author", "Unknown") if metadata else "Unknown",
            "description": metadata.get("description", "") if metadata else "",
            "tags": metadata.get("tags", []) if metadata else []
        }

        # Process previews
        if previews:
            manifest["previews"] = self._process_previews(previews, pack_id)

        # Calculate checksums
        manifest["checksums"] = self._calculate_checksums(content, previews)

        # Validate pack structure
        from .validator import PackValidator
        validator = PackValidator()
        if not validator.validate_pack(manifest):
            raise ValueError("Pack validation failed")

        logger.info(f"Pack created successfully: {pack_id}")
        return manifest

    def create_brand_kit_pack(self,
                             brand_kit_id: str,
                             name: str,
                             version: str = "1.0.0",
                             metadata: Optional[Dict[str, Any]] = None,
                             include_preview: bool = True) -> Dict[str, Any]:
        """
        Create a marketplace pack for a brand kit.

        Args:
            brand_kit_id: ID of the brand kit to package
            name: Display name for the pack
            version: Version string
            metadata: Additional metadata
            include_preview: Whether to generate and include preview

        Returns:
            Pack manifest dictionary
        """
        from ..brandkit import load_brandkit

        # Load the brand kit
        brand_kit = load_brandkit(brand_kit_id)
        if not brand_kit:
            raise ValueError(f"Brand kit '{brand_kit_id}' not found")

        # Prepare content
        content = {
            "brand_kit": brand_kit.to_dict(),
            "type": "brand_kit"
        }

        # Prepare metadata
        pack_metadata = metadata or {}
        pack_metadata.update({
            "brand_kit_id": brand_kit_id,
            "brand_name": brand_kit.name,
            "description": brand_kit.description or f"Brand kit for {brand_kit.name}",
            "author": brand_kit.author or "Unknown",
            "tags": ["brand-kit"] + (pack_metadata.get("tags", [])),
            "brand_colors": list(brand_kit.colors.keys()) if brand_kit.colors else [],
            "brand_fonts": list(brand_kit.fonts.keys()) if brand_kit.fonts else [],
            "has_styles": bool(brand_kit.styles),
            "has_workflows": bool(brand_kit.workflows)
        })

        # Generate preview if requested
        previews = None
        if include_preview:
            try:
                from ..brandkit.preview import generate_brand_kit_preview
                preview_path = generate_brand_kit_preview(brand_kit, self.temp_dir / f"{brand_kit_id}_preview.png")
                if preview_path.exists():
                    previews = [preview_path]
            except Exception as e:
                logger.warning(f"Failed to generate brand kit preview: {e}")

        # Create the pack
        return self.create_pack(
            pack_type="brand_kit",
            name=name,
            version=version,
            content=content,
            metadata=pack_metadata,
            previews=previews
        )

    def export_pack(self,
                   manifest: Dict[str, Any],
                   output_path: Optional[Path] = None,
                   compress: bool = True) -> Path:
        """
        Export a pack to a distributable file.

        Args:
            manifest: Pack manifest
            output_path: Output path (optional)
            compress: Whether to compress the pack

        Returns:
            Path to exported pack file
        """
        pack_id = manifest["id"]
        pack_name = manifest["name"]
        version = manifest["version"]

        if output_path is None:
            filename = f"{pack_id}_v{version}.zip" if compress else f"{pack_id}_v{version}"
            output_path = self.packs_dir / filename

        logger.info(f"Exporting pack to: {output_path}")

        if compress:
            self._export_zip(manifest, output_path)
        else:
            self._export_directory(manifest, output_path)

        # Verify export
        if not output_path.exists():
            raise FileNotFoundError(f"Export failed: {output_path}")

        logger.info(f"Pack exported successfully: {output_path}")
        return output_path

    def _generate_pack_id(self, pack_type: str, name: str) -> str:
        """Generate a unique pack ID."""
        # Clean and format the name
        clean_name = "".join(c for c in name.lower() if c.isalnum() or c in "._-")
        pack_id = f"{pack_type}_{clean_name}"

        # Ensure uniqueness by adding hash if needed
        if (self.packs_dir / f"{pack_id}.zip").exists():
            name_hash = hashlib.md5(name.encode()).hexdigest()[:6]
            pack_id = f"{pack_type}_{clean_name}_{name_hash}"

        return pack_id

    def _process_previews(self, preview_paths: List[Path], pack_id: str) -> List[Dict[str, Any]]:
        """Process preview images and return metadata."""
        previews = []
        preview_dir = self.temp_dir / pack_id / "previews"
        preview_dir.mkdir(parents=True, exist_ok=True)

        for i, preview_path in enumerate(preview_paths):
            if preview_path.exists():
                # Copy preview to temp directory
                ext = preview_path.suffix
                preview_filename = f"preview_{i+1}{ext}"
                temp_preview_path = preview_dir / preview_filename

                shutil.copy2(preview_path, temp_preview_path)

                # Calculate checksum
                with open(temp_preview_path, 'rb') as f:
                    checksum = hashlib.md5(f.read()).hexdigest()

                previews.append({
                    "filename": preview_filename,
                    "path": str(preview_path),
                    "checksum": checksum,
                    "size": temp_preview_path.stat().st_size
                })

        return previews

    def _calculate_checksums(self,
                           content: Dict[str, Any],
                           previews: Optional[List[Path]] = None) -> Dict[str, str]:
        """Calculate checksums for pack content."""
        checksums = {}

        # Content checksum
        content_str = json.dumps(content, sort_keys=True)
        checksums["content"] = hashlib.md5(content_str.encode()).hexdigest()

        # Preview checksums
        if previews:
            for i, preview_path in enumerate(previews):
                if preview_path.exists():
                    with open(preview_path, 'rb') as f:
                        checksums[f"preview_{i+1}"] = hashlib.md5(f.read()).hexdigest()

        # Overall pack checksum
        all_data = content_str
        if previews:
            for preview_path in previews:
                if preview_path.exists():
                    with open(preview_path, 'rb') as f:
                        all_data += f.read().decode('utf-8', errors='ignore')

        checksums["overall"] = hashlib.md5(all_data.encode()).hexdigest()

        return checksums

    def _export_zip(self, manifest: Dict[str, Any], output_path: Path):
        """Export pack as ZIP file."""
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Write manifest
            manifest_json = json.dumps(manifest, indent=2, ensure_ascii=False)
            zf.writestr("manifest.json", manifest_json)

            # Write content files if they exist
            content = manifest.get("content", {})
            if isinstance(content, dict) and "files" in content:
                for file_info in content["files"]:
                    file_path = file_info.get("path")
                    if file_path and Path(file_path).exists():
                        zf.write(file_path, f"content/{Path(file_path).name}")

            # Write preview files
            for preview in manifest.get("previews", []):
                preview_path = self.temp_dir / manifest["id"] / "previews" / preview["filename"]
                if preview_path.exists():
                    zf.write(preview_path, f"previews/{preview['filename']}")

    def _export_directory(self, manifest: Dict[str, Any], output_path: Path):
        """Export pack as directory structure."""
        output_path.mkdir(parents=True, exist_ok=True)

        # Write manifest
        manifest_path = output_path / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        # Copy content files
        content_dir = output_path / "content"
        content_dir.mkdir(exist_ok=True)

        content = manifest.get("content", {})
        if isinstance(content, dict) and "files" in content:
            for file_info in content["files"]:
                file_path = file_info.get("path")
                if file_path and Path(file_path).exists():
                    shutil.copy2(file_path, content_dir / Path(file_path).name)

        # Copy preview files
        preview_dir = output_path / "previews"
        preview_dir.mkdir(exist_ok=True)

        for preview in manifest.get("previews", []):
            preview_path = self.temp_dir / manifest["id"] / "previews" / preview["filename"]
            if preview_path.exists():
                shutil.copy2(preview_path, preview_dir / preview["filename"])


# Convenience functions
def create_pack(pack_type: str,
               name: str,
               version: str,
               content: Dict[str, Any],
               metadata: Optional[Dict[str, Any]] = None,
               previews: Optional[List[Path]] = None,
               dependencies: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Convenience function to create a pack.

    Args:
        pack_type: Type of pack ("template", "style", "workflow", "model")
        name: Pack name
        version: Version string
        content: Main pack content
        metadata: Additional metadata
        previews: List of preview image paths
        dependencies: List of dependencies

    Returns:
        Pack manifest dictionary
    """
    packager = Packager()
    return packager.create_pack(pack_type, name, version, content, metadata, previews, dependencies)


def export_pack(manifest: Dict[str, Any],
               output_path: Optional[Path] = None,
               compress: bool = True) -> Path:
    """
    Convenience function to export a pack.

    Args:
        manifest: Pack manifest
        output_path: Output path (optional)
        compress: Whether to compress the pack

    Returns:
        Path to exported pack file
    """
    packager = Packager()
    return packager.export_pack(manifest, output_path, compress)