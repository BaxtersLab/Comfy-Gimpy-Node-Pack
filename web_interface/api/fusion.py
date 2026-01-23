"""
Fusion API endpoints for web interface.
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Dict, Any, Optional

from gimp_comfy_bridge.fusion import (
    initialize_fusion_engine,
    fuse
)
from gimp_comfy_bridge.fusion.brandkits import BrandKitManager
from gimp_comfy_bridge.fusion.engine import FusionOptions
from gimp_comfy_bridge.fusion.preview import PreviewGenerator

logger = logging.getLogger(__name__)

# Create blueprint
fusion_bp = Blueprint('fusion', __name__, url_prefix='/api/fusion')

# Global instances
_fusion_engine = None
_brand_kit_manager = None
_preview_generator = None


def initialize_fusion_api():
    """Initialize fusion API components."""
    global _fusion_engine, _brand_kit_manager, _preview_generator

    if _fusion_engine is None:
        _fusion_engine = initialize_fusion_engine()
        _brand_kit_manager = BrandKitManager()
        _preview_generator = PreviewGenerator()
        logger.info("Fusion API initialized")


@fusion_bp.route('/fuse', methods=['POST'])
def fuse_template_style():
    """
    Fuse a template with a style to generate variants.

    POST /api/fusion/fuse
    {
        "template_id": "string",
        "style_id": "string",
        "brand_kit_id": "string (optional)",
        "variant_count": 1,
        "lora_weights": {"lora1": 0.5, "lora2": 0.3},
        "style_mix_ratios": {"style1": 0.7, "style2": 0.3},
        "randomness_seed": 42,
        "generate_previews": true,
        "output_format": "png",
        "quality": 95
    }
    """
    try:
        initialize_fusion_api()

        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        # Validate required fields
        template_id = data.get('template_id')
        style_id = data.get('style_id')

        if not template_id or not style_id:
            return jsonify({"error": "template_id and style_id are required"}), 400

        # Load template and style (simplified - in real implementation would use registries)
        template = {"id": template_id, "name": f"Template {template_id}", "layout": {}}
        style = {"id": style_id, "name": f"Style {style_id}", "positive_prompt": "default prompt"}

        # Create fusion options
        options = FusionOptions(
            lora_weights=data.get('lora_weights'),
            style_mix_ratios=data.get('style_mix_ratios'),
            brand_kit_id=data.get('brand_kit_id'),
            variant_count=data.get('variant_count', 1),
            randomness_seed=data.get('randomness_seed'),
            generate_previews=data.get('generate_previews', True),
            output_format=data.get('output_format', 'png'),
            quality=data.get('quality', 95)
        )

        # Perform fusion
        result = _fusion_engine.fuse(template, style, options)

        # Convert result to dict for JSON response
        response_data = {
            "task_id": result.task_id,
            "variant_count": len(result.variants),
            "variants": result.variants,
            "preview_urls": result.preview_urls,
            "brand_kit_applied": result.brand_kit_applied,
            "created_at": result.created_at.isoformat() if result.created_at else None
        }

        logger.info(f"Fusion completed: {result.task_id} with {len(result.variants)} variants")
        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Fusion failed: {e}")
        return jsonify({"error": str(e)}), 500


@fusion_bp.route('/brand-kits', methods=['GET'])
def list_brand_kits():
    """Get list of available brand kits."""
    try:
        initialize_fusion_api()
        kits = _brand_kit_manager.list_brand_kits()
        return jsonify({"brand_kits": kits}), 200
    except Exception as e:
        logger.error(f"Failed to list brand kits: {e}")
        return jsonify({"error": str(e)}), 500


@fusion_bp.route('/brand-kits', methods=['POST'])
def create_brand_kit():
    """Create a new brand kit."""
    try:
        initialize_fusion_api()

        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        kit_id = data.get('id')
        name = data.get('name')
        description = data.get('description', '')

        if not kit_id or not name:
            return jsonify({"error": "id and name are required"}), 400

        kit = _brand_kit_manager.create_brand_kit_template(kit_id, name, description)
        success = _brand_kit_manager.save_brand_kit(kit)

        if success:
            return jsonify({"message": "Brand kit created", "kit": kit.to_dict()}), 201
        else:
            return jsonify({"error": "Failed to save brand kit"}), 500

    except Exception as e:
        logger.error(f"Failed to create brand kit: {e}")
        return jsonify({"error": str(e)}), 500


@fusion_bp.route('/brand-kits/<kit_id>', methods=['GET'])
def get_brand_kit(kit_id: str):
    """Get a specific brand kit."""
    try:
        initialize_fusion_api()
        kit = _brand_kit_manager.load_brand_kit(kit_id)

        if kit:
            return jsonify(kit.to_dict()), 200
        else:
            return jsonify({"error": "Brand kit not found"}), 404

    except Exception as e:
        logger.error(f"Failed to get brand kit {kit_id}: {e}")
        return jsonify({"error": str(e)}), 500


@fusion_bp.route('/previews/stats', methods=['GET'])
def get_preview_stats():
    """Get preview generation statistics."""
    try:
        initialize_fusion_api()
        stats = _preview_generator.get_preview_stats()
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Failed to get preview stats: {e}")
        return jsonify({"error": str(e)}), 500


@fusion_bp.route('/previews/cleanup', methods=['POST'])
def cleanup_previews():
    """Clean up old preview files."""
    try:
        initialize_fusion_api()

        data = request.get_json() or {}
        max_age_days = data.get('max_age_days', 7)

        _preview_generator.cleanup_old_previews(max_age_days)
        return jsonify({"message": f"Cleaned up previews older than {max_age_days} days"}), 200

    except Exception as e:
        logger.error(f"Failed to cleanup previews: {e}")
        return jsonify({"error": str(e)}), 500


@fusion_bp.route('/variants/stats', methods=['POST'])
def get_variant_stats():
    """Get statistics about generated variants."""
    try:
        initialize_fusion_api()

        data = request.get_json()
        if not data or 'variants' not in data:
            return jsonify({"error": "variants array is required"}), 400

        from gimp_comfy_bridge.fusion.variants import VariantGenerator
        generator = VariantGenerator()
        stats = generator.get_variant_stats(data['variants'])

        return jsonify(stats), 200

    except Exception as e:
        logger.error(f"Failed to get variant stats: {e}")
        return jsonify({"error": str(e)}), 500


@fusion_bp.route('/health', methods=['GET'])
def fusion_health():
    """Check fusion engine health."""
    try:
        initialize_fusion_api()

        health = {
            "status": "healthy",
            "fusion_engine": "initialized",
            "brand_kits_loaded": len(_brand_kit_manager.list_brand_kits()) if _brand_kit_manager else 0,
            "preview_stats": _preview_generator.get_preview_stats() if _preview_generator else {}
        }

        return jsonify(health), 200

    except Exception as e:
        logger.error(f"Fusion health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500