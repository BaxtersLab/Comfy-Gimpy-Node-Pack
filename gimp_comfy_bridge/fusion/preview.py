"""
Preview thumbnail generation for fusion results.
"""

import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import base64
import io
from PIL import Image, ImageDraw, ImageFont
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)


class PreviewGenerator:
    """Generates preview thumbnails for fusion results."""

    def __init__(self, preview_dir: Optional[Path] = None, max_size: int = 256):
        self.preview_dir = preview_dir or Path("previews")
        self.preview_dir.mkdir(parents=True, exist_ok=True)
        self.max_size = max_size
        self.font = None

        # Try to load a default font
        try:
            # Use default PIL font
            self.font = ImageFont.load_default()
        except Exception:
            self.font = None

    def generate_preview(self,
                        variant: Dict[str, Any],
                        variant_name: str,
                        output_format: str = "png",
                        quality: int = 95) -> Optional[str]:
        """
        Generate a preview thumbnail for a variant.

        Args:
            variant: Variant configuration
            variant_name: Name for the preview file
            output_format: Output format (png, jpg, webp)
            quality: Quality for compressed formats

        Returns:
            Path to generated preview file, or None if failed
        """
        try:
            # Create a placeholder preview image
            preview_image = self._create_placeholder_preview(variant, variant_name)

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            variant_hash = hashlib.md5(str(variant).encode()).hexdigest()[:8]
            filename = f"preview_{variant_name}_{variant_hash}_{timestamp}.{output_format}"
            preview_path = self.preview_dir / filename

            # Save the preview
            if output_format.lower() == "png":
                preview_image.save(preview_path, "PNG")
            elif output_format.lower() == "jpg" or output_format.lower() == "jpeg":
                preview_image.save(preview_path, "JPEG", quality=quality)
            elif output_format.lower() == "webp":
                preview_image.save(preview_path, "WEBP", quality=quality)
            else:
                logger.warning(f"Unsupported format: {output_format}, using PNG")
                preview_image.save(preview_path, "PNG")

            logger.info(f"Generated preview: {preview_path}")
            return str(preview_path)

        except Exception as e:
            logger.error(f"Failed to generate preview for {variant_name}: {e}")
            return None

    def _create_placeholder_preview(self,
                                   variant: Dict[str, Any],
                                   variant_name: str) -> Image.Image:
        """Create a placeholder preview image."""
        # Create a new image with a gradient background
        img = Image.new('RGB', (self.max_size, self.max_size), color='#f0f0f0')
        draw = ImageDraw.Draw(img)

        # Add a subtle gradient
        for y in range(self.max_size):
            r = int(240 + (200 - 240) * (y / self.max_size))
            g = int(240 + (220 - 240) * (y / self.max_size))
            b = int(240 + (240 - 240) * (y / self.max_size))
            draw.line([(0, y), (self.max_size, y)], fill=(r, g, b))

        # Add variant information
        text_lines = [
            f"Variant: {variant_name}",
            f"Template: {variant.get('template_id', 'N/A')}",
            f"Style: {variant.get('style_id', 'N/A')}"
        ]

        if variant.get('brand_kit_id'):
            text_lines.append(f"Brand: {variant['brand_kit_id']}")

        # Draw text
        y_offset = 20
        for line in text_lines:
            if self.font:
                draw.text((10, y_offset), line, fill='#333333', font=self.font)
            else:
                draw.text((10, y_offset), line, fill='#333333')
            y_offset += 20

        # Add a border
        draw.rectangle([0, 0, self.max_size-1, self.max_size-1],
                      outline='#cccccc', width=2)

        # Add some visual elements based on variant properties
        self._add_variant_visual_elements(img, variant)

        return img

    def _add_variant_visual_elements(self, img: Image.Image, variant: Dict[str, Any]):
        """Add visual elements based on variant properties."""
        draw = ImageDraw.Draw(img)
        size = self.max_size

        # Add color swatches if brand kit colors are available
        brand_colors = variant.get('brand_colors', [])
        if brand_colors:
            swatch_size = 20
            for i, color in enumerate(brand_colors[:4]):  # Max 4 swatches
                try:
                    x = size - (i + 1) * (swatch_size + 5) - 5
                    y = size - swatch_size - 5
                    draw.rectangle([x, y, x + swatch_size, y + swatch_size],
                                 fill=color, outline='#666666')
                except Exception:
                    continue

        # Add style indicators
        style_params = variant.get('style_parameters', {})
        if style_params.get('color_temperature_shift', 0) > 0:
            # Warm color indicator
            draw.ellipse([size-30, 10, size-10, 30], fill='#FF6B35', outline='#333333')
        elif style_params.get('color_temperature_shift', 0) < 0:
            # Cool color indicator
            draw.ellipse([size-30, 10, size-10, 30], fill='#4A90E2', outline='#333333')

        # Add LoRA indicator
        if variant.get('loras'):
            draw.rectangle([10, size-15, 25, size-5], fill='#9C27B0', outline='#333333')

    def generate_batch_previews(self,
                               variants: List[Dict[str, Any]],
                               batch_name: str,
                               output_format: str = "png",
                               quality: int = 95) -> List[str]:
        """
        Generate previews for a batch of variants.

        Args:
            variants: List of variant configurations
            batch_name: Name for the batch
            output_format: Output format
            quality: Quality setting

        Returns:
            List of preview file paths
        """
        preview_urls = []

        for i, variant in enumerate(variants):
            variant_name = f"{batch_name}_{i+1:03d}"
            preview_url = self.generate_preview(
                variant, variant_name, output_format, quality
            )
            if preview_url:
                preview_urls.append(preview_url)

        logger.info(f"Generated {len(preview_urls)} batch previews for {batch_name}")
        return preview_urls

    def get_preview_base64(self, preview_path: str) -> Optional[str]:
        """
        Get preview image as base64 string.

        Args:
            preview_path: Path to preview file

        Returns:
            Base64 encoded image data
        """
        try:
            with open(preview_path, 'rb') as f:
                image_data = f.read()
                return base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encode preview {preview_path}: {e}")
            return None

    def cleanup_old_previews(self, max_age_days: int = 7):
        """
        Clean up old preview files.

        Args:
            max_age_days: Maximum age in days
        """
        import time
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 60 * 60

        cleaned_count = 0
        for preview_file in self.preview_dir.glob("*"):
            if preview_file.is_file():
                file_age = current_time - preview_file.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        preview_file.unlink()
                        cleaned_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to remove old preview {preview_file}: {e}")

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old preview files")

    def get_preview_stats(self) -> Dict[str, Any]:
        """Get statistics about stored previews."""
        stats = {
            "total_files": 0,
            "total_size_mb": 0.0,
            "formats": {},
            "oldest_file": None,
            "newest_file": None
        }

        import time
        current_time = time.time()

        for preview_file in self.preview_dir.glob("*"):
            if preview_file.is_file():
                stats["total_files"] += 1

                # File size
                size_mb = preview_file.stat().st_size / (1024 * 1024)
                stats["total_size_mb"] += size_mb

                # Format count
                ext = preview_file.suffix.lower()
                stats["formats"][ext] = stats["formats"].get(ext, 0) + 1

                # Age tracking
                mtime = preview_file.stat().st_mtime
                if stats["oldest_file"] is None or mtime < stats["oldest_file"][1]:
                    stats["oldest_file"] = (str(preview_file), mtime)
                if stats["newest_file"] is None or mtime > stats["newest_file"][1]:
                    stats["newest_file"] = (str(preview_file), mtime)

        # Convert timestamps to readable format
        if stats["oldest_file"]:
            stats["oldest_file"] = (
                stats["oldest_file"][0],
                time.ctime(stats["oldest_file"][1])
            )
        if stats["newest_file"]:
            stats["newest_file"] = (
                stats["newest_file"][0],
                time.ctime(stats["newest_file"][1])
            )

        return stats