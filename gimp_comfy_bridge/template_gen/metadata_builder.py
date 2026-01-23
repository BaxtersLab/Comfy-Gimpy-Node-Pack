"""
Metadata Builder for Comfy Gimpy Studio (Phase 12)

Automatically generates template metadata including names, descriptions,
tags, recommended styles, and workflow requirements.
"""

import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import re

from ..shared.types import TemplateCategory

logger = logging.getLogger(__name__)


@dataclass
class TemplateMetadata:
    """Template metadata structure."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    category: str = ""
    tags: List[str] = field(default_factory=list)
    recommended_styles: List[str] = field(default_factory=list)
    workflow_requirements: Dict[str, Any] = field(default_factory=dict)
    dimensions: tuple[int, int] = (1920, 1080)
    complexity: str = "medium"
    quality: str = "standard"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = "1.0"
    author: str = "Comfy Gimpy Studio"
    license: str = "MIT"

    # AI generation metadata
    generation_seed: Optional[int] = None
    base_style: Optional[str] = None
    brand_kit: Optional[str] = None
    layout_elements: int = 0
    has_workflow: bool = True
    has_previews: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "tags": self.tags,
            "recommended_styles": self.recommended_styles,
            "workflow_requirements": self.workflow_requirements,
            "dimensions": list(self.dimensions),
            "complexity": self.complexity,
            "quality": self.quality,
            "created_at": self.created_at,
            "version": self.version,
            "author": self.author,
            "license": self.license,
            "generation_seed": self.generation_seed,
            "base_style": self.base_style,
            "brand_kit": self.brand_kit,
            "layout_elements": self.layout_elements,
            "has_workflow": self.has_workflow,
            "has_previews": self.has_previews
        }


class MetadataBuilder:
    """Builds template metadata automatically."""

    def __init__(self):
        """Initialize the metadata builder."""
        self._load_name_templates()
        self._load_tag_mappings()
        self._load_style_mappings()

        logger.info("Metadata builder initialized")

    def _load_name_templates(self):
        """Load name generation templates."""
        self.name_templates = {
            TemplateCategory.POSTER: [
                "Dynamic {style} Poster Design",
                "Eye-catching {category} Template",
                "Professional {style} {category}",
                "Creative {category} Layout",
                "{style} Design {category}"
            ],
            TemplateCategory.BROCHURE: [
                "Elegant {style} Brochure",
                "Professional {category} Template",
                "Informative {style} {category}",
                "Corporate {category} Design",
                "{style} Business {category}"
            ],
            TemplateCategory.WEBSITE: [
                "Modern {style} Website Mockup",
                "Responsive {category} Template",
                "Clean {style} {category} Design",
                "Professional Web {category}",
                "{style} Digital {category}"
            ],
            TemplateCategory.BUSINESS_CARD: [
                "Professional {style} Business Card",
                "Clean {category} Template",
                "Corporate {style} {category}",
                "Minimalist {category} Design",
                "{style} Contact {category}"
            ],
            TemplateCategory.FLYER: [
                "Vibrant {style} Flyer",
                "Attention-grabbing {category}",
                "Colorful {style} {category}",
                "Marketing {category} Template",
                "{style} Promotional {category}"
            ],
            TemplateCategory.SOCIAL_MEDIA: [
                "Engaging {style} Social Post",
                "Viral {category} Template",
                "Trendy {style} {category}",
                "Social Media {category} Design",
                "{style} Digital {category}"
            ],
            TemplateCategory.PRESENTATION: [
                "Professional {style} Presentation",
                "Corporate {category} Template",
                "Clean {style} {category} Design",
                "Business {category} Slides",
                "{style} Conference {category}"
            ],
            TemplateCategory.LOGO: [
                "Memorable {style} Logo Design",
                "Professional {category} Template",
                "Creative {style} {category}",
                "Brand {category} Identity",
                "{style} Visual {category}"
            ],
            TemplateCategory.EMAIL: [
                "Effective {style} Email Template",
                "Professional {category} Design",
                "Clean {style} {category}",
                "Marketing {category} Template",
                "{style} Communication {category}"
            ],
            TemplateCategory.MENU: [
                "Appetizing {style} Menu Design",
                "Professional {category} Template",
                "Elegant {style} {category}",
                "Restaurant {category} Layout",
                "{style} Culinary {category}"
            ]
        }

    def _load_tag_mappings(self):
        """Load tag mappings for categories."""
        self.tag_mappings = {
            TemplateCategory.POSTER: ["poster", "print", "marketing", "advertising", "visual"],
            TemplateCategory.BROCHURE: ["brochure", "print", "business", "corporate", "information"],
            TemplateCategory.WEBSITE: ["website", "web", "digital", "responsive", "ui"],
            TemplateCategory.BUSINESS_CARD: ["business card", "contact", "professional", "corporate", "print"],
            TemplateCategory.FLYER: ["flyer", "print", "marketing", "promotional", "advertising"],
            TemplateCategory.SOCIAL_MEDIA: ["social media", "digital", "marketing", "content", "engagement"],
            TemplateCategory.PRESENTATION: ["presentation", "slides", "business", "corporate", "conference"],
            TemplateCategory.LOGO: ["logo", "brand", "identity", "symbol", "visual"],
            TemplateCategory.EMAIL: ["email", "marketing", "communication", "digital", "newsletter"],
            TemplateCategory.MENU: ["menu", "restaurant", "food", "hospitality", "print"]
        }

    def _load_style_mappings(self):
        """Load style mappings and recommendations."""
        self.style_mappings = {
            "minimalist": ["clean", "simple", "modern", "minimal"],
            "corporate": ["professional", "business", "formal", "corporate"],
            "creative": ["artistic", "bold", "colorful", "creative"],
            "vintage": ["retro", "classic", "nostalgic", "vintage"],
            "modern": ["contemporary", "sleek", "current", "modern"],
            "elegant": ["sophisticated", "refined", "luxury", "elegant"],
            "playful": ["fun", "colorful", "energetic", "playful"],
            "industrial": ["urban", "rugged", "mechanical", "industrial"],
            "nature": ["organic", "earth", "green", "natural"],
            "tech": ["digital", "futuristic", "innovative", "tech"]
        }

    def build_metadata(self, category: TemplateCategory,
                      layout_data: Dict[str, Any],
                      style_info: Optional[Dict[str, Any]] = None,
                      brand_kit: Optional[str] = None,
                      quality: str = "standard") -> TemplateMetadata:
        """
        Build complete template metadata.

        Args:
            category: Template category
            layout_data: Generated layout data
            style_info: Optional style information
            brand_kit: Optional brand kit name
            quality: Quality level

        Returns:
            TemplateMetadata object
        """
        try:
            logger.info(f"Building metadata for {category.value} template")

            metadata = TemplateMetadata()
            metadata.category = category.value
            metadata.quality = quality

            # Generate name
            metadata.name = self._generate_name(category, style_info)

            # Generate description
            metadata.description = self._generate_description(category, style_info, layout_data)

            # Generate tags
            metadata.tags = self._generate_tags(category, style_info, brand_kit)

            # Generate recommended styles
            metadata.recommended_styles = self._generate_recommended_styles(style_info)

            # Generate workflow requirements
            metadata.workflow_requirements = self._generate_workflow_requirements(
                category, layout_data, quality
            )

            # Set dimensions
            metadata.dimensions = tuple(layout_data.get("dimensions", (1920, 1080)))

            # Set layout elements count
            metadata.layout_elements = len(layout_data.get("elements", []))

            # Set style and brand info
            if style_info:
                metadata.base_style = style_info.get("name", "")
            metadata.brand_kit = brand_kit

            # Set complexity based on layout
            element_count = len(layout_data.get("elements", []))
            if element_count < 5:
                metadata.complexity = "simple"
            elif element_count < 10:
                metadata.complexity = "medium"
            else:
                metadata.complexity = "complex"

            logger.info(f"Metadata built: {metadata.name}")
            return metadata

        except Exception as e:
            logger.error(f"Metadata building failed: {e}")
            # Return minimal metadata
            return TemplateMetadata(
                name=f"Generated {category.value.title()} Template",
                category=category.value,
                description=f"A {category.value} template generated by AI"
            )

    def _generate_name(self, category: TemplateCategory, style_info: Optional[Dict[str, Any]]) -> str:
        """Generate a template name."""
        import random

        templates = self.name_templates.get(category, ["{style} {category} Template"])

        # Get style name
        style_name = "Modern"
        if style_info:
            style_name = style_info.get("name", "Modern").title()

        # Get category display name
        category_name = category.value.replace("_", " ").title()

        # Choose random template
        template = random.choice(templates)

        # Fill in placeholders
        name = template.format(style=style_name, category=category_name)

        # Clean up name
        name = re.sub(r'\s+', ' ', name).strip()

        return name

    def _generate_description(self, category: TemplateCategory,
                            style_info: Optional[Dict[str, Any]],
                            layout_data: Dict[str, Any]) -> str:
        """Generate a template description."""
        category_name = category.value.replace("_", " ").title()

        style_desc = ""
        if style_info:
            style_name = style_info.get("name", "").title()
            style_desc = f" with a {style_name.lower()} design"

        element_count = len(layout_data.get("elements", []))
        complexity = "simple"
        if element_count > 10:
            complexity = "complex"
        elif element_count > 5:
            complexity = "medium"

        description = f"A professionally designed {category_name.lower()} template{style_desc}. " \
                     f"This {complexity} layout includes {element_count} elements and is " \
                     f"optimized for {category_name.lower()} use cases."

        return description

    def _generate_tags(self, category: TemplateCategory,
                      style_info: Optional[Dict[str, Any]],
                      brand_kit: Optional[str]) -> List[str]:
        """Generate tags for the template."""
        tags = set()

        # Add category tags
        tags.update(self.tag_mappings.get(category, []))

        # Add style tags
        if style_info:
            style_name = style_info.get("name", "").lower()
            if style_name in self.style_mappings:
                tags.update(self.style_mappings[style_name])

        # Add brand kit tag
        if brand_kit:
            tags.add(f"brand:{brand_kit.lower()}")

        # Add quality tags
        tags.add("ai-generated")
        tags.add("template")

        return sorted(list(tags))

    def _generate_recommended_styles(self, style_info: Optional[Dict[str, Any]]) -> List[str]:
        """Generate recommended styles for the template."""
        recommendations = []

        if style_info:
            base_style = style_info.get("name", "").lower()

            # Add complementary styles
            if base_style in self.style_mappings:
                related_styles = self.style_mappings[base_style][:3]  # Top 3 related
                recommendations.extend(related_styles)

            # Add the base style itself
            if base_style:
                recommendations.insert(0, base_style)

        # Default recommendations if no style info
        if not recommendations:
            recommendations = ["modern", "clean", "professional"]

        return list(set(recommendations))  # Remove duplicates

    def _generate_workflow_requirements(self, category: TemplateCategory,
                                      layout_data: Dict[str, Any],
                                      quality: str) -> Dict[str, Any]:
        """Generate workflow requirements for the template."""
        requirements = {
            "models": [],
            "loras": [],
            "controlnets": [],
            "upscalers": [],
            "min_steps": 20,
            "max_steps": 50,
            "recommended_steps": 30,
            "cfg_scale": 7.0,
            "denoising_strength": 0.6
        }

        # Analyze layout elements to determine requirements
        elements = layout_data.get("elements", [])
        has_images = any(e.get("type") == "image" for e in elements)
        has_text = any(e.get("type") == "text" for e in elements)

        if has_images:
            requirements["models"].append("SDXL Base 1.0")
            requirements["controlnets"].append("canny")
            requirements["upscalers"].append("4x-UltraSharp")

        if quality == "high":
            requirements["recommended_steps"] = 40
            requirements["cfg_scale"] = 8.0
        elif quality == "draft":
            requirements["recommended_steps"] = 15
            requirements["cfg_scale"] = 6.0

        # Category-specific requirements
        if category == TemplateCategory.LOGO:
            requirements["models"] = ["SDXL Logo Model"]
            requirements["loras"] = ["logo_design_v1"]
        elif category == TemplateCategory.POSTER:
            requirements["models"] = ["SDXL Poster Model"]
            requirements["controlnets"] = ["depth", "canny"]
        elif category == TemplateCategory.WEBSITE:
            requirements["models"] = ["SDXL Web Design Model"]
            requirements["loras"] = ["ui_elements_v2"]

        return requirements

    def update_metadata(self, metadata: TemplateMetadata, **updates) -> TemplateMetadata:
        """
        Update existing metadata with new values.

        Args:
            metadata: Existing metadata
            **updates: Fields to update

        Returns:
            Updated metadata
        """
        for key, value in updates.items():
            if hasattr(metadata, key):
                setattr(metadata, key, value)

        metadata.version = self._increment_version(metadata.version)
        return metadata

    def _increment_version(self, version: str) -> str:
        """Increment version number."""
        try:
            major, minor = version.split(".")
            return f"{major}.{int(minor) + 1}"
        except:
            return "1.1"

    def validate_metadata(self, metadata: TemplateMetadata) -> List[str]:
        """
        Validate metadata completeness.

        Args:
            metadata: Metadata to validate

        Returns:
            List of validation errors
        """
        errors = []

        if not metadata.name:
            errors.append("Name is required")

        if not metadata.category:
            errors.append("Category is required")

        if not metadata.description:
            errors.append("Description is required")

        if len(metadata.tags) == 0:
            errors.append("At least one tag is required")

        if metadata.dimensions[0] <= 0 or metadata.dimensions[1] <= 0:
            errors.append("Valid dimensions are required")

        return errors