"""
Brand Kit API endpoints for web interface.
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Dict, Any, Optional
import asyncio

from ..brandkit import (
    load_brandkit, save_brandkit, list_brandkits,
    BrandKit, BrandKitApplier, BrandKitValidator
)
from ..shared.config import Config

logger = logging.getLogger(__name__)

# Create blueprint
brandkit_bp = Blueprint('brandkit', __name__, url_prefix='/api/brandkit')

# Global instances
_config = Config()
_validator = BrandKitValidator()
_applier = BrandKitApplier()


@brandkit_bp.route('/list', methods=['GET'])
def list_brand_kits():
    """List all available brand kits."""
    try:
        kits = list_brandkits()
        return jsonify({
            "success": True,
            "brand_kits": kits
        }), 200
    except Exception as e:
        logger.error(f"Failed to list brand kits: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@brandkit_bp.route('/load/<kit_id>', methods=['GET'])
def load_brand_kit(kit_id: str):
    """Load a specific brand kit."""
    try:
        kit = load_brandkit(kit_id)
        if not kit:
            return jsonify({
                "success": False,
                "error": f"Brand kit '{kit_id}' not found"
            }), 404

        return jsonify({
            "success": True,
            "brand_kit": kit.to_dict()
        }), 200
    except Exception as e:
        logger.error(f"Failed to load brand kit '{kit_id}': {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@brandkit_bp.route('/save', methods=['POST'])
def save_brand_kit():
    """Save a brand kit."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400

        # Create BrandKit from data
        kit_data = data.get('brand_kit', {})
        kit = BrandKit.from_dict(kit_data)

        # Validate
        validation = _validator.validate_brand_kit(kit)
        if not validation.valid:
            return jsonify({
                "success": False,
                "error": "Validation failed",
                "validation_errors": validation.errors
            }), 400

        # Save
        success = save_brandkit(kit)
        if not success:
            return jsonify({
                "success": False,
                "error": "Failed to save brand kit"
            }), 500

        return jsonify({
            "success": True,
            "message": f"Brand kit '{kit.id}' saved successfully"
        }), 200

    except Exception as e:
        logger.error(f"Failed to save brand kit: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@brandkit_bp.route('/validate', methods=['POST'])
def validate_brand_kit():
    """Validate a brand kit."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400

        kit_data = data.get('brand_kit', {})
        kit = BrandKit.from_dict(kit_data)

        validation = _validator.validate_brand_kit(kit)

        return jsonify({
            "success": True,
            "valid": validation.valid,
            "errors": validation.errors,
            "warnings": validation.warnings
        }), 200

    except Exception as e:
        logger.error(f"Failed to validate brand kit: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@brandkit_bp.route('/preview/<kit_id>', methods=['GET'])
def generate_preview(kit_id: str):
    """Generate a preview image for a brand kit."""
    try:
        from ..brandkit.preview import generate_brand_kit_preview
        import tempfile
        from pathlib import Path

        kit = load_brandkit(kit_id)
        if not kit:
            return jsonify({
                "success": False,
                "error": f"Brand kit '{kit_id}' not found"
            }), 404

        # Generate preview
        with tempfile.TemporaryDirectory() as temp_dir:
            preview_path = generate_brand_kit_preview(kit, Path(temp_dir) / f"{kit_id}_preview.png")

            if preview_path.exists():
                # Return preview image
                from flask import send_file
                return send_file(preview_path, mimetype='image/png')
            else:
                return jsonify({
                    "success": False,
                    "error": "Failed to generate preview"
                }), 500

    except Exception as e:
        logger.error(f"Failed to generate preview for brand kit '{kit_id}': {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@brandkit_bp.route('/apply', methods=['POST'])
async def apply_brand_kit():
    """Apply a brand kit to content."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400

        kit_id = data.get('brand_kit_id')
        content_type = data.get('content_type')  # 'template', 'style', 'workflow'
        content = data.get('content', {})

        if not kit_id or not content_type:
            return jsonify({
                "success": False,
                "error": "brand_kit_id and content_type are required"
            }), 400

        kit = load_brandkit(kit_id)
        if not kit:
            return jsonify({
                "success": False,
                "error": f"Brand kit '{kit_id}' not found"
            }), 404

        # Apply brand kit based on content type
        result = {}
        if content_type == 'template':
            # Apply to template
            result = await _applier.apply_to_template(content, kit)
        elif content_type == 'style':
            # Apply to style
            result = await _applier.apply_to_style(content, kit)
        elif content_type == 'workflow':
            # Apply to workflow (would need NodeGraph)
            return jsonify({
                "success": False,
                "error": "Workflow application requires NodeGraph object"
            }), 400
        else:
            return jsonify({
                "success": False,
                "error": f"Unsupported content type: {content_type}"
            }), 400

        return jsonify({
            "success": True,
            "result": result
        }), 200

    except Exception as e:
        logger.error(f"Failed to apply brand kit: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@brandkit_bp.route('/create', methods=['POST'])
def create_brand_kit():
    """Create a new brand kit from parameters."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400

        kit_id = data.get('id')
        name = data.get('name')
        description = data.get('description', '')

        if not kit_id or not name:
            return jsonify({
                "success": False,
                "error": "id and name are required"
            }), 400

        # Create basic brand kit
        kit = BrandKit(
            id=kit_id,
            name=name,
            description=description,
            colors={},
            fonts={},
            styles={},
            workflows={}
        )

        # Add optional data
        if 'colors' in data:
            kit.colors = data['colors']
        if 'fonts' in data:
            kit.fonts = data['fonts']
        if 'styles' in data:
            kit.styles = data['styles']
        if 'workflows' in data:
            kit.workflows = data['workflows']

        # Validate and save
        validation = _validator.validate_brand_kit(kit)
        if not validation.valid:
            return jsonify({
                "success": False,
                "error": "Validation failed",
                "validation_errors": validation.errors
            }), 400

        success = save_brandkit(kit)
        if not success:
            return jsonify({
                "success": False,
                "error": "Failed to save brand kit"
            }), 500

        return jsonify({
            "success": True,
            "brand_kit": kit.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Failed to create brand kit: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@brandkit_bp.route('/delete/<kit_id>', methods=['DELETE'])
def delete_brand_kit(kit_id: str):
    """Delete a brand kit."""
    try:
        # For now, just return not implemented
        # In a full implementation, this would delete from storage
        return jsonify({
            "success": False,
            "error": "Delete operation not yet implemented"
        }), 501

    except Exception as e:
        logger.error(f"Failed to delete brand kit '{kit_id}': {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500