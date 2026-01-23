"""
Template generation API endpoints for Comfy Gimpy Studio.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from ...fusion.engine import initialize_fusion_engine
from ...shared.types import TemplateGenerationRequest, TemplateGenerationOptions, TemplateGenerationResult
from ...shared.config import load_config

logger = logging.getLogger(__name__)

# Create blueprint
templates_bp = Blueprint('templates', __name__, url_prefix='/api/templates')

# Initialize fusion engine
fusion_engine = initialize_fusion_engine()
config = load_config()


@templates_bp.route('/generate', methods=['POST'])
async def generate_template():
    """
    Generate a new template using AI assistance.

    Request JSON:
    {
        "method": "prompt|image|workflow|enhancement",
        "prompt": "Template description (for prompt method)",
        "image_path": "Path to reference image (for image method)",
        "workflow_data": {...} (for workflow method),
        "base_template": {...} (for enhancement method),
        "options": {
            "category": "poster|brochure|website|etc.",
            "generate_variants": true,
            "variant_count": 3,
            "style_references": ["style_id1", "style_id2"],
            "brand_kit_id": "brand_kit_id",
            "output_format": "xcf",
            "include_previews": true,
            "quality": 95
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        # Validate request
        if "method" not in data:
            return jsonify({"error": "Method is required"}), 400

        method = data["method"]
        if method not in ["prompt", "image", "workflow", "enhancement"]:
            return jsonify({"error": f"Invalid method: {method}"}), 400

        # Create generation request
        gen_request = TemplateGenerationRequest(
            method=method,
            prompt=data.get("prompt"),
            image_path=data.get("image_path"),
            workflow_data=data.get("workflow_data"),
            base_template=data.get("base_template"),
            options=TemplateGenerationOptions(**data.get("options", {}))
        )

        # Validate method-specific requirements
        if method == "prompt" and not gen_request.prompt:
            return jsonify({"error": "Prompt is required for prompt method"}), 400
        elif method == "image" and not gen_request.image_path:
            return jsonify({"error": "Image path is required for image method"}), 400
        elif method == "workflow" and not gen_request.workflow_data:
            return jsonify({"error": "Workflow data is required for workflow method"}), 400
        elif method == "enhancement" and not gen_request.base_template:
            return jsonify({"error": "Base template is required for enhancement method"}), 400

        start_time = datetime.now()

        # Generate template based on method
        if method == "prompt":
            template = await fusion_engine.generate_template_from_prompt(
                prompt=gen_request.prompt,
                category=gen_request.options.category,
                style_references=gen_request.options.style_references,
                brand_kit_id=gen_request.options.brand_kit_id,
                generate_variants=gen_request.options.generate_variants,
                variant_count=gen_request.options.variant_count
            )
        elif method == "image":
            template = await fusion_engine.generate_template_from_image(
                image_path=gen_request.image_path,
                category=gen_request.options.category,
                generate_variants=gen_request.options.generate_variants,
                variant_count=gen_request.options.variant_count
            )
        elif method == "workflow":
            template = await fusion_engine.generate_template_from_workflow(
                workflow_data=gen_request.workflow_data,
                category=gen_request.options.category,
                generate_variants=gen_request.options.generate_variants,
                variant_count=gen_request.options.variant_count
            )
        elif method == "enhancement":
            template = await fusion_engine.enhance_template_with_ai(
                template=gen_request.base_template,
                enhancement_prompt=gen_request.prompt or "Enhance this template",
                generate_variants=gen_request.options.generate_variants,
                variant_count=gen_request.options.variant_count
            )

        # Save template if requested
        saved_path = None
        if request.args.get("save", "false").lower() == "true":
            saved_path = await fusion_engine.save_generated_template(
                template=template,
                output_dir=str(config.templates_dir)
            )

        # Calculate generation time
        generation_time = (datetime.now() - start_time).total_seconds()

        # Create result
        result = TemplateGenerationResult(
            template=template,
            variants=template.get("variants", []),
            preview_urls=template.get("previews", {}).get("urls"),
            saved_path=saved_path,
            generation_time=generation_time,
            success=True
        )

        logger.info(f"Template generated successfully: {template.get('id', 'unknown')} in {generation_time:.2f}s")

        return jsonify({
            "success": True,
            "template": result.template,
            "variants": result.variants,
            "preview_urls": result.preview_urls,
            "saved_path": result.saved_path,
            "generation_time": result.generation_time
        })

    except Exception as e:
        logger.error(f"Template generation failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "generation_time": (datetime.now() - start_time).total_seconds() if 'start_time' in locals() else 0
        }), 500


@templates_bp.route('/upload-image', methods=['POST'])
def upload_image():
    """
    Upload an image for template generation.

    Returns temporary path for use in generation requests.
    """
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "No image selected"}), 400

        # Validate file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'webp', 'gif', 'bmp'}
        if not file.filename.lower().endswith(tuple('.' + ext for ext in allowed_extensions)):
            return jsonify({"error": "Invalid image format"}), 400

        # Secure filename and save
        filename = secure_filename(file.filename)
        temp_path = config.get_safe_temp_dir() / f"template_gen_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        file.save(str(temp_path))

        logger.info(f"Image uploaded for template generation: {temp_path}")

        return jsonify({
            "success": True,
            "image_path": str(temp_path),
            "filename": filename
        })

    except Exception as e:
        logger.error(f"Image upload failed: {e}")
        return jsonify({"error": str(e)}), 500


@templates_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get supported template categories."""
    try:
        categories = fusion_engine.get_supported_template_categories()
        return jsonify({
            "success": True,
            "categories": categories
        })
    except Exception as e:
        logger.error(f"Failed to get categories: {e}")
        return jsonify({"error": str(e)}), 500


@templates_bp.route('/capabilities', methods=['GET'])
def get_capabilities():
    """Get template generation capabilities."""
    try:
        capabilities = fusion_engine.get_template_generation_capabilities()
        return jsonify({
            "success": True,
            "capabilities": capabilities
        })
    except Exception as e:
        logger.error(f"Failed to get capabilities: {e}")
        return jsonify({"error": str(e)}), 500


@templates_bp.route('/save/<template_id>', methods=['POST'])
async def save_template(template_id: str):
    """
    Save a generated template to disk.

    Request JSON:
    {
        "template": {...},
        "output_dir": "/path/to/output" (optional)
    }
    """
    try:
        data = request.get_json()
        if not data or "template" not in data:
            return jsonify({"error": "Template data is required"}), 400

        template = data["template"]
        output_dir = data.get("output_dir", str(config.templates_dir))

        saved_path = await fusion_engine.save_generated_template(
            template=template,
            output_dir=output_dir
        )

        logger.info(f"Template saved: {template_id} -> {saved_path}")

        return jsonify({
            "success": True,
            "saved_path": saved_path,
            "template_id": template_id
        })

    except Exception as e:
        logger.error(f"Template save failed: {e}")
        return jsonify({"error": str(e)}), 500


@templates_bp.route('/list-generated', methods=['GET'])
def list_generated_templates():
    """List all generated templates."""
    try:
        generated_dir = config.templates_dir / "generated"
        if not generated_dir.exists():
            return jsonify({
                "success": True,
                "templates": []
            })

        templates = []
        for template_dir in generated_dir.iterdir():
            if template_dir.is_dir():
                metadata_file = template_dir / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        templates.append({
                            "id": metadata.get("id"),
                            "name": metadata.get("name"),
                            "category": metadata.get("category"),
                            "created_at": metadata.get("created_at"),
                            "path": str(template_dir)
                        })
                    except Exception as e:
                        logger.warning(f"Failed to read metadata for {template_dir}: {e}")

        return jsonify({
            "success": True,
            "templates": templates
        })

    except Exception as e:
        logger.error(f"Failed to list generated templates: {e}")
        return jsonify({"error": str(e)}), 500


@templates_bp.route('/delete/<template_id>', methods=['DELETE'])
def delete_generated_template(template_id: str):
    """Delete a generated template."""
    try:
        generated_dir = config.templates_dir / "generated"
        template_dir = generated_dir / template_id

        if not template_dir.exists():
            return jsonify({"error": "Template not found"}), 404

        # Remove directory and all contents
        import shutil
        shutil.rmtree(template_dir)

        logger.info(f"Template deleted: {template_id}")

        return jsonify({
            "success": True,
            "template_id": template_id
        })

    except Exception as e:
        logger.error(f"Template deletion failed: {e}")
        return jsonify({"error": str(e)}), 500