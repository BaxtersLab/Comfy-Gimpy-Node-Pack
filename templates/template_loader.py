#!/usr/bin/env python3
"""
Template Loader for Comfy Gimpy Studio

Loads template metadata and prepares templates for use in GIMP.
Handles template discovery, validation, and integration with GIMP layers.
"""

import json
import pathlib
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import sys
import os


@dataclass
class TemplateLayer:
    """Represents a layer in a template."""
    name: str
    layer_type: str
    visible: bool
    opacity: float
    blend_mode: str
    position: Tuple[int, int, int, int]  # x, y, width, height


@dataclass
class TemplatePlaceholder:
    """Represents a content placeholder in a template."""
    id: str
    placeholder_type: str
    layer_name: str
    label: str
    default_content: str
    constraints: Dict[str, Any]


@dataclass
class Template:
    """Complete template definition."""
    name: str
    description: str
    category: str
    version: str
    author: str
    tags: List[str]
    dimensions: Tuple[int, int, int]  # width, height, dpi
    background_color: str
    layers: List[TemplateLayer]
    placeholders: List[TemplatePlaceholder]
    workflow_bindings: Dict[str, Any]
    style_requirements: Dict[str, Any]
    dependencies: Dict[str, List[str]]
    metadata: Dict[str, Any]

    @property
    def aspect_ratio(self) -> float:
        """Calculate aspect ratio (width/height)."""
        return self.dimensions[0] / self.dimensions[1] if self.dimensions[1] > 0 else 1.0


class TemplateLoader:
    """Loads and manages templates for Comfy Gimpy Studio."""

    def __init__(self, templates_dir: pathlib.Path, validator=None):
        """
        Initialize the template loader.

        Args:
            templates_dir: Root directory containing templates
            validator: Optional template validator instance
        """
        self.templates_dir = templates_dir
        self.validator = validator
        self._template_cache: Dict[str, Template] = {}
        self._loaded_templates: Dict[str, Dict] = {}

    def discover_templates(self) -> List[str]:
        """
        Discover all available templates.

        Returns:
            List of template identifiers (category/template_name)
        """
        templates = []

        for category_dir in self.templates_dir.iterdir():
            if category_dir.is_dir() and not category_dir.name.startswith('.'):
                for template_file in category_dir.glob('*.json'):
                    template_id = f"{category_dir.name}/{template_file.stem}"
                    templates.append(template_id)

        return sorted(templates)

    def load_template(self, template_id: str, validate: bool = True) -> Optional[Template]:
        """
        Load a template by its identifier.

        Args:
            template_id: Template identifier (category/template_name)
            validate: Whether to validate the template

        Returns:
            Template object or None if loading failed
        """
        if template_id in self._template_cache:
            return self._template_cache[template_id]

        try:
            # Parse template ID
            category, template_name = template_id.split('/', 1)
            template_path = self.templates_dir / category / f"{template_name}.json"

            if not template_path.exists():
                print(f"Template file not found: {template_path}")
                return None

            # Load and parse JSON
            with open(template_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validate if requested
            if validate and self.validator:
                is_valid, errors = self.validator.validate_template(template_path)
                if not is_valid:
                    print(f"Template validation failed for {template_id}:")
                    for error in errors:
                        print(f"  - {error}")
                    return None

            # Convert to Template object
            template = self._parse_template_data(data, template_id)
            self._template_cache[template_id] = template

            return template

        except Exception as e:
            print(f"Failed to load template {template_id}: {e}")
            return None

    def _parse_template_data(self, data: Dict, template_id: str) -> Template:
        """Parse raw template data into a Template object."""
        # Parse dimensions
        dims = data.get('dimensions', {})
        dimensions = (
            dims.get('width', 1000),
            dims.get('height', 1000),
            dims.get('dpi', 300)
        )

        # Parse layers
        layers = []
        for layer_data in data.get('layers', []):
            pos = layer_data.get('position', {})
            layer = TemplateLayer(
                name=layer_data.get('name', ''),
                layer_type=layer_data.get('type', 'background'),
                visible=layer_data.get('visible', True),
                opacity=layer_data.get('opacity', 100) / 100.0,
                blend_mode=layer_data.get('blend_mode', 'NORMAL'),
                position=(
                    pos.get('x', 0),
                    pos.get('y', 0),
                    pos.get('width', 100),
                    pos.get('height', 100)
                )
            )
            layers.append(layer)

        # Parse placeholders
        placeholders = []
        for ph_data in data.get('placeholders', []):
            placeholder = TemplatePlaceholder(
                id=ph_data.get('id', ''),
                placeholder_type=ph_data.get('type', 'text'),
                layer_name=ph_data.get('layer_name', ''),
                label=ph_data.get('label', ''),
                default_content=ph_data.get('default_content', ''),
                constraints=ph_data.get('constraints', {})
            )
            placeholders.append(placeholder)

        # Create template object
        template = Template(
            name=data.get('name', ''),
            description=data.get('description', ''),
            category=data.get('category', ''),
            version=data.get('version', '1.0.0'),
            author=data.get('author', ''),
            tags=data.get('tags', []),
            dimensions=dimensions,
            background_color=data.get('background_color', '#ffffff'),
            layers=layers,
            placeholders=placeholders,
            workflow_bindings=data.get('workflow_bindings', {}),
            style_requirements=data.get('style_requirements', {}),
            dependencies=data.get('dependencies', {}),
            metadata=data.get('metadata', {})
        )

        return template

    def get_template_preview_path(self, template_id: str) -> Optional[pathlib.Path]:
        """
        Get the path to a template's preview image.

        Args:
            template_id: Template identifier

        Returns:
            Path to preview image or None if not found
        """
        try:
            category, template_name = template_id.split('/', 1)
            preview_path = self.templates_dir / category / f"{template_name}.png"
            return preview_path if preview_path.exists() else None
        except:
            return None

    def get_templates_by_category(self, category: str) -> List[str]:
        """
        Get all templates in a specific category.

        Args:
            category: Category name

        Returns:
            List of template identifiers in that category
        """
        category_dir = self.templates_dir / category
        if not category_dir.exists():
            return []

        templates = []
        for template_file in category_dir.glob('*.json'):
            templates.append(f"{category}/{template_file.stem}")

        return sorted(templates)

    def search_templates(self, query: str, category: Optional[str] = None) -> List[str]:
        """
        Search templates by name, description, or tags.

        Args:
            query: Search query (case-insensitive)
            category: Optional category filter

        Returns:
            List of matching template identifiers
        """
        query_lower = query.lower()
        matches = []

        search_templates = self.get_templates_by_category(category) if category else self.discover_templates()

        for template_id in search_templates:
            template = self.load_template(template_id, validate=False)
            if template:
                # Search in name, description, and tags
                searchable_text = (
                    template.name + ' ' +
                    template.description + ' ' +
                    ' '.join(template.tags)
                ).lower()

                if query_lower in searchable_text:
                    matches.append(template_id)

        return matches

    def validate_template_dependencies(self, template: Template) -> Tuple[bool, List[str]]:
        """
        Check if a template's dependencies are available.

        Args:
            template: Template to check

        Returns:
            Tuple of (all_available, list_of_missing_dependencies)
        """
        missing = []

        # Check workflows
        required_workflows = template.dependencies.get('workflows', [])
        # In a real implementation, this would check against available ComfyUI workflows
        # For now, we'll assume they're available

        # Check models
        required_models = template.dependencies.get('models', [])
        # Would check against available models

        # Check fonts
        required_fonts = template.dependencies.get('fonts', [])
        # Would check against available fonts

        return len(missing) == 0, missing

    def prepare_template_for_gimp(self, template: Template) -> Dict[str, Any]:
        """
        Prepare template data for GIMP integration.

        Args:
            template: Template to prepare

        Returns:
            Dictionary with GIMP-ready data
        """
        return {
            'name': template.name,
            'dimensions': template.dimensions,
            'background_color': template.background_color,
            'layers': [
                {
                    'name': layer.name,
                    'type': layer.layer_type,
                    'visible': layer.visible,
                    'opacity': layer.opacity,
                    'blend_mode': layer.blend_mode,
                    'bounds': layer.position
                }
                for layer in template.layers
            ],
            'placeholders': [
                {
                    'id': ph.id,
                    'type': ph.placeholder_type,
                    'layer': ph.layer_name,
                    'label': ph.label,
                    'default': ph.default_content,
                    'constraints': ph.constraints
                }
                for ph in template.placeholders
            ],
            'workflow': template.workflow_bindings.get('default_workflow'),
            'parameter_mappings': template.workflow_bindings.get('parameter_mappings', {})
        }


def main():
    """Command-line interface for template loading."""
    if len(sys.argv) < 2:
        print("Usage: python template_loader.py <templates_dir> [command] [args...]")
        print("Commands:")
        print("  list                    - List all templates")
        print("  load <template_id>      - Load and display template info")
        print("  search <query>          - Search templates")
        print("  category <category>     - List templates in category")
        sys.exit(1)

    templates_dir = pathlib.Path(sys.argv[1])
    loader = TemplateLoader(templates_dir)

    command = sys.argv[2] if len(sys.argv) > 2 else 'list'

    if command == 'list':
        templates = loader.discover_templates()
        print(f"Found {len(templates)} templates:")
        for template_id in templates:
            print(f"  - {template_id}")

    elif command == 'load' and len(sys.argv) > 3:
        template_id = sys.argv[3]
        template = loader.load_template(template_id)

        if template:
            print(f"Template: {template.name}")
            print(f"Description: {template.description}")
            print(f"Category: {template.category}")
            print(f"Version: {template.version}")
            print(f"Author: {template.author}")
            print(f"Dimensions: {template.dimensions[0]}x{template.dimensions[1]} @ {template.dimensions[2]} DPI")
            print(f"Layers: {len(template.layers)}")
            print(f"Placeholders: {len(template.placeholders)}")
            print(f"Tags: {', '.join(template.tags)}")

            preview_path = loader.get_template_preview_path(template_id)
            if preview_path:
                print(f"Preview: {preview_path}")
        else:
            print(f"Failed to load template: {template_id}")
            sys.exit(1)

    elif command == 'search' and len(sys.argv) > 3:
        query = sys.argv[3]
        results = loader.search_templates(query)
        print(f"Search results for '{query}':")
        for template_id in results:
            print(f"  - {template_id}")

    elif command == 'category' and len(sys.argv) > 3:
        category = sys.argv[3]
        templates = loader.get_templates_by_category(category)
        print(f"Templates in category '{category}':")
        for template_id in templates:
            print(f"  - {template_id}")

    else:
        print("Invalid command or arguments")
        sys.exit(1)


if __name__ == '__main__':
    main()