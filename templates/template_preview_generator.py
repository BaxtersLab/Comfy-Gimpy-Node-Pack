#!/usr/bin/env python3
"""
Template Preview Generator for Comfy Gimpy Studio

Generates preview thumbnails for templates by rendering them through ComfyUI workflows.
Creates realistic previews that show how templates will appear when loaded in GIMP.
"""

import json
import pathlib
import requests
import time
from typing import Dict, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
import sys
import os


class TemplatePreviewGenerator:
    """Generates preview images for templates."""

    def __init__(self, comfyui_url: str = "http://127.0.0.1:8188"):
        """
        Initialize the preview generator.

        Args:
            comfyui_url: URL of the ComfyUI server
        """
        self.comfyui_url = comfyui_url.rstrip('/')
        self.font_cache = {}

    def _get_font(self, font_name: str = "arial.ttf", size: int = 20) -> ImageFont.FreeTypeFont:
        """Get a font for text rendering, with fallback to default."""
        cache_key = f"{font_name}_{size}"

        if cache_key in self.font_cache:
            return self.font_cache[cache_key]

        try:
            # Try to load the specified font
            font = ImageFont.truetype(font_name, size)
        except (OSError, IOError):
            try:
                # Fallback to system default
                font = ImageFont.load_default()
            except:
                # Last resort: create a simple font
                font = ImageFont.load_default()

        self.font_cache[cache_key] = font
        return font

    def _create_mockup_image(self, template_data: Dict, size: Tuple[int, int] = (300, 400)) -> Image.Image:
        """
        Create a mockup preview image from template data.

        Args:
            template_data: Template metadata dictionary
            size: Preview image size (width, height)

        Returns:
            PIL Image object
        """
        # Create base image
        dimensions = template_data.get('dimensions', {})
        template_width = dimensions.get('width', 1000)
        template_height = dimensions.get('height', 1000)

        # Calculate scaling to fit preview size while maintaining aspect ratio
        scale = min(size[0] / template_width, size[1] / template_height)
        preview_width = int(template_width * scale)
        preview_height = int(template_height * scale)

        # Create image with background color
        bg_color = template_data.get('background_color', '#ffffff')
        if bg_color.startswith('#'):
            # Convert hex to RGB
            bg_color = bg_color.lstrip('#')
            bg_color = tuple(int(bg_color[i:i+2], 16) for i in (0, 2, 4))
        else:
            # Use named color or default to white
            color_map = {
                'white': (255, 255, 255),
                'black': (0, 0, 0),
                'gray': (128, 128, 128)
            }
            bg_color = color_map.get(bg_color.lower(), (255, 255, 255))

        img = Image.new('RGB', (preview_width, preview_height), bg_color)
        draw = ImageDraw.Draw(img)

        # Draw layer representations
        layers = template_data.get('layers', [])
        for layer in layers:
            if not layer.get('visible', True):
                continue

            layer_pos = layer.get('position', {})
            layer_x = int(layer_pos.get('x', 0) * scale)
            layer_y = int(layer_pos.get('y', 0) * scale)
            layer_w = int(layer_pos.get('width', 100) * scale)
            layer_h = int(layer_pos.get('height', 100) * scale)

            layer_type = layer.get('type', 'background')
            opacity = layer.get('opacity', 100) / 100.0

            if layer_type == 'text':
                # Draw text placeholder
                font = self._get_font(size=max(12, int(layer_h * 0.8)))
                text = "Sample Text"
                bbox = draw.textbbox((layer_x, layer_y), text, font=font)
                text_color = (100, 100, 100, int(255 * opacity))
                draw.text((layer_x, layer_y), text, fill=text_color, font=font)

            elif layer_type in ['image', 'logo']:
                # Draw image placeholder
                border_color = (200, 200, 200, int(255 * opacity))
                draw.rectangle([layer_x, layer_y, layer_x + layer_w, layer_y + layer_h],
                             outline=border_color, width=2)
                # Add icon indicator
                icon_text = "🖼️" if layer_type == 'image' else "🏷️"
                icon_font = self._get_font(size=max(16, int(layer_h * 0.5)))
                icon_bbox = draw.textbbox((layer_x, layer_y), icon_text, font=icon_font)
                draw.text((layer_x + (layer_w - (icon_bbox[2] - icon_bbox[0])) // 2,
                          layer_y + (layer_h - (icon_bbox[3] - icon_bbox[1])) // 2),
                         icon_text, fill=(150, 150, 150, int(255 * opacity)), font=icon_font)

            elif layer_type == 'shape':
                # Draw shape placeholder
                shape_color = (180, 180, 180, int(255 * opacity))
                draw.rectangle([layer_x, layer_y, layer_x + layer_w, layer_y + layer_h],
                             fill=shape_color)

        # Add template info overlay
        info_font = self._get_font(size=10)
        info_text = f"{template_data.get('name', 'Template')}"
        draw.text((5, 5), info_text, fill=(0, 0, 0, 180), font=info_font)

        category_text = f"Category: {template_data.get('category', 'unknown')}"
        draw.text((5, preview_height - 20), category_text, fill=(0, 0, 0, 180), font=info_font)

        return img

    def _generate_via_comfyui(self, template_data: Dict, workflow_name: Optional[str] = None) -> Optional[Image.Image]:
        """
        Generate preview using ComfyUI workflow.

        Args:
            template_data: Template metadata
            workflow_name: Specific workflow to use

        Returns:
            Generated image or None if failed
        """
        try:
            # This is a placeholder for actual ComfyUI integration
            # In a real implementation, this would:
            # 1. Load the specified workflow
            # 2. Set template parameters
            # 3. Execute the workflow
            # 4. Return the generated image

            print(f"ComfyUI preview generation not yet implemented for workflow: {workflow_name}")
            return None

        except Exception as e:
            print(f"ComfyUI preview generation failed: {e}")
            return None

    def generate_preview(self, template_path: pathlib.Path, output_path: Optional[pathlib.Path] = None,
                        use_comfyui: bool = False, size: Tuple[int, int] = (300, 400)) -> bool:
        """
        Generate a preview image for a template.

        Args:
            template_path: Path to template JSON file
            output_path: Where to save the preview (default: same dir as template with .png extension)
            use_comfyui: Whether to use ComfyUI for realistic preview
            size: Preview image size

        Returns:
            True if successful, False otherwise
        """
        try:
            # Load template data
            with open(template_path, 'r', encoding='utf-8') as f:
                template_data = json.load(f)

            # Determine output path
            if output_path is None:
                output_path = template_path.with_suffix('.png')

            # Generate preview image
            if use_comfyui:
                # Try ComfyUI generation first
                workflow_name = template_data.get('workflow_bindings', {}).get('default_workflow')
                img = self._generate_via_comfyui(template_data, workflow_name)

                if img is None:
                    # Fallback to mockup
                    print("Falling back to mockup preview generation")
                    img = self._create_mockup_image(template_data, size)
            else:
                # Use mockup generation
                img = self._create_mockup_image(template_data, size)

            # Save the image
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, 'PNG')
            print(f"Preview saved to: {output_path}")

            return True

        except Exception as e:
            print(f"Failed to generate preview for {template_path}: {e}")
            return False

    def generate_all_previews(self, templates_dir: pathlib.Path, use_comfyui: bool = False,
                             size: Tuple[int, int] = (300, 400)) -> Dict[str, bool]:
        """
        Generate previews for all templates in the directory.

        Args:
            templates_dir: Root templates directory
            use_comfyui: Whether to use ComfyUI
            size: Preview size

        Returns:
            Dictionary mapping template paths to success status
        """
        results = {}

        # Find all JSON files in category subdirectories
        for category_dir in templates_dir.iterdir():
            if category_dir.is_dir() and not category_dir.name.startswith('.'):
                for template_file in category_dir.glob('*.json'):
                    success = self.generate_preview(template_file, use_comfyui=use_comfyui, size=size)
                    results[str(template_file.relative_to(templates_dir))] = success

        return results


def main():
    """Command-line interface for preview generation."""
    if len(sys.argv) < 2:
        print("Usage: python template_preview_generator.py <templates_dir> [template_file] [--comfyui] [--size WxH]")
        sys.exit(1)

    templates_dir = pathlib.Path(sys.argv[1])
    use_comfyui = '--comfyui' in sys.argv
    size = (300, 400)  # default

    # Parse size argument
    if '--size' in sys.argv:
        size_idx = sys.argv.index('--size')
        if size_idx + 1 < len(sys.argv):
            try:
                w, h = map(int, sys.argv[size_idx + 1].split('x'))
                size = (w, h)
            except ValueError:
                print("Invalid size format. Use WxH (e.g., 300x400)")
                sys.exit(1)

    generator = TemplatePreviewGenerator()

    if len(sys.argv) >= 3 and not sys.argv[2].startswith('--'):
        # Generate single template preview
        template_path = pathlib.Path(sys.argv[2])
        success = generator.generate_preview(template_path, use_comfyui=use_comfyui, size=size)

        if success:
            print(f"✓ Preview generated for {template_path}")
        else:
            print(f"✗ Failed to generate preview for {template_path}")
            sys.exit(1)
    else:
        # Generate all previews
        results = generator.generate_all_previews(templates_dir, use_comfyui=use_comfyui, size=size)

        successful = sum(results.values())
        total = len(results)

        print(f"Generated {successful}/{total} previews")

        if successful < total:
            print("Failed templates:")
            for template, success in results.items():
                if not success:
                    print(f"  - {template}")
            sys.exit(1)


if __name__ == '__main__':
    main()