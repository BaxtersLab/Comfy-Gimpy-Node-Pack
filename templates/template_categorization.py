#!/usr/bin/env python3
"""
Template Categorization and Tagging System for Comfy Gimpy Studio

Provides advanced categorization, tagging, and search capabilities for templates.
Enables users to discover and filter templates based on various criteria.
"""

import json
import pathlib
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict
import re
import sys


@dataclass
class TemplateCategory:
    """Represents a template category with metadata."""
    name: str
    display_name: str
    description: str
    icon: str = ""
    template_count: int = 0
    subcategories: List[str] = field(default_factory=list)


@dataclass
class TemplateTag:
    """Represents a tag with usage statistics."""
    name: str
    category: str  # e.g., "style", "content", "use_case"
    display_name: str
    description: str = ""
    usage_count: int = 0
    related_tags: List[str] = field(default_factory=list)


@dataclass
class TemplateMetadata:
    """Metadata for a template used in categorization."""
    template_id: str
    name: str
    category: str
    tags: List[str]
    dimensions: Tuple[int, int, int]  # width, height, dpi
    author: str
    version: str
    description: str
    placeholders_count: int
    layers_count: int
    workflow_name: str
    style_requirements: Dict[str, Any]


class TemplateCategorizer:
    """Manages template categorization and tagging."""

    def __init__(self, templates_dir: pathlib.Path):
        """
        Initialize the categorizer.

        Args:
            templates_dir: Directory containing templates
        """
        self.templates_dir = templates_dir
        self._categories: Dict[str, TemplateCategory] = {}
        self._tags: Dict[str, TemplateTag] = {}
        self._template_metadata: Dict[str, TemplateMetadata] = {}
        self._tag_index: Dict[str, Set[str]] = defaultdict(set)  # tag -> template_ids
        self._category_index: Dict[str, Set[str]] = defaultdict(set)  # category -> template_ids

        # Initialize default categories
        self._initialize_default_categories()

        # Initialize default tags
        self._initialize_default_tags()

    def _initialize_default_categories(self):
        """Initialize the default template categories."""
        categories_data = [
            {
                "name": "posters",
                "display_name": "Posters",
                "description": "Event posters, promotional posters, and artistic displays",
                "icon": "📄",
                "subcategories": ["event", "promotional", "artistic", "informational"]
            },
            {
                "name": "brochures",
                "display_name": "Brochures",
                "description": "Tri-fold, bi-fold brochures and flyers",
                "icon": "📑",
                "subcategories": ["trifold", "bifold", "flyer", "newsletter"]
            },
            {
                "name": "business_cards",
                "display_name": "Business Cards",
                "description": "Professional and creative business card designs",
                "icon": "💼",
                "subcategories": ["standard", "creative", "digital"]
            },
            {
                "name": "websites",
                "display_name": "Website Templates",
                "description": "Website mockups and landing page designs",
                "icon": "🌐",
                "subcategories": ["landing_page", "portfolio", "blog", "ecommerce"]
            },
            {
                "name": "social_media",
                "display_name": "Social Media",
                "description": "Social media post templates and graphics",
                "icon": "📱",
                "subcategories": ["instagram", "facebook", "twitter", "linkedin"]
            }
        ]

        for cat_data in categories_data:
            category = TemplateCategory(**cat_data)
            self._categories[category.name] = category

    def _initialize_default_tags(self):
        """Initialize default tags organized by category."""
        tags_data = [
            # Style tags
            {"name": "modern", "category": "style", "display_name": "Modern", "description": "Contemporary and sleek designs"},
            {"name": "minimalist", "category": "style", "display_name": "Minimalist", "description": "Clean and simple layouts"},
            {"name": "vintage", "category": "style", "display_name": "Vintage", "description": "Retro and classic aesthetics"},
            {"name": "corporate", "category": "style", "display_name": "Corporate", "description": "Professional business styling"},
            {"name": "creative", "category": "style", "display_name": "Creative", "description": "Artistic and imaginative designs"},

            # Content tags
            {"name": "text-heavy", "category": "content", "display_name": "Text Heavy", "description": "Templates with significant text content"},
            {"name": "image-focused", "category": "content", "display_name": "Image Focused", "description": "Templates centered around images"},
            {"name": "logo-centric", "category": "content", "display_name": "Logo Centric", "description": "Templates featuring prominent logos"},

            # Use case tags
            {"name": "business", "category": "use_case", "display_name": "Business", "description": "Business and professional use"},
            {"name": "event", "category": "use_case", "display_name": "Event", "description": "Event promotion and announcements"},
            {"name": "promotion", "category": "use_case", "display_name": "Promotion", "description": "Marketing and promotional materials"},
            {"name": "personal", "category": "use_case", "display_name": "Personal", "description": "Personal and individual use"},
            {"name": "education", "category": "use_case", "display_name": "Education", "description": "Educational and training materials"},
        ]

        for tag_data in tags_data:
            tag = TemplateTag(**tag_data)
            self._tags[tag.name] = tag

    def load_template_metadata(self, template_id: str) -> Optional[TemplateMetadata]:
        """
        Load metadata for a specific template.

        Args:
            template_id: Template identifier

        Returns:
            TemplateMetadata object or None if not found
        """
        if template_id in self._template_metadata:
            return self._template_metadata[template_id]

        try:
            # Parse template path
            category, template_name = template_id.split('/', 1)
            template_path = self.templates_dir / category / f"{template_name}.json"

            if not template_path.exists():
                return None

            # Load template data
            with open(template_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Extract metadata
            dimensions = data.get('dimensions', {})
            workflow_bindings = data.get('workflow_bindings', {})

            metadata = TemplateMetadata(
                template_id=template_id,
                name=data.get('name', ''),
                category=data.get('category', ''),
                tags=data.get('tags', []),
                dimensions=(dimensions.get('width', 0), dimensions.get('height', 0), dimensions.get('dpi', 300)),
                author=data.get('author', ''),
                version=data.get('version', '1.0.0'),
                description=data.get('description', ''),
                placeholders_count=len(data.get('placeholders', [])),
                layers_count=len(data.get('layers', [])),
                workflow_name=workflow_bindings.get('default_workflow', ''),
                style_requirements=data.get('style_requirements', {})
            )

            self._template_metadata[template_id] = metadata

            # Update indexes
            self._category_index[metadata.category].add(template_id)
            for tag in metadata.tags:
                self._tag_index[tag].add(template_id)

            # Update category count
            if metadata.category in self._categories:
                self._categories[metadata.category].template_count += 1

            # Update tag usage counts
            for tag_name in metadata.tags:
                if tag_name in self._tags:
                    self._tags[tag_name].usage_count += 1

            return metadata

        except Exception as e:
            print(f"Failed to load metadata for {template_id}: {e}")
            return None

    def load_all_templates(self) -> List[str]:
        """
        Load metadata for all available templates.

        Returns:
            List of template IDs that were successfully loaded
        """
        template_ids = []

        # Discover all templates
        for category_dir in self.templates_dir.iterdir():
            if category_dir.is_dir() and not category_dir.name.startswith('.'):
                for template_file in category_dir.glob('*.json'):
                    template_id = f"{category_dir.name}/{template_file.stem}"
                    if self.load_template_metadata(template_id):
                        template_ids.append(template_id)

        return template_ids

    def get_categories(self) -> Dict[str, TemplateCategory]:
        """Get all available categories."""
        return self._categories.copy()

    def get_tags(self, category: Optional[str] = None) -> Dict[str, TemplateTag]:
        """
        Get tags, optionally filtered by category.

        Args:
            category: Tag category filter (e.g., "style", "content")

        Returns:
            Dictionary of tags
        """
        if category:
            return {name: tag for name, tag in self._tags.items() if tag.category == category}
        return self._tags.copy()

    def search_templates(self, query: str = "", category: Optional[str] = None,
                        tags: Optional[List[str]] = None,
                        author: Optional[str] = None,
                        min_placeholders: Optional[int] = None,
                        max_dimensions: Optional[Tuple[int, int]] = None) -> List[str]:
        """
        Search templates based on various criteria.

        Args:
            query: Text search in name and description
            category: Category filter
            tags: List of required tags
            author: Author filter
            min_placeholders: Minimum number of placeholders
            max_dimensions: Maximum dimensions (width, height)

        Returns:
            List of matching template IDs
        """
        # Load all templates if none are loaded yet
        if not self._template_metadata:
            self.load_all_templates()

        candidates = set(self._template_metadata.keys())

        # Apply category filter
        if category:
            if category in self._category_index:
                candidates &= self._category_index[category]
            else:
                return []  # No templates in this category

        # Apply tag filters
        if tags:
            for tag in tags:
                if tag in self._tag_index:
                    candidates &= self._tag_index[tag]
                else:
                    return []  # Tag doesn't exist

        # Apply text search
        if query:
            query_lower = query.lower()
            matching = set()
            for template_id in candidates:
                metadata = self._template_metadata.get(template_id)
                if metadata:
                    searchable = (metadata.name + ' ' + metadata.description).lower()
                    if query_lower in searchable:
                        matching.add(template_id)
            candidates = matching

        # Apply author filter
        if author:
            author_lower = author.lower()
            matching = set()
            for template_id in candidates:
                metadata = self._template_metadata.get(template_id)
                if metadata and author_lower in metadata.author.lower():
                    matching.add(template_id)
            candidates = matching

        # Apply placeholder count filter
        if min_placeholders is not None:
            matching = set()
            for template_id in candidates:
                metadata = self._template_metadata.get(template_id)
                if metadata and metadata.placeholders_count >= min_placeholders:
                    matching.add(template_id)
            candidates = matching

        # Apply dimension filter
        if max_dimensions:
            max_w, max_h = max_dimensions
            matching = set()
            for template_id in candidates:
                metadata = self._template_metadata.get(template_id)
                if metadata:
                    w, h, _ = metadata.dimensions
                    if w <= max_w and h <= max_h:
                        matching.add(template_id)
            candidates = matching

        return sorted(list(candidates))

    def get_related_templates(self, template_id: str, limit: int = 5) -> List[Tuple[str, float]]:
        """
        Find templates related to the given template.

        Args:
            template_id: Base template ID
            limit: Maximum number of related templates to return

        Returns:
            List of (template_id, similarity_score) tuples
        """
        base_metadata = self._template_metadata.get(template_id)
        if not base_metadata:
            return []

        related = []

        for other_id, other_metadata in self._template_metadata.items():
            if other_id == template_id:
                continue

            score = 0.0

            # Category match
            if base_metadata.category == other_metadata.category:
                score += 0.4

            # Tag overlap
            base_tags = set(base_metadata.tags)
            other_tags = set(other_metadata.tags)
            if base_tags and other_tags:
                tag_overlap = len(base_tags & other_tags) / len(base_tags | other_tags)
                score += tag_overlap * 0.4

            # Author match
            if base_metadata.author == other_metadata.author:
                score += 0.1

            # Style requirements similarity (simplified)
            base_styles = set(base_metadata.style_requirements.get('recommended_styles', []))
            other_styles = set(other_metadata.style_requirements.get('recommended_styles', []))
            if base_styles and other_styles:
                style_overlap = len(base_styles & other_styles) / len(base_styles | other_styles)
                score += style_overlap * 0.1

            if score > 0:
                related.append((other_id, score))

        # Sort by score and return top matches
        related.sort(key=lambda x: x[1], reverse=True)
        return related[:limit]

    def get_category_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for each category."""
        stats = {}

        for category_name, category in self._categories.items():
            template_ids = list(self._category_index.get(category_name, set()))
            templates = [self._template_metadata[tid] for tid in template_ids if tid in self._template_metadata]

            if templates:
                avg_placeholders = sum(t.placeholders_count for t in templates) / len(templates)
                avg_layers = sum(t.layers_count for t in templates) / len(templates)

                # Collect all tags in this category
                all_tags = set()
                for t in templates:
                    all_tags.update(t.tags)

                stats[category_name] = {
                    "template_count": len(templates),
                    "avg_placeholders": round(avg_placeholders, 1),
                    "avg_layers": round(avg_layers, 1),
                    "unique_tags": len(all_tags),
                    "popular_tags": sorted(all_tags, key=lambda t: self._tags.get(t, TemplateTag(t, "", "")).usage_count, reverse=True)[:5]
                }
            else:
                stats[category_name] = {
                    "template_count": 0,
                    "avg_placeholders": 0,
                    "avg_layers": 0,
                    "unique_tags": 0,
                    "popular_tags": []
                }

        return stats

    def suggest_tags(self, template_description: str, limit: int = 5) -> List[Tuple[str, float]]:
        """
        Suggest relevant tags based on template description.

        Args:
            template_description: Description text to analyze
            limit: Maximum number of suggestions

        Returns:
            List of (tag_name, confidence_score) tuples
        """
        description_lower = template_description.lower()
        suggestions = []

        for tag_name, tag in self._tags.items():
            score = 0.0

            # Check if tag name appears in description
            if tag_name in description_lower:
                score += 0.5

            # Check display name
            if tag.display_name.lower() in description_lower:
                score += 0.3

            # Check description
            if tag.description and any(word in description_lower for word in tag.description.lower().split()):
                score += 0.2

            if score > 0:
                suggestions.append((tag_name, score))

        suggestions.sort(key=lambda x: x[1], reverse=True)
        return suggestions[:limit]


def main():
    """Command-line interface for template categorization."""
    if len(sys.argv) < 2:
        print("Usage: python template_categorization.py <templates_dir> [command] [args...]")
        print("Commands:")
        print("  load-all                    - Load all templates")
        print("  categories                  - List all categories")
        print("  tags [category]             - List tags (optionally by category)")
        print("  search <query>              - Search templates")
        print("  stats                       - Show category statistics")
        print("  related <template_id>       - Find related templates")
        print("  suggest-tags <description>  - Suggest tags for description")
        sys.exit(1)

    templates_dir = pathlib.Path(sys.argv[1])
    categorizer = TemplateCategorizer(templates_dir)

    command = sys.argv[2] if len(sys.argv) > 2 else 'load-all'

    if command == 'load-all':
        templates = categorizer.load_all_templates()
        print(f"Loaded {len(templates)} templates")

    elif command == 'categories':
        categories = categorizer.get_categories()
        print("Available categories:")
        for name, category in categories.items():
            print(f"  {category.icon} {category.display_name} ({category.template_count} templates)")
            print(f"    {category.description}")

    elif command == 'tags':
        category_filter = sys.argv[3] if len(sys.argv) > 3 else None
        tags = categorizer.get_tags(category_filter)
        category_desc = f" in category '{category_filter}'" if category_filter else ""
        print(f"Available tags{category_desc}:")
        for name, tag in tags.items():
            print(f"  {name}: {tag.display_name} ({tag.usage_count} uses)")
            if tag.description:
                print(f"    {tag.description}")

    elif command == 'search' and len(sys.argv) > 3:
        query = sys.argv[3]
        results = categorizer.search_templates(query=query)
        print(f"Search results for '{query}':")
        for template_id in results:
            metadata = categorizer._template_metadata.get(template_id)
            if metadata:
                print(f"  - {template_id}: {metadata.name}")

    elif command == 'stats':
        stats = categorizer.get_category_stats()
        print("Category Statistics:")
        for category, stat in stats.items():
            print(f"\n{category}:")
            print(f"  Templates: {stat['template_count']}")
            print(f"  Avg placeholders: {stat['avg_placeholders']}")
            print(f"  Avg layers: {stat['avg_layers']}")
            print(f"  Unique tags: {stat['unique_tags']}")
            if stat['popular_tags']:
                print(f"  Popular tags: {', '.join(stat['popular_tags'][:3])}")

    elif command == 'related' and len(sys.argv) > 3:
        template_id = sys.argv[3]
        related = categorizer.get_related_templates(template_id)
        print(f"Templates related to {template_id}:")
        for rel_id, score in related:
            metadata = categorizer._template_metadata.get(rel_id)
            if metadata:
                print(".2f")

    elif command == 'suggest-tags' and len(sys.argv) > 3:
        description = ' '.join(sys.argv[3:])
        suggestions = categorizer.suggest_tags(description)
        print(f"Tag suggestions for: {description}")
        for tag_name, score in suggestions:
            tag = categorizer._tags.get(tag_name)
            if tag:
                print(".2f")

    else:
        print("Invalid command or arguments")


if __name__ == '__main__':
    main()