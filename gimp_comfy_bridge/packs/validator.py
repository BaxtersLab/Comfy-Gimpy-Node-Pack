"""
Pack validation functionality.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import json
import hashlib
import re

logger = logging.getLogger(__name__)


class PackValidator:
    """Validates pack structure and content."""

    def __init__(self):
        self.required_fields = {
            "id": str,
            "type": str,
            "name": str,
            "version": str,
            "created_at": str,
            "content": dict,
            "metadata": dict,
            "license": str,
            "author": str
        }

        self.valid_pack_types = ["template", "style", "workflow", "model"]

        # Version regex pattern (semantic versioning)
        self.version_pattern = re.compile(r'^\d+\.\d+\.\d+(-[\w\.\-]+)?(\+[\w\.\-]+)?$')

    def validate_pack(self, manifest: Dict[str, Any]) -> bool:
        """
        Validate a pack manifest.

        Args:
            manifest: Pack manifest dictionary

        Returns:
            True if valid, False otherwise
        """
        try:
            # Check required fields
            if not self._validate_required_fields(manifest):
                return False

            # Validate pack type
            if not self._validate_pack_type(manifest):
                return False

            # Validate version format
            if not self._validate_version(manifest):
                return False

            # Validate content structure
            if not self._validate_content(manifest):
                return False

            # Validate metadata
            if not self._validate_metadata(manifest):
                return False

            # Validate dependencies
            if not self._validate_dependencies(manifest):
                return False

            # Validate previews
            if not self._validate_previews(manifest):
                return False

            # Validate checksums
            if not self._validate_checksums(manifest):
                return False

            logger.info(f"Pack validation successful: {manifest['id']}")
            return True

        except Exception as e:
            logger.error(f"Pack validation failed: {e}")
            return False

    def _validate_required_fields(self, manifest: Dict[str, Any]) -> bool:
        """Validate that all required fields are present and correct type."""
        for field, expected_type in self.required_fields.items():
            if field not in manifest:
                logger.error(f"Missing required field: {field}")
                return False

            if not isinstance(manifest[field], expected_type):
                logger.error(f"Field {field} has wrong type. Expected {expected_type.__name__}, got {type(manifest[field]).__name__}")
                return False

        return True

    def _validate_pack_type(self, manifest: Dict[str, Any]) -> bool:
        """Validate pack type."""
        pack_type = manifest.get("type")
        if pack_type not in self.valid_pack_types:
            logger.error(f"Invalid pack type: {pack_type}. Must be one of: {self.valid_pack_types}")
            return False
        return True

    def _validate_version(self, manifest: Dict[str, Any]) -> bool:
        """Validate version format (semantic versioning)."""
        version = manifest.get("version", "")
        if not self.version_pattern.match(version):
            logger.error(f"Invalid version format: {version}. Must follow semantic versioning (e.g., 1.0.0)")
            return False
        return True

    def _validate_content(self, manifest: Dict[str, Any]) -> bool:
        """Validate content structure based on pack type."""
        pack_type = manifest.get("type")
        content = manifest.get("content", {})

        if pack_type == "template":
            return self._validate_template_content(content)
        elif pack_type == "style":
            return self._validate_style_content(content)
        elif pack_type == "workflow":
            return self._validate_workflow_content(content)
        elif pack_type == "model":
            return self._validate_model_content(content)
        else:
            logger.error(f"Unknown pack type for content validation: {pack_type}")
            return False

    def _validate_template_content(self, content: Dict[str, Any]) -> bool:
        """Validate template pack content."""
        required_keys = ["layout", "parameters"]
        for key in required_keys:
            if key not in content:
                logger.error(f"Template pack missing required content key: {key}")
                return False
        return True

    def _validate_style_content(self, content: Dict[str, Any]) -> bool:
        """Validate style pack content."""
        # Styles can have various structures, be more flexible
        if not content:
            logger.error("Style pack content cannot be empty")
            return False
        return True

    def _validate_workflow_content(self, content: Dict[str, Any]) -> bool:
        """Validate workflow pack content."""
        required_keys = ["nodes", "connections"]
        for key in required_keys:
            if key not in content:
                logger.error(f"Workflow pack missing required content key: {key}")
                return False
        return True

    def _validate_model_content(self, content: Dict[str, Any]) -> bool:
        """Validate model pack content."""
        required_keys = ["model_path", "config"]
        for key in required_keys:
            if key not in content:
                logger.error(f"Model pack missing required content key: {key}")
                return False
        return True

    def _validate_metadata(self, manifest: Dict[str, Any]) -> bool:
        """Validate metadata structure."""
        metadata = manifest.get("metadata", {})

        # Check for common metadata issues
        if "tags" in metadata and not isinstance(metadata["tags"], list):
            logger.error("Metadata 'tags' must be a list")
            return False

        if "homepage" in metadata:
            homepage = metadata["homepage"]
            if not isinstance(homepage, str) or not homepage.startswith(("http://", "https://")):
                logger.error("Metadata 'homepage' must be a valid URL")
                return False

        return True

    def _validate_dependencies(self, manifest: Dict[str, Any]) -> bool:
        """Validate dependencies structure."""
        dependencies = manifest.get("dependencies", [])

        if not isinstance(dependencies, list):
            logger.error("Dependencies must be a list")
            return False

        for dep in dependencies:
            if not isinstance(dep, dict):
                logger.error("Each dependency must be a dictionary")
                return False

            required_dep_keys = ["name", "version"]
            for key in required_dep_keys:
                if key not in dep:
                    logger.error(f"Dependency missing required key: {key}")
                    return False

            # Validate dependency version
            dep_version = dep.get("version", "")
            if not self.version_pattern.match(dep_version):
                logger.error(f"Invalid dependency version format: {dep_version}")
                return False

        return True

    def _validate_previews(self, manifest: Dict[str, Any]) -> bool:
        """Validate previews structure."""
        previews = manifest.get("previews", [])

        if not isinstance(previews, list):
            logger.error("Previews must be a list")
            return False

        for preview in previews:
            if not isinstance(preview, dict):
                logger.error("Each preview must be a dictionary")
                return False

            required_preview_keys = ["filename", "checksum"]
            for key in required_preview_keys:
                if key not in preview:
                    logger.error(f"Preview missing required key: {key}")
                    return False

        return True

    def _validate_checksums(self, manifest: Dict[str, Any]) -> bool:
        """Validate checksums structure."""
        checksums = manifest.get("checksums", {})

        if not isinstance(checksums, dict):
            logger.error("Checksums must be a dictionary")
            return False

        if "overall" not in checksums:
            logger.error("Checksums must include 'overall' checksum")
            return False

        # Validate checksum format (MD5 hex)
        for name, checksum in checksums.items():
            if not isinstance(checksum, str) or len(checksum) != 32 or not all(c in '0123456789abcdef' for c in checksum):
                logger.error(f"Invalid checksum format for {name}: {checksum}")
                return False

        return True

    def validate_pack_file(self, pack_path: Path) -> bool:
        """
        Validate a pack file (ZIP or directory).

        Args:
            pack_path: Path to pack file or directory

        Returns:
            True if valid, False otherwise
        """
        try:
            if pack_path.is_file() and pack_path.suffix == '.zip':
                return self._validate_zip_pack(pack_path)
            elif pack_path.is_dir():
                return self._validate_directory_pack(pack_path)
            else:
                logger.error(f"Invalid pack path: {pack_path}")
                return False
        except Exception as e:
            logger.error(f"Pack file validation failed: {e}")
            return False

    def _validate_zip_pack(self, zip_path: Path) -> bool:
        """Validate a ZIP pack file."""
        import zipfile

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # Check for manifest
                if "manifest.json" not in zf.namelist():
                    logger.error("Pack ZIP missing manifest.json")
                    return False

                # Read and validate manifest
                with zf.open("manifest.json") as f:
                    manifest = json.loads(f.read().decode('utf-8'))

                return self.validate_pack(manifest)
        except Exception as e:
            logger.error(f"ZIP pack validation failed: {e}")
            return False

    def _validate_directory_pack(self, dir_path: Path) -> bool:
        """Validate a directory pack."""
        manifest_path = dir_path / "manifest.json"
        if not manifest_path.exists():
            logger.error(f"Pack directory missing manifest.json: {dir_path}")
            return False

        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            return self.validate_pack(manifest)
        except Exception as e:
            logger.error(f"Directory pack validation failed: {e}")
            return False


# Convenience function
def validate_pack(manifest: Dict[str, Any]) -> bool:
    """
    Convenience function to validate a pack manifest.

    Args:
        manifest: Pack manifest dictionary

    Returns:
        True if valid, False otherwise
    """
    validator = PackValidator()
    return validator.validate_pack(manifest)