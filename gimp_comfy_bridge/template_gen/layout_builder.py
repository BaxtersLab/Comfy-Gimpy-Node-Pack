"""
Layout Builder for Comfy Gimpy Studio (Phase 12)

Builds GIMP XCF layout structures for generated templates,
including text boxes, image placeholders, guides, and layer groups.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import json

from ..shared.config import Config
from ..shared.types import TemplateCategory

logger = logging.getLogger(__name__)


@dataclass
class LayoutElement:
    """Represents a layout element in the template."""

    element_type: str  # "text", "image", "shape", "guide"
    name: str
    x: int
    y: int
    width: int
    height: int
    properties: Dict[str, Any] = None

    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


class LayoutBuilder:
    """Builds GIMP XCF layout structures for templates."""

    def __init__(self, config: Config):
        """
        Initialize the layout builder.

        Args:
            config: Application configuration
        """
        self.config = config

        # Layout templates for different categories
        self._load_layout_templates()

        logger.info("Layout builder initialized")

    def _load_layout_templates(self):
        """Load predefined layout templates."""
        # These would typically be loaded from JSON files
        # For now, we'll define them programmatically
        self.layout_templates = {
            TemplateCategory.POSTER: self._get_poster_layout,
            TemplateCategory.BROCHURE: self._get_brochure_layout,
            TemplateCategory.WEBSITE: self._get_website_layout,
            TemplateCategory.BUSINESS_CARD: self._get_business_card_layout,
            TemplateCategory.FLYER: self._get_flyer_layout,
            TemplateCategory.SOCIAL_MEDIA: self._get_social_media_layout,
            TemplateCategory.PRESENTATION: self._get_presentation_layout,
            TemplateCategory.LOGO: self._get_logo_layout,
            TemplateCategory.EMAIL: self._get_email_layout,
            TemplateCategory.MENU: self._get_menu_layout
        }

    def build_layout(self, category: TemplateCategory,
                    dimensions: Tuple[int, int],
                    style_data: Optional[Dict[str, Any]] = None,
                    complexity: str = "medium",
                    brand_kit: Optional[str] = None) -> Dict[str, Any]:
        """
        Build a layout for the specified category.

        Args:
            category: Template category
            dimensions: (width, height) in pixels
            style_data: Optional style data to influence layout
            complexity: Layout complexity ("simple", "medium", "complex")
            brand_kit: Optional brand kit to incorporate

        Returns:
            Layout data dictionary
        """
        try:
            logger.info(f"Building {complexity} layout for {category.value}")

            # Get base layout template
            if category in self.layout_templates:
                base_layout = self.layout_templates[category](dimensions, complexity)
            else:
                base_layout = self._get_generic_layout(dimensions, complexity)

            # Apply style influences
            if style_data:
                base_layout = self._apply_style_influences(base_layout, style_data)

            # Apply brand kit elements
            if brand_kit:
                base_layout = self._apply_brand_kit(base_layout, brand_kit)

            # Add guides and grids
            base_layout = self._add_guides_and_grids(base_layout, dimensions)

            # Validate layout
            self._validate_layout(base_layout, dimensions)

            logger.info(f"Layout built with {len(base_layout.get('elements', []))} elements")
            return base_layout

        except Exception as e:
            logger.error(f"Layout building failed: {e}")
            # Return minimal fallback layout
            return self._get_fallback_layout(dimensions)

    def _get_poster_layout(self, dimensions: Tuple[int, int], complexity: str) -> Dict[str, Any]:
        """Get poster layout template."""
        width, height = dimensions
        elements = []

        if complexity == "simple":
            # Simple poster: title, subtitle, main image
            elements = [
                LayoutElement("text", "title", width//2 - 300, height//4, 600, 80,
                            {"font_size": 72, "alignment": "center"}),
                LayoutElement("text", "subtitle", width//2 - 250, height//4 + 100, 500, 40,
                            {"font_size": 24, "alignment": "center"}),
                LayoutElement("image", "main_image", width//2 - 400, height//2, 800, 600,
                            {"aspect_ratio": "4:3"})
            ]
        elif complexity == "medium":
            # Medium poster: header, main content, footer
            elements = [
                LayoutElement("text", "title", width//2 - 300, 100, 600, 80,
                            {"font_size": 72, "alignment": "center"}),
                LayoutElement("text", "subtitle", width//2 - 250, 200, 500, 40,
                            {"font_size": 24, "alignment": "center"}),
                LayoutElement("image", "hero_image", width//2 - 400, 280, 800, 400,
                            {"aspect_ratio": "2:1"}),
                LayoutElement("text", "body_text", width//2 - 350, 720, 700, 120,
                            {"font_size": 18, "alignment": "center", "multiline": True}),
                LayoutElement("text", "footer", width//2 - 200, height - 100, 400, 30,
                            {"font_size": 14, "alignment": "center"})
            ]
        else:  # complex
            # Complex poster: multiple sections, images, text blocks
            elements = [
                LayoutElement("text", "title", width//2 - 300, 50, 600, 80,
                            {"font_size": 72, "alignment": "center"}),
                LayoutElement("text", "subtitle", width//2 - 250, 150, 500, 40,
                            {"font_size": 24, "alignment": "center"}),
                LayoutElement("image", "hero_image", width//2 - 400, 220, 800, 300,
                            {"aspect_ratio": "8:3"}),
                LayoutElement("text", "section_title_1", 100, 550, 300, 40,
                            {"font_size": 28, "alignment": "left"}),
                LayoutElement("text", "body_text_1", 100, 600, 350, 150,
                            {"font_size": 16, "alignment": "left", "multiline": True}),
                LayoutElement("image", "side_image_1", 500, 550, 250, 200,
                            {"aspect_ratio": "5:4"}),
                LayoutElement("text", "section_title_2", width - 450, 550, 300, 40,
                            {"font_size": 28, "alignment": "left"}),
                LayoutElement("text", "body_text_2", width - 450, 600, 350, 150,
                            {"font_size": 16, "alignment": "left", "multiline": True}),
                LayoutElement("image", "side_image_2", width - 250, 550, 150, 200,
                            {"aspect_ratio": "3:4"}),
                LayoutElement("text", "footer", width//2 - 200, height - 80, 400, 30,
                            {"font_size": 14, "alignment": "center"})
            ]

        return {
            "dimensions": dimensions,
            "elements": [self._element_to_dict(e) for e in elements],
            "guides": self._generate_guides(dimensions, "poster"),
            "layer_groups": ["Background", "Content", "Text", "Images"],
            "category": "poster"
        }

    def _get_brochure_layout(self, dimensions: Tuple[int, int], complexity: str) -> Dict[str, Any]:
        """Get brochure layout template."""
        width, height = dimensions
        elements = []

        # Tri-fold brochure layout
        panel_width = width // 3

        if complexity == "simple":
            elements = [
                LayoutElement("text", "title", panel_width//2 - 100, 100, 200, 50,
                            {"font_size": 36, "alignment": "center"}),
                LayoutElement("image", "main_image", panel_width//2 - 150, 180, 300, 200,
                            {"aspect_ratio": "3:2"}),
                LayoutElement("text", "body_text", panel_width//2 - 120, 400, 240, 150,
                            {"font_size": 14, "alignment": "left", "multiline": True})
            ]
        else:
            # Add content to all three panels
            for i in range(3):
                x_offset = i * panel_width
                elements.extend([
                    LayoutElement("text", f"panel_{i+1}_title", x_offset + 50, 50, panel_width - 100, 40,
                                {"font_size": 24, "alignment": "center"}),
                    LayoutElement("image", f"panel_{i+1}_image", x_offset + 50, 110, panel_width - 100, 150,
                                {"aspect_ratio": "4:3"}),
                    LayoutElement("text", f"panel_{i+1}_text", x_offset + 50, 280, panel_width - 100, 120,
                                {"font_size": 12, "alignment": "left", "multiline": True})
                ])

        return {
            "dimensions": dimensions,
            "elements": [self._element_to_dict(e) for e in elements],
            "guides": self._generate_guides(dimensions, "brochure"),
            "layer_groups": ["Panel 1", "Panel 2", "Panel 3", "Background"],
            "category": "brochure"
        }

    def _get_website_layout(self, dimensions: Tuple[int, int], complexity: str) -> Dict[str, Any]:
        """Get website mockup layout template."""
        width, height = dimensions
        elements = []

        # Header
        elements.append(LayoutElement("text", "site_title", 50, 30, 200, 40,
                                    {"font_size": 24, "alignment": "left"}))
        elements.append(LayoutElement("text", "navigation", width - 300, 30, 250, 30,
                                    {"font_size": 16, "alignment": "right"}))

        # Hero section
        elements.extend([
            LayoutElement("image", "hero_image", 0, 80, width, 300,
                        {"aspect_ratio": "16:9"}),
            LayoutElement("text", "hero_title", width//2 - 200, 200, 400, 60,
                        {"font_size": 48, "alignment": "center"}),
            LayoutElement("text", "hero_subtitle", width//2 - 150, 280, 300, 30,
                        {"font_size": 18, "alignment": "center"})
        ])

        if complexity in ["medium", "complex"]:
            # Content sections
            y_offset = 400
            for i in range(2 if complexity == "medium" else 3):
                elements.extend([
                    LayoutElement("text", f"section_{i+1}_title", 50, y_offset, width - 100, 40,
                                {"font_size": 32, "alignment": "left"}),
                    LayoutElement("text", f"section_{i+1}_text", 50, y_offset + 50, width//2 - 50, 100,
                                {"font_size": 16, "alignment": "left", "multiline": True}),
                    LayoutElement("image", f"section_{i+1}_image", width//2 + 50, y_offset + 50, width//2 - 100, 150,
                                {"aspect_ratio": "16:9"})
                ])
                y_offset += 220

        # Footer
        elements.append(LayoutElement("text", "footer", 50, height - 60, width - 100, 30,
                                    {"font_size": 14, "alignment": "center"}))

        return {
            "dimensions": dimensions,
            "elements": [self._element_to_dict(e) for e in elements],
            "guides": self._generate_guides(dimensions, "website"),
            "layer_groups": ["Header", "Hero", "Content", "Footer", "Background"],
            "category": "website"
        }

    def _get_business_card_layout(self, dimensions: Tuple[int, int], complexity: str) -> Dict[str, Any]:
        """Get business card layout template."""
        width, height = dimensions
        elements = []

        # Standard business card layout
        elements = [
            LayoutElement("text", "name", 20, 20, width - 40, 30,
                        {"font_size": 18, "alignment": "left"}),
            LayoutElement("text", "title", 20, 55, width - 40, 20,
                        {"font_size": 12, "alignment": "left"}),
            LayoutElement("text", "company", 20, 80, width - 40, 20,
                        {"font_size": 12, "alignment": "left"}),
            LayoutElement("text", "contact", 20, height - 50, width - 40, 15,
                        {"font_size": 10, "alignment": "left", "multiline": True})
        ]

        # Add logo if complex
        if complexity == "complex":
            elements.append(LayoutElement("image", "logo", width - 80, 20, 60, 60,
                                        {"aspect_ratio": "1:1"}))

        return {
            "dimensions": dimensions,
            "elements": [self._element_to_dict(e) for e in elements],
            "guides": self._generate_guides(dimensions, "business_card"),
            "layer_groups": ["Text", "Logo", "Background"],
            "category": "business_card"
        }

    def _get_flyer_layout(self, dimensions: Tuple[int, int], complexity: str) -> Dict[str, Any]:
        """Get flyer layout template."""
        width, height = dimensions
        elements = []

        # Eye-catching flyer layout
        elements = [
            LayoutElement("image", "background_image", 0, 0, width, height,
                        {"aspect_ratio": "8.5:11"}),
            LayoutElement("text", "headline", width//2 - 200, height//4, 400, 60,
                        {"font_size": 48, "alignment": "center"}),
            LayoutElement("text", "subheadline", width//2 - 150, height//4 + 80, 300, 30,
                        {"font_size": 24, "alignment": "center"}),
            LayoutElement("text", "body_text", width//2 - 180, height//2, 360, 120,
                        {"font_size": 16, "alignment": "center", "multiline": True}),
            LayoutElement("text", "call_to_action", width//2 - 120, height - 150, 240, 40,
                        {"font_size": 20, "alignment": "center"}),
            LayoutElement("text", "fine_print", 50, height - 50, width - 100, 20,
                        {"font_size": 10, "alignment": "center"})
        ]

        return {
            "dimensions": dimensions,
            "elements": [self._element_to_dict(e) for e in elements],
            "guides": self._generate_guides(dimensions, "flyer"),
            "layer_groups": ["Background", "Text", "Images"],
            "category": "flyer"
        }

    def _get_social_media_layout(self, dimensions: Tuple[int, int], complexity: str) -> Dict[str, Any]:
        """Get social media layout template."""
        width, height = dimensions
        elements = []

        # Square format social media post
        elements = [
            LayoutElement("image", "background", 0, 0, width, height,
                        {"aspect_ratio": "1:1"}),
            LayoutElement("text", "main_text", width//2 - 150, height//2 - 50, 300, 60,
                        {"font_size": 36, "alignment": "center", "multiline": True}),
            LayoutElement("text", "username", 50, height - 80, width - 100, 25,
                        {"font_size": 16, "alignment": "center"})
        ]

        if complexity == "complex":
            elements.append(LayoutElement("image", "profile_image", 50, 50, 100, 100,
                                        {"aspect_ratio": "1:1", "circle_crop": True}))

        return {
            "dimensions": dimensions,
            "elements": [self._element_to_dict(e) for e in elements],
            "guides": self._generate_guides(dimensions, "social_media"),
            "layer_groups": ["Background", "Text", "Profile", "Graphics"],
            "category": "social_media"
        }

    def _get_presentation_layout(self, dimensions: Tuple[int, int], complexity: str) -> Dict[str, Any]:
        """Get presentation slide layout template."""
        width, height = dimensions
        elements = []

        # 16:9 presentation slide
        elements = [
            LayoutElement("text", "title", 100, 100, width - 200, 80,
                        {"font_size": 44, "alignment": "left"}),
            LayoutElement("text", "subtitle", 100, 200, width - 200, 40,
                        {"font_size": 24, "alignment": "left"}),
            LayoutElement("text", "bullet_points", 120, 280, width - 240, height - 400,
                        {"font_size": 20, "alignment": "left", "multiline": True, "bullet_list": True})
        ]

        if complexity in ["medium", "complex"]:
            elements.append(LayoutElement("image", "main_image", width//2 + 50, 280, width//2 - 150, 200,
                                        {"aspect_ratio": "16:9"}))

        return {
            "dimensions": dimensions,
            "elements": [self._element_to_dict(e) for e in elements],
            "guides": self._generate_guides(dimensions, "presentation"),
            "layer_groups": ["Title", "Content", "Images", "Background"],
            "category": "presentation"
        }

    def _get_logo_layout(self, dimensions: Tuple[int, int], complexity: str) -> Dict[str, Any]:
        """Get logo layout template."""
        width, height = dimensions
        center_x, center_y = width // 2, height // 2

        elements = [
            LayoutElement("text", "logo_text", center_x - 150, center_y - 50, 300, 100,
                        {"font_size": 72, "alignment": "center"}),
            LayoutElement("shape", "logo_symbol", center_x - 50, center_y - 50, 100, 100,
                        {"shape_type": "circle"})
        ]

        return {
            "dimensions": dimensions,
            "elements": [self._element_to_dict(e) for e in elements],
            "guides": self._generate_guides(dimensions, "logo"),
            "layer_groups": ["Text", "Symbol", "Background"],
            "category": "logo"
        }

    def _get_email_layout(self, dimensions: Tuple[int, int], complexity: str) -> Dict[str, Any]:
        """Get email template layout."""
        width, height = dimensions
        elements = []

        # Email header
        elements.extend([
            LayoutElement("text", "subject", 50, 30, width - 100, 30,
                        {"font_size": 18, "alignment": "left"}),
            LayoutElement("text", "preheader", 50, 70, width - 100, 20,
                        {"font_size": 12, "alignment": "left"})
        ])

        # Email body
        y_offset = 120
        elements.extend([
            LayoutElement("text", "greeting", 50, y_offset, width - 100, 30,
                        {"font_size": 16, "alignment": "left"}),
            LayoutElement("image", "hero_image", 50, y_offset + 50, width - 100, 200,
                        {"aspect_ratio": "16:9"}),
            LayoutElement("text", "main_content", 50, y_offset + 270, width - 100, 150,
                        {"font_size": 14, "alignment": "left", "multiline": True}),
            LayoutElement("text", "call_to_action", width//2 - 100, y_offset + 440, 200, 40,
                        {"font_size": 18, "alignment": "center"}),
            LayoutElement("text", "footer", 50, height - 60, width - 100, 30,
                        {"font_size": 12, "alignment": "center"})
        ])

        return {
            "dimensions": dimensions,
            "elements": [self._element_to_dict(e) for e in elements],
            "guides": self._generate_guides(dimensions, "email"),
            "layer_groups": ["Header", "Hero", "Content", "CTA", "Footer"],
            "category": "email"
        }

    def _get_menu_layout(self, dimensions: Tuple[int, int], complexity: str) -> Dict[str, Any]:
        """Get menu layout template."""
        width, height = dimensions
        elements = []

        # Restaurant menu layout
        elements.extend([
            LayoutElement("text", "restaurant_name", width//2 - 200, 50, 400, 60,
                        {"font_size": 48, "alignment": "center"}),
            LayoutElement("text", "menu_title", width//2 - 150, 130, 300, 40,
                        {"font_size": 28, "alignment": "center"})
        ])

        # Menu sections
        y_offset = 200
        sections = ["Appetizers", "Main Courses", "Desserts", "Beverages"]
        for section in sections:
            elements.extend([
                LayoutElement("text", f"{section.lower()}_title", 100, y_offset, 300, 30,
                            {"font_size": 24, "alignment": "left"}),
                LayoutElement("text", f"{section.lower()}_items", 120, y_offset + 40, width - 240, 120,
                            {"font_size": 14, "alignment": "left", "multiline": True})
            ])
            y_offset += 180

        return {
            "dimensions": dimensions,
            "elements": [self._element_to_dict(e) for e in elements],
            "guides": self._generate_guides(dimensions, "menu"),
            "layer_groups": ["Header", "Sections", "Background"],
            "category": "menu"
        }

    def _get_generic_layout(self, dimensions: Tuple[int, int], complexity: str) -> Dict[str, Any]:
        """Get generic layout template."""
        width, height = dimensions
        elements = []

        # Simple generic layout
        elements = [
            LayoutElement("text", "title", width//2 - 150, height//4, 300, 50,
                        {"font_size": 36, "alignment": "center"}),
            LayoutElement("image", "main_image", width//2 - 200, height//2, 400, 300,
                        {"aspect_ratio": "4:3"}),
            LayoutElement("text", "description", width//2 - 180, height - 150, 360, 80,
                        {"font_size": 16, "alignment": "center", "multiline": True})
        ]

        return {
            "dimensions": dimensions,
            "elements": [self._element_to_dict(e) for e in elements],
            "guides": self._generate_guides(dimensions, "generic"),
            "layer_groups": ["Text", "Images", "Background"],
            "category": "generic"
        }

    def _get_fallback_layout(self, dimensions: Tuple[int, int]) -> Dict[str, Any]:
        """Get minimal fallback layout."""
        width, height = dimensions
        elements = [
            LayoutElement("text", "title", width//2 - 100, height//2 - 25, 200, 50,
                        {"font_size": 24, "alignment": "center"})
        ]

        return {
            "dimensions": dimensions,
            "elements": [self._element_to_dict(e) for e in elements],
            "guides": [],
            "layer_groups": ["Text", "Background"],
            "category": "fallback"
        }

    def _apply_style_influences(self, layout_data: Dict[str, Any], style_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply style influences to layout."""
        # This would modify layout based on style preferences
        # For now, just return the layout unchanged
        return layout_data

    def _apply_brand_kit(self, layout_data: Dict[str, Any], brand_kit: str) -> Dict[str, Any]:
        """Apply brand kit elements to layout."""
        # This would add brand-specific elements like logos, colors, etc.
        # For now, just return the layout unchanged
        return layout_data

    def _add_guides_and_grids(self, layout_data: Dict[str, Any], dimensions: Tuple[int, int]) -> Dict[str, Any]:
        """Add guides and grids to layout."""
        width, height = dimensions

        # Add margin guides
        margin = 50
        layout_data["guides"].extend([
            {"type": "vertical", "position": margin},
            {"type": "vertical", "position": width - margin},
            {"type": "horizontal", "position": margin},
            {"type": "horizontal", "position": height - margin}
        ])

        # Add center guides
        layout_data["guides"].extend([
            {"type": "vertical", "position": width // 2},
            {"type": "horizontal", "position": height // 2}
        ])

        return layout_data

    def _generate_guides(self, dimensions: Tuple[int, int], layout_type: str) -> List[Dict[str, Any]]:
        """Generate guides for a layout type."""
        # Basic guides - can be extended per layout type
        return []

    def _validate_layout(self, layout_data: Dict[str, Any], dimensions: Tuple[int, int]):
        """Validate layout data."""
        width, height = dimensions

        for element in layout_data.get("elements", []):
            # Check bounds
            if (element["x"] + element["width"] > width or
                element["y"] + element["height"] > height):
                logger.warning(f"Element {element['name']} extends beyond canvas bounds")

    def _element_to_dict(self, element: LayoutElement) -> Dict[str, Any]:
        """Convert LayoutElement to dictionary."""
        return {
            "type": element.element_type,
            "name": element.name,
            "x": element.x,
            "y": element.y,
            "width": element.width,
            "height": element.height,
            "properties": element.properties
        }

    def export_to_xcf(self, layout_data: Dict[str, Any], output_path: Path):
        """
        Export layout to GIMP XCF format.

        Args:
            layout_data: Layout data dictionary
            output_path: Output file path
        """
        # This would create an actual XCF file
        # For now, we'll create a JSON representation
        with open(output_path, 'w') as f:
            json.dump(layout_data, f, indent=2)

        logger.info(f"Layout exported to: {output_path}")