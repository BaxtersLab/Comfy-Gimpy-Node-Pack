"""
Preview Builder for Comfy Gimpy Studio (Phase 12)

Generates preview images, thumbnails, and style previews for templates
using ComfyUI workflows and the fusion engine.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json

from ..shared.config import Config
from ..workflow_auto import WorkflowBuilder
from ..fusion import FusionEngine

logger = logging.getLogger(__name__)


class PreviewBuilder:
    """Builds preview images for generated templates."""

    def __init__(self, workflow_builder: WorkflowBuilder,
                 fusion_engine: FusionEngine,
                 config: Config):
        """
        Initialize the preview builder.

        Args:
            workflow_builder: Workflow auto-generation builder
            fusion_engine: Style fusion engine
            config: Application configuration
        """
        self.workflow_builder = workflow_builder
        self.fusion_engine = fusion_engine
        self.config = config

        # Preview settings
        self.thumbnail_size = (300, 300)
        self.preview_size = (800, 600)
        self.quality = 85

        logger.info("Preview builder initialized")

    def generate_previews(self, layout_data: Dict[str, Any],
                         workflow_data: Dict[str, Any],
                         style_name: Optional[str] = None,
                         dimensions: Tuple[int, int] = (1920, 1080),
                         quality: str = "standard") -> List[Dict[str, Any]]:
        """
        Generate all preview images for a template.

        Args:
            layout_data: Layout data dictionary
            workflow_data: Workflow data dictionary
            style_name: Optional style name
            dimensions: Template dimensions
            quality: Quality level

        Returns:
            List of preview data dictionaries
        """
        try:
            logger.info("Generating template previews")

            previews = []

            # Generate main preview
            main_preview = self._generate_main_preview(layout_data, workflow_data, dimensions, quality)
            if main_preview:
                previews.append(main_preview)

            # Generate thumbnail
            thumbnail = self._generate_thumbnail(layout_data, dimensions)
            if thumbnail:
                previews.append(thumbnail)

            # Generate style preview if style specified
            if style_name:
                style_preview = self._generate_style_preview(layout_data, style_name, dimensions)
                if style_preview:
                    previews.append(style_preview)

            # Generate layout wireframe
            wireframe = self._generate_wireframe_preview(layout_data, dimensions)
            if wireframe:
                previews.append(wireframe)

            logger.info(f"Generated {len(previews)} previews")
            return previews

        except Exception as e:
            logger.error(f"Preview generation failed: {e}")
            return []

    def _generate_main_preview(self, layout_data: Dict[str, Any],
                              workflow_data: Dict[str, Any],
                              dimensions: Tuple[int, int],
                              quality: str) -> Optional[Dict[str, Any]]:
        """
        Generate the main template preview.

        Args:
            layout_data: Layout data
            workflow_data: Workflow data
            dimensions: Template dimensions
            quality: Quality level

        Returns:
            Preview data dictionary or None
        """
        try:
            # Create base image
            img = Image.new('RGB', dimensions, color='white')
            draw = ImageDraw.Draw(img)

            # Draw layout elements as placeholders
            for element in layout_data.get("elements", []):
                self._draw_layout_element(draw, element, dimensions)

            # Apply style overlay if workflow data available
            if workflow_data:
                img = self._apply_workflow_styling(img, workflow_data, quality)

            # Resize for preview
            img.thumbnail(self.preview_size, Image.Resampling.LANCZOS)

            # Save preview
            preview_path = self._get_preview_path("preview", "png")
            img.save(preview_path, quality=self.quality)

            return {
                "type": "preview",
                "filename": "preview.png",
                "path": str(preview_path),
                "dimensions": img.size,
                "description": "Main template preview"
            }

        except Exception as e:
            logger.error(f"Main preview generation failed: {e}")
            return None

    def _generate_thumbnail(self, layout_data: Dict[str, Any],
                           dimensions: Tuple[int, int]) -> Optional[Dict[str, Any]]:
        """
        Generate thumbnail preview.

        Args:
            layout_data: Layout data
            dimensions: Template dimensions

        Returns:
            Thumbnail data dictionary or None
        """
        try:
            # Create base image
            img = Image.new('RGB', dimensions, color='white')
            draw = ImageDraw.Draw(img)

            # Draw simplified layout elements
            for element in layout_data.get("elements", []):
                self._draw_layout_element_simple(draw, element, dimensions)

            # Resize to thumbnail
            img.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)

            # Add border
            bordered = Image.new('RGB', (self.thumbnail_size[0] + 4, self.thumbnail_size[1] + 4), color='black')
            bordered.paste(img, (2, 2))

            # Save thumbnail
            thumb_path = self._get_preview_path("thumbnail", "png")
            bordered.save(thumb_path, quality=self.quality)

            return {
                "type": "thumbnail",
                "filename": "thumbnail.png",
                "path": str(thumb_path),
                "dimensions": bordered.size,
                "description": "Template thumbnail"
            }

        except Exception as e:
            logger.error(f"Thumbnail generation failed: {e}")
            return None

    def _generate_style_preview(self, layout_data: Dict[str, Any],
                               style_name: str,
                               dimensions: Tuple[int, int]) -> Optional[Dict[str, Any]]:
        """
        Generate style-specific preview.

        Args:
            layout_data: Layout data
            style_name: Style name
            dimensions: Template dimensions

        Returns:
            Style preview data dictionary or None
        """
        try:
            # Create base image
            img = Image.new('RGB', dimensions, color='white')
            draw = ImageDraw.Draw(img)

            # Apply style colors/patterns
            style_colors = self._get_style_colors(style_name)
            img = self._apply_style_colors(img, style_colors)

            # Draw layout elements with style
            for element in layout_data.get("elements", []):
                self._draw_layout_element_styled(draw, element, dimensions, style_colors)

            # Resize for preview
            img.thumbnail(self.preview_size, Image.Resampling.LANCZOS)

            # Save style preview
            style_path = self._get_preview_path(f"style_{style_name}", "png")
            img.save(style_path, quality=self.quality)

            return {
                "type": "style_preview",
                "filename": f"style_{style_name}.png",
                "path": str(style_path),
                "dimensions": img.size,
                "style": style_name,
                "description": f"Style preview for {style_name}"
            }

        except Exception as e:
            logger.error(f"Style preview generation failed: {e}")
            return None

    def _generate_wireframe_preview(self, layout_data: Dict[str, Any],
                                   dimensions: Tuple[int, int]) -> Optional[Dict[str, Any]]:
        """
        Generate wireframe preview showing layout structure.

        Args:
            layout_data: Layout data
            dimensions: Template dimensions

        Returns:
            Wireframe preview data dictionary or None
        """
        try:
            # Create base image
            img = Image.new('RGB', dimensions, color='white')
            draw = ImageDraw.Draw(img)

            # Draw wireframe elements
            for element in layout_data.get("elements", []):
                self._draw_wireframe_element(draw, element, dimensions)

            # Draw guides
            for guide in layout_data.get("guides", []):
                self._draw_guide(draw, guide, dimensions)

            # Resize for preview
            img.thumbnail(self.preview_size, Image.Resampling.LANCZOS)

            # Save wireframe
            wireframe_path = self._get_preview_path("wireframe", "png")
            img.save(wireframe_path, quality=self.quality)

            return {
                "type": "wireframe",
                "filename": "wireframe.png",
                "path": str(wireframe_path),
                "dimensions": img.size,
                "description": "Layout wireframe preview"
            }

        except Exception as e:
            logger.error(f"Wireframe generation failed: {e}")
            return None

    def _draw_layout_element(self, draw: ImageDraw.ImageDraw,
                           element: Dict[str, Any],
                           dimensions: Tuple[int, int]):
        """
        Draw a layout element on the preview.

        Args:
            draw: PIL ImageDraw object
            element: Element data
            dimensions: Canvas dimensions
        """
        x, y = element.get("x", 0), element.get("y", 0)
        w, h = element.get("width", 100), element.get("height", 100)
        elem_type = element.get("type", "unknown")

        # Draw based on element type
        if elem_type == "text":
            # Draw text placeholder
            draw.rectangle([x, y, x + w, y + h], outline='blue', fill='lightblue')
            draw.text((x + 10, y + 10), "TEXT", fill='blue')
        elif elem_type == "image":
            # Draw image placeholder
            draw.rectangle([x, y, x + w, y + h], outline='green', fill='lightgreen')
            draw.text((x + 10, y + 10), "IMAGE", fill='green')
        elif elem_type == "shape":
            # Draw shape placeholder
            draw.rectangle([x, y, x + w, y + h], outline='red', fill='pink')
            draw.text((x + 10, y + 10), "SHAPE", fill='red')
        else:
            # Generic placeholder
            draw.rectangle([x, y, x + w, y + h], outline='gray', fill='lightgray')

    def _draw_layout_element_simple(self, draw: ImageDraw.ImageDraw,
                                  element: Dict[str, Any],
                                  dimensions: Tuple[int, int]):
        """
        Draw a simplified layout element for thumbnails.

        Args:
            draw: PIL ImageDraw object
            element: Element data
            dimensions: Canvas dimensions
        """
        x, y = element.get("x", 0), element.get("y", 0)
        w, h = element.get("width", 100), element.get("height", 100)

        # Simple colored rectangle
        colors = {'text': 'blue', 'image': 'green', 'shape': 'red'}
        color = colors.get(element.get("type", "unknown"), 'gray')

        draw.rectangle([x, y, x + w, y + h], fill=color)

    def _draw_layout_element_styled(self, draw: ImageDraw.ImageDraw,
                                  element: Dict[str, Any],
                                  dimensions: Tuple[int, int],
                                  style_colors: Dict[str, str]):
        """
        Draw a styled layout element.

        Args:
            draw: PIL ImageDraw object
            element: Element data
            dimensions: Canvas dimensions
            style_colors: Style color palette
        """
        x, y = element.get("x", 0), element.get("y", 0)
        w, h = element.get("width", 100), element.get("height", 100)
        elem_type = element.get("type", "unknown")

        # Use style colors
        primary_color = style_colors.get("primary", "blue")
        secondary_color = style_colors.get("secondary", "lightblue")

        if elem_type == "text":
            draw.rectangle([x, y, x + w, y + h], fill=secondary_color, outline=primary_color)
        elif elem_type == "image":
            draw.rectangle([x, y, x + w, y + h], fill=primary_color)
        else:
            draw.rectangle([x, y, x + w, y + h], fill=secondary_color, outline=primary_color)

    def _draw_wireframe_element(self, draw: ImageDraw.ImageDraw,
                              element: Dict[str, Any],
                              dimensions: Tuple[int, int]):
        """
        Draw wireframe representation of element.

        Args:
            draw: PIL ImageDraw object
            element: Element data
            dimensions: Canvas dimensions
        """
        x, y = element.get("x", 0), element.get("y", 0)
        w, h = element.get("width", 100), element.get("height", 100)

        # Draw rectangle outline
        draw.rectangle([x, y, x + w, y + h], outline='black', width=2)

        # Add element type label
        elem_type = element.get("type", "unknown").upper()
        draw.text((x + 5, y + 5), elem_type, fill='black')

    def _draw_guide(self, draw: ImageDraw.ImageDraw,
                   guide: Dict[str, Any],
                   dimensions: Tuple[int, int]):
        """
        Draw a guide line.

        Args:
            draw: PIL ImageDraw object
            guide: Guide data
            dimensions: Canvas dimensions
        """
        guide_type = guide.get("type", "")
        position = guide.get("position", 0)

        if guide_type == "vertical":
            draw.line([position, 0, position, dimensions[1]], fill='red', width=1)
        elif guide_type == "horizontal":
            draw.line([0, position, dimensions[0], position], fill='red', width=1)

    def _apply_workflow_styling(self, img: Image.Image,
                               workflow_data: Dict[str, Any],
                               quality: str) -> Image.Image:
        """
        Apply workflow-based styling to preview.

        Args:
            img: Base image
            workflow_data: Workflow data
            quality: Quality level

        Returns:
            Styled image
        """
        # This would integrate with actual ComfyUI workflow execution
        # For now, just return the image unchanged
        return img

    def _get_style_colors(self, style_name: str) -> Dict[str, str]:
        """
        Get color palette for a style.

        Args:
            style_name: Style name

        Returns:
            Color palette dictionary
        """
        # Style color mappings
        style_palettes = {
            "minimalist": {"primary": "#000000", "secondary": "#ffffff", "accent": "#cccccc"},
            "corporate": {"primary": "#003366", "secondary": "#ffffff", "accent": "#0066cc"},
            "creative": {"primary": "#ff6b35", "secondary": "#f7f3e9", "accent": "#8338ec"},
            "vintage": {"primary": "#8b4513", "secondary": "#f5f5dc", "accent": "#daa520"},
            "modern": {"primary": "#2c3e50", "secondary": "#ecf0f1", "accent": "#3498db"},
            "elegant": {"primary": "#2c1810", "secondary": "#f8f8f8", "accent": "#d4af37"},
            "playful": {"primary": "#ff0080", "secondary": "#ffff00", "accent": "#00ff00"},
            "industrial": {"primary": "#333333", "secondary": "#cccccc", "accent": "#ff6600"},
            "nature": {"primary": "#228b22", "secondary": "#f0f8ff", "accent": "#daa520"},
            "tech": {"primary": "#00ff41", "secondary": "#000000", "accent": "#ffffff"}
        }

        return style_palettes.get(style_name.lower(), {"primary": "#333333", "secondary": "#cccccc", "accent": "#666666"})

    def _apply_style_colors(self, img: Image.Image, colors: Dict[str, str]) -> Image.Image:
        """
        Apply style colors to image background.

        Args:
            img: Base image
            colors: Color palette

        Returns:
            Colored image
        """
        # Create gradient background
        width, height = img.size
        gradient = Image.new('RGB', (width, height))

        # Simple gradient from secondary to primary
        for y in range(height):
            for x in range(width):
                # Simple interpolation
                ratio = y / height
                # For now, just use secondary color
                gradient.putpixel((x, y), self._hex_to_rgb(colors.get("secondary", "#ffffff")))

        return gradient

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """
        Convert hex color to RGB tuple.

        Args:
            hex_color: Hex color string

        Returns:
            RGB tuple
        """
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _get_preview_path(self, name: str, ext: str) -> Path:
        """
        Get path for preview file.

        Args:
            name: Preview name
            ext: File extension

        Returns:
            Preview file path
        """
        # This would be in a temp directory or template directory
        # For now, return a placeholder path
        return Path(f"temp/preview_{name}.{ext}")

    def generate_variant_previews(self, base_template_path: Path,
                                variants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate previews for template variants.

        Args:
            base_template_path: Path to base template
            variants: List of variant data

        Returns:
            List of variant preview data
        """
        # This would generate previews for each variant
        # For now, return empty list
        return []