"""
Template registry for Comfy Gimpy Studio.

Manages template discovery, caching, and metadata indexing.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

from .metadata import TemplateMetadata, load_metadata

logger = logging.getLogger(__name__)


@dataclass
class TemplateInfo:
    """
    Basic information about a template.
    """
    category: str
    name: str
    path: Path
    metadata: Optional[TemplateMetadata] = None


@dataclass
class TemplateCategory:
    """
    Information about a template category.
    """
    name: str
    display_name: str
    description: str
    template_count: int = 0


class TemplateRegistry:
    """
    Registry for managing template discovery and metadata.
    """

    def __init__(self, templates_base_path: Path):
        """
        Initialize the template registry.

        Args:
            templates_base_path: Base path containing template categories
        """
        self.templates_base_path = templates_base_path
        self._templates: Dict[str, Dict[str, TemplateInfo]] = {}  # category -> name -> info
        self._categories: Dict[str, TemplateCategory] = {}
        self._scanned = False

    def scan_templates(self) -> None:
        """
        Scan the templates directory and build the registry.
        """
        logger.info(f"Scanning templates in: {self.templates_base_path}")

        if not self.templates_base_path.exists():
            logger.warning(f"Templates directory does not exist: {self.templates_base_path}")
            self._scanned = True
            return

        # Clear existing data
        self._templates.clear()
        self._categories.clear()

        # Scan each category directory
        for category_dir in self.templates_base_path.iterdir():
            if not category_dir.is_dir() or category_dir.name.startswith('.'):
                continue

            category_name = category_dir.name
            logger.debug(f"Scanning category: {category_name}")

            # Initialize category
            self._categories[category_name] = TemplateCategory(
                name=category_name,
                display_name=self._format_category_name(category_name),
                description=f"Templates for {self._format_category_name(category_name).lower()}",
                template_count=0
            )

            # Scan templates in this category
            category_templates = {}
            for template_dir in category_dir.iterdir():
                if not template_dir.is_dir() or template_dir.name.startswith('.'):
                    continue

                template_name = template_dir.name
                logger.debug(f"Found template: {category_name}/{template_name}")

                # Create template info
                template_info = TemplateInfo(
                    category=category_name,
                    name=template_name,
                    path=template_dir
                )

                # Try to load metadata
                metadata_path = template_dir / "metadata.json"
                if metadata_path.exists():
                    try:
                        template_info.metadata = load_metadata(metadata_path)
                    except Exception as e:
                        logger.warning(f"Failed to load metadata for {category_name}/{template_name}: {e}")

                category_templates[template_name] = template_info

            if category_templates:
                self._templates[category_name] = category_templates
                self._categories[category_name].template_count = len(category_templates)

        self._scanned = True
        logger.info(f"Template scan complete. Found {len(self._categories)} categories with {sum(len(temps) for temps in self._templates.values())} templates")

    def _ensure_scanned(self) -> None:
        """Ensure templates have been scanned."""
        if not self._scanned:
            self.scan_templates()

    def _format_category_name(self, category_name: str) -> str:
        """Format category name for display."""
        return category_name.replace('_', ' ').title()

    def list_categories(self) -> List[TemplateCategory]:
        """
        Get list of all template categories.

        Returns:
            List of TemplateCategory objects
        """
        self._ensure_scanned()
        return list(self._categories.values())

    def list_templates(self, category: Optional[str] = None) -> List[TemplateInfo]:
        """
        Get list of templates, optionally filtered by category.

        Args:
            category: Category name to filter by, or None for all

        Returns:
            List of TemplateInfo objects
        """
        self._ensure_scanned()

        if category:
            if category not in self._templates:
                return []
            return list(self._templates[category].values())
        else:
            # Return all templates
            all_templates = []
            for category_templates in self._templates.values():
                all_templates.extend(category_templates.values())
            return all_templates

    def get_template_metadata(self, category: str, name: str) -> Optional[TemplateMetadata]:
        """
        Get metadata for a specific template.

        Args:
            category: Template category
            name: Template name

        Returns:
            TemplateMetadata object or None if not found
        """
        self._ensure_scanned()

        if category not in self._templates or name not in self._templates[category]:
            return None

        template_info = self._templates[category][name]

        # Return cached metadata if available
        if template_info.metadata:
            return template_info.metadata

        # Try to load metadata
        metadata_path = template_info.path / "metadata.json"
        if metadata_path.exists():
            try:
                template_info.metadata = load_metadata(metadata_path)
                return template_info.metadata
            except Exception as e:
                logger.error(f"Failed to load metadata for {category}/{name}: {e}")

        return None

    def get_template_paths(self, category: str, name: str) -> Optional[Dict[str, Path]]:
        """
        Get paths for all template files.

        Args:
            category: Template category
            name: Template name

        Returns:
            Dictionary mapping file types to paths, or None if template not found
        """
        self._ensure_scanned()

        if category not in self._templates or name not in self._templates[category]:
            return None

        template_path = self._templates[category][name].path

        paths = {
            'root': template_path,
            'metadata': template_path / "metadata.json",
            'layout': template_path / "layout.xcf",
            'workflow': template_path / "workflow.json",
            'preview': template_path / "preview.png",
            'styles': template_path / "styles"
        }

        return paths

    def get_category_info(self, category: str) -> Optional[TemplateCategory]:
        """
        Get information about a specific category.

        Args:
            category: Category name

        Returns:
            TemplateCategory object or None if not found
        """
        self._ensure_scanned()
        return self._categories.get(category)

    def search_templates(self, query: str, category: Optional[str] = None) -> List[TemplateInfo]:
        """
        Search templates by name, description, or tags.

        Args:
            query: Search query (case-insensitive)
            category: Optional category filter

        Returns:
            List of matching TemplateInfo objects
        """
        self._ensure_scanned()

        query_lower = query.lower()
        matches = []

        templates_to_search = self.list_templates(category)

        for template_info in templates_to_search:
            if not template_info.metadata:
                continue

            # Search in name, description, and tags
            searchable_text = (
                template_info.metadata.name + ' ' +
                template_info.metadata.description + ' ' +
                ' '.join(template_info.metadata.tags)
            ).lower()

            if query_lower in searchable_text:
                matches.append(template_info)

        return matches

    def invalidate_cache(self) -> None:
        """
        Invalidate the template cache, forcing a rescan on next access.
        """
        self._scanned = False
        logger.info("Template cache invalidated")

    def get_template_count(self) -> int:
        """
        Get total number of templates.

        Returns:
            Total template count
        """
        self._ensure_scanned()
        return sum(len(templates) for templates in self._templates.values())

    def get_category_count(self) -> int:
        """
        Get number of categories.

        Returns:
            Category count
        """
        self._ensure_scanned()
        return len(self._categories)