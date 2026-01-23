"""
Execution Result Processor - Phase 9
Processes and delivers ComfyUI execution results with format conversion and optimization.
"""

import asyncio
import logging
import base64
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from PIL import Image
import numpy as np

from shared.config import get_config
from shared.types import ExecutionResult, ProcessedOutput
from gimp_comfy_bridge.execution.engine import ExecutionJob

logger = logging.getLogger(__name__)


@dataclass
class ProcessingOptions:
    """Options for result processing."""
    output_formats: List[str] = field(default_factory=lambda: ["png"])
    quality: int = 95
    max_dimension: Optional[int] = None  # Maximum width/height for resizing
    enable_compression: bool = True
    generate_thumbnails: bool = True
    thumbnail_size: tuple = (256, 256)
    save_to_disk: bool = True
    output_directory: Optional[Path] = None
    metadata_extraction: bool = True
    format_optimization: bool = True


@dataclass
class ProcessedResult:
    """Processed execution result with multiple formats."""
    job_id: str
    success: bool
    outputs: List[ProcessedOutput] = field(default_factory=list)
    thumbnails: List[bytes] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time: float = 0.0
    file_paths: List[Path] = field(default_factory=list)
    error_message: Optional[str] = None


class ResultProcessor:
    """Processes ComfyUI execution results into usable formats."""

    def __init__(self):
        self.config = get_config()
        self.output_dir = self.config.data_dir / "execution_outputs"
        self.output_dir.mkdir(exist_ok=True)

    async def process_job_result(
        self,
        job: ExecutionJob,
        options: Optional[ProcessingOptions] = None
    ) -> ProcessedResult:
        """Process the result of an execution job."""

        start_time = asyncio.get_event_loop().time()
        options = options or ProcessingOptions()

        if not job.result or not job.result.success:
            return ProcessedResult(
                job_id=job.job_id,
                success=False,
                error_message=job.error_message or "No execution result available"
            )

        try:
            processed_outputs = []
            thumbnails = []
            file_paths = []

            # Process each output from the execution result
            for output_key, output_data in job.result.outputs.items():
                processed = await self._process_output(
                    output_key, output_data, options
                )
                if processed:
                    processed_outputs.append(processed)

                    # Generate thumbnail if requested
                    if options.generate_thumbnails:
                        thumbnail = await self._generate_thumbnail(
                            processed, options.thumbnail_size
                        )
                        if thumbnail:
                            thumbnails.append(thumbnail)

                    # Save to disk if requested
                    if options.save_to_disk:
                        file_path = await self._save_output(processed, options)
                        if file_path:
                            file_paths.append(file_path)

            # Extract metadata
            metadata = {}
            if options.metadata_extraction:
                metadata = await self._extract_metadata(job, processed_outputs)

            processing_time = asyncio.get_event_loop().time() - start_time

            return ProcessedResult(
                job_id=job.job_id,
                success=True,
                outputs=processed_outputs,
                thumbnails=thumbnails,
                metadata=metadata,
                processing_time=processing_time,
                file_paths=file_paths
            )

        except Exception as e:
            logger.error(f"Failed to process job result {job.job_id}: {e}")
            processing_time = asyncio.get_event_loop().time() - start_time

            return ProcessedResult(
                job_id=job.job_id,
                success=False,
                error_message=str(e),
                processing_time=processing_time
            )

    async def _process_output(
        self,
        output_key: str,
        output_data: Any,
        options: ProcessingOptions
    ) -> Optional[ProcessedOutput]:
        """Process a single output from execution results."""

        try:
            # Handle different output types
            if self._is_image_output(output_data):
                return await self._process_image_output(
                    output_key, output_data, options
                )
            elif self._is_video_output(output_data):
                return await self._process_video_output(
                    output_key, output_data, options
                )
            elif self._is_text_output(output_data):
                return await self._process_text_output(
                    output_key, output_data, options
                )
            else:
                # Generic output processing
                return await self._process_generic_output(
                    output_key, output_data, options
                )

        except Exception as e:
            logger.error(f"Failed to process output {output_key}: {e}")
            return None

    def _is_image_output(self, output_data: Any) -> bool:
        """Check if output data represents an image."""
        if isinstance(output_data, list) and len(output_data) > 0:
            item = output_data[0]
            # Check for ComfyUI image format (dict with filename, subfolder, type)
            if isinstance(item, dict) and "filename" in item:
                return True
        return False

    def _is_video_output(self, output_data: Any) -> bool:
        """Check if output data represents a video."""
        # Video detection logic would go here
        return False

    def _is_text_output(self, output_data: Any) -> bool:
        """Check if output data represents text."""
        return isinstance(output_data, str)

    async def _process_image_output(
        self,
        output_key: str,
        output_data: List[Dict[str, Any]],
        options: ProcessingOptions
    ) -> Optional[ProcessedOutput]:
        """Process image output from ComfyUI."""

        processed_images = []

        for image_data in output_data:
            try:
                # Load image from ComfyUI output directory
                image_path = self._get_comfyui_output_path(image_data)
                if not image_path.exists():
                    logger.warning(f"Image file not found: {image_path}")
                    continue

                # Open and process image
                with Image.open(image_path) as img:
                    # Convert to RGB if necessary
                    if img.mode not in ("RGB", "RGBA"):
                        img = img.convert("RGB")

                    # Resize if max_dimension specified
                    if options.max_dimension:
                        img.thumbnail(
                            (options.max_dimension, options.max_dimension),
                            Image.Resampling.LANCZOS
                        )

                    # Convert to requested formats
                    for fmt in options.output_formats:
                        if fmt.lower() == "png":
                            buffer = io.BytesIO()
                            img.save(buffer, format="PNG", optimize=options.enable_compression)
                            processed_images.append({
                                "format": "png",
                                "data": buffer.getvalue(),
                                "metadata": {
                                    "width": img.width,
                                    "height": img.height,
                                    "mode": img.mode
                                }
                            })
                        elif fmt.lower() == "jpg" or fmt.lower() == "jpeg":
                            buffer = io.BytesIO()
                            img.save(buffer, format="JPEG",
                                   quality=options.quality,
                                   optimize=options.enable_compression)
                            processed_images.append({
                                "format": "jpg",
                                "data": buffer.getvalue(),
                                "metadata": {
                                    "width": img.width,
                                    "height": img.height,
                                    "mode": img.mode
                                }
                            })
                        elif fmt.lower() == "webp":
                            buffer = io.BytesIO()
                            img.save(buffer, format="WebP",
                                   quality=options.quality,
                                   lossless=False)
                            processed_images.append({
                                "format": "webp",
                                "data": buffer.getvalue(),
                                "metadata": {
                                    "width": img.width,
                                    "height": img.height,
                                    "mode": img.mode
                                }
                            })

            except Exception as e:
                logger.error(f"Failed to process image {image_data}: {e}")
                continue

        if processed_images:
            return ProcessedOutput(
                key=output_key,
                type="image",
                data=processed_images,
                metadata={
                    "count": len(processed_images),
                    "formats": list(set(img["format"] for img in processed_images))
                }
            )

        return None

    async def _process_video_output(
        self,
        output_key: str,
        output_data: Any,
        options: ProcessingOptions
    ) -> Optional[ProcessedOutput]:
        """Process video output (placeholder for future implementation)."""
        # Video processing would be implemented here
        return ProcessedOutput(
            key=output_key,
            type="video",
            data=output_data,
            metadata={"note": "Video processing not yet implemented"}
        )

    async def _process_text_output(
        self,
        output_key: str,
        output_data: str,
        options: ProcessingOptions
    ) -> Optional[ProcessedOutput]:
        """Process text output."""
        return ProcessedOutput(
            key=output_key,
            type="text",
            data=output_data,
            metadata={"length": len(output_data)}
        )

    async def _process_generic_output(
        self,
        output_key: str,
        output_data: Any,
        options: ProcessingOptions
    ) -> Optional[ProcessedOutput]:
        """Process generic output."""
        return ProcessedOutput(
            key=output_key,
            type="generic",
            data=output_data,
            metadata={"type": str(type(output_data))}
        )

    async def _generate_thumbnail(
        self,
        processed_output: ProcessedOutput,
        size: tuple
    ) -> Optional[bytes]:
        """Generate a thumbnail from processed output."""

        if processed_output.type != "image" or not processed_output.data:
            return None

        try:
            # Get the first image data
            image_data = processed_output.data[0]
            if isinstance(image_data, dict) and "data" in image_data:
                img_bytes = image_data["data"]
            else:
                return None

            # Open image and create thumbnail
            with Image.open(io.BytesIO(img_bytes)) as img:
                # Convert to RGB for thumbnail
                if img.mode != "RGB":
                    img = img.convert("RGB")

                # Create thumbnail
                img.thumbnail(size, Image.Resampling.LANCZOS)

                # Save as PNG
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                return buffer.getvalue()

        except Exception as e:
            logger.error(f"Failed to generate thumbnail: {e}")
            return None

    async def _save_output(
        self,
        processed_output: ProcessedOutput,
        options: ProcessingOptions
    ) -> Optional[Path]:
        """Save processed output to disk."""

        try:
            output_dir = options.output_directory or self.output_dir
            output_dir.mkdir(exist_ok=True)

            if processed_output.type == "image" and processed_output.data:
                # Save the first format available
                image_data = processed_output.data[0]
                if isinstance(image_data, dict) and "data" in image_data:
                    fmt = image_data.get("format", "png")
                    filename = f"{processed_output.key}.{fmt}"
                    file_path = output_dir / filename

                    with open(file_path, "wb") as f:
                        f.write(image_data["data"])

                    return file_path

            elif processed_output.type == "text" and isinstance(processed_output.data, str):
                filename = f"{processed_output.key}.txt"
                file_path = output_dir / filename

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(processed_output.data)

                return file_path

        except Exception as e:
            logger.error(f"Failed to save output {processed_output.key}: {e}")

        return None

    async def _extract_metadata(
        self,
        job: ExecutionJob,
        processed_outputs: List[ProcessedOutput]
    ) -> Dict[str, Any]:
        """Extract metadata from job and outputs."""

        metadata = {
            "job_id": job.job_id,
            "execution_time": job.result.execution_time if job.result else 0,
            "output_count": len(processed_outputs),
            "output_types": list(set(out.type for out in processed_outputs))
        }

        # Add fusion metadata if available
        if job.fusion_result:
            metadata["fusion_id"] = job.fusion_result.id
            metadata["variant_count"] = len(job.fusion_result.variants)
            metadata["lora_weights"] = job.fusion_result.lora_weights

        # Add ComfyUI-specific metadata
        if job.result and hasattr(job.result, 'metadata'):
            comfy_metadata = job.result.metadata.get("comfyui_history", {})
            if "status" in comfy_metadata:
                metadata["comfyui_status"] = comfy_metadata["status"]

        return metadata

    def _get_comfyui_output_path(self, image_data: Dict[str, Any]) -> Path:
        """Get the full path to a ComfyUI output file."""
        # This assumes ComfyUI's default output directory structure
        # In practice, this would need to be configured based on ComfyUI settings
        comfyui_output_dir = Path(self.config.get("comfyui_output_dir", "ComfyUI/output"))

        filename = image_data.get("filename", "")
        subfolder = image_data.get("subfolder", "")
        output_type = image_data.get("type", "output")

        if subfolder:
            return comfyui_output_dir / subfolder / filename
        else:
            return comfyui_output_dir / filename


class BatchProcessor:
    """Processes multiple execution results in batch."""

    def __init__(self):
        self.processor = ResultProcessor()

    async def process_batch(
        self,
        jobs: List[ExecutionJob],
        options: Optional[ProcessingOptions] = None
    ) -> List[ProcessedResult]:
        """Process multiple jobs in batch."""

        tasks = [
            self.processor.process_job_result(job, options)
            for job in jobs
        ]

        return await asyncio.gather(*tasks, return_exceptions=True)

    async def process_fusion_batch(
        self,
        fusion_result: 'FusionResult',
        jobs: List[ExecutionJob],
        options: Optional[ProcessingOptions] = None
    ) -> Dict[str, Any]:
        """Process a batch of fusion results with correlation."""

        # Process all jobs
        results = await self.process_batch(jobs, options)

        # Correlate with fusion variants
        variant_results = {}
        for i, (variant, result) in enumerate(zip(fusion_result.variants, results)):
            if isinstance(result, Exception):
                variant_results[variant.id] = {
                    "success": False,
                    "error": str(result)
                }
            else:
                variant_results[variant.id] = {
                    "success": result.success,
                    "outputs": len(result.outputs) if result.outputs else 0,
                    "processing_time": result.processing_time,
                    "file_paths": [str(p) for p in result.file_paths]
                }

        return {
            "fusion_id": fusion_result.id,
            "total_variants": len(fusion_result.variants),
            "processed_variants": len([r for r in results if not isinstance(r, Exception) and r.success]),
            "variant_results": variant_results,
            "batch_metadata": {
                "processing_options": options.__dict__ if options else None,
                "total_processing_time": sum(r.processing_time for r in results
                                          if not isinstance(r, Exception))
            }
        }


# Convenience functions
async def process_execution_result(
    job: ExecutionJob,
    options: Optional[ProcessingOptions] = None
) -> ProcessedResult:
    """Process a single execution result (convenience function)."""
    processor = ResultProcessor()
    return await processor.process_job_result(job, options)


async def process_batch_results(
    jobs: List[ExecutionJob],
    options: Optional[ProcessingOptions] = None
) -> List[ProcessedResult]:
    """Process multiple execution results (convenience function)."""
    processor = BatchProcessor()
    return await processor.process_batch(jobs, options)