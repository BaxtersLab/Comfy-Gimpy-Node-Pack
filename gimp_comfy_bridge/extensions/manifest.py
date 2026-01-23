# gimp_comfy_bridge/extensions/manifest.py

"""
Extension Manifest System

Handles extension metadata, permissions, and validation.
"""

import json
import hashlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
import semver

@dataclass
class ExtensionManifest:
    """Extension manifest data structure."""

    # Basic metadata
    name: str
    version: str
    description: str
    author: str
    author_email: Optional[str] = None

    # Extension details
    extension_id: str = ""
    homepage: Optional[str] = None
    repository: Optional[str] = None
    license: Optional[str] = None
    keywords: List[str] = field(default_factory=list)

    # Dependencies
    dependencies: Dict[str, str] = field(default_factory=dict)  # name: version_range
    peer_dependencies: Dict[str, str] = field(default_factory=dict)

    # Capabilities
    permissions: List[str] = field(default_factory=list)
    ui_panels: List[str] = field(default_factory=list)
    workflows: List[str] = field(default_factory=list)
    asset_types: List[str] = field(default_factory=list)
    template_generators: List[str] = field(default_factory=list)
    copywriting_modules: List[str] = field(default_factory=list)
    brand_kit_tools: List[str] = field(default_factory=list)
    layout_heuristics: List[str] = field(default_factory=list)

    # Entry points
    main_module: str = "main.py"
    entry_points: Dict[str, str] = field(default_factory=dict)

    # Marketplace info
    marketplace_id: Optional[str] = None
    price: Optional[float] = None
    tags: List[str] = field(default_factory=list)

    # Internal fields
    _manifest_path: Optional[Path] = None
    _checksum: Optional[str] = None

    def __post_init__(self):
        """Generate extension ID if not provided."""
        if not self.extension_id:
            self.extension_id = f"{self.author}.{self.name}".lower().replace(" ", "_")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExtensionManifest':
        """Create manifest from dictionary."""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> 'ExtensionManifest':
        """Create manifest from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def from_file(cls, path: Path) -> 'ExtensionManifest':
        """Load manifest from file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        manifest = cls.from_dict(data)
        manifest._manifest_path = path
        manifest._checksum = cls._calculate_checksum(path)

        return manifest

    def to_dict(self) -> Dict[str, Any]:
        """Convert manifest to dictionary."""
        data = {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'author_email': self.author_email,
            'extension_id': self.extension_id,
            'homepage': self.homepage,
            'repository': self.repository,
            'license': self.license,
            'keywords': self.keywords,
            'dependencies': self.dependencies,
            'peer_dependencies': self.peer_dependencies,
            'permissions': self.permissions,
            'ui_panels': self.ui_panels,
            'workflows': self.workflows,
            'asset_types': self.asset_types,
            'template_generators': self.template_generators,
            'copywriting_modules': self.copywriting_modules,
            'brand_kit_tools': self.brand_kit_tools,
            'layout_heuristics': self.layout_heuristics,
            'main_module': self.main_module,
            'entry_points': self.entry_points,
            'marketplace_id': self.marketplace_id,
            'price': self.price,
            'tags': self.tags
        }
        # Remove None values
        return {k: v for k, v in data.items() if v is not None}

    def to_json(self, indent: int = 2) -> str:
        """Convert manifest to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, path: Path) -> None:
        """Save manifest to file."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)

    def validate(self) -> List[str]:
        """Validate manifest data."""
        errors = []

        # Required fields
        required_fields = ['name', 'version', 'description', 'author']
        for field in required_fields:
            if not getattr(self, field):
                errors.append(f"Missing required field: {field}")

        # Version validation
        try:
            semver.VersionInfo.parse(self.version)
        except ValueError:
            errors.append(f"Invalid version format: {self.version}")

        # Extension ID validation
        if not self.extension_id.replace('.', '').replace('_', '').replace('-', '').isalnum():
            errors.append(f"Invalid extension ID: {self.extension_id}")

        # Permission validation
        valid_permissions = [
            'file_system', 'network', 'ui_injection', 'asset_access',
            'workflow_execution', 'template_generation', 'brand_kit_access',
            'copywriting_access', 'layout_optimization', 'marketplace_access'
        ]
        for perm in self.permissions:
            if perm not in valid_permissions:
                errors.append(f"Unknown permission: {perm}")

        return errors

    def has_permission(self, permission: str) -> bool:
        """Check if extension has a specific permission."""
        return permission in self.permissions

    def get_capabilities(self) -> Dict[str, List[str]]:
        """Get all extension capabilities."""
        return {
            'ui_panels': self.ui_panels,
            'workflows': self.workflows,
            'asset_types': self.asset_types,
            'template_generators': self.template_generators,
            'copywriting_modules': self.copywriting_modules,
            'brand_kit_tools': self.brand_kit_tools,
            'layout_heuristics': self.layout_heuristics
        }

    @staticmethod
    def _calculate_checksum(path: Path) -> str:
        """Calculate SHA256 checksum of manifest file."""
        sha256 = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def is_modified(self) -> bool:
        """Check if manifest file has been modified."""
        if not self._manifest_path:
            return False
        return self._calculate_checksum(self._manifest_path) != self._checksum