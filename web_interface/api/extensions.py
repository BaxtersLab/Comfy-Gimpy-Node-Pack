# web_interface/api/extensions.py

"""
Extensions API for Comfy Gimpy Studio Web Interface.

Provides REST endpoints for extension management, installation, and configuration.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import asyncio
from flask import Blueprint, request, jsonify, current_app

from ...gimp_comfy_bridge.extensions import (
    get_extension_registry,
    get_extension_loader,
    ExtensionManifest
)

logger = logging.getLogger(__name__)

# Create blueprint
extensions_bp = Blueprint('extensions', __name__, url_prefix='/api/extensions')

@extensions_bp.route('/', methods=['GET'])
def list_extensions():
    """List all extensions with their status."""
    try:
        loader = get_extension_loader()
        status = loader.list_extension_status()

        return jsonify({
            'success': True,
            'extensions': status
        })

    except Exception as e:
        logger.error(f"Failed to list extensions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@extensions_bp.route('/<extension_id>', methods=['GET'])
def get_extension(extension_id: str):
    """Get detailed information about a specific extension."""
    try:
        loader = get_extension_loader()
        status = loader.get_extension_status(extension_id)

        if status['status'] == 'not_found':
            return jsonify({
                'success': False,
                'error': 'Extension not found'
            }), 404

        return jsonify({
            'success': True,
            'extension': status
        })

    except Exception as e:
        logger.error(f"Failed to get extension {extension_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@extensions_bp.route('/<extension_id>/enable', methods=['POST'])
def enable_extension(extension_id: str):
    """Enable an extension."""
    try:
        registry = get_extension_registry()

        if not registry.enable_extension(extension_id):
            return jsonify({
                'success': False,
                'error': 'Extension not found or already enabled'
            }), 404

        return jsonify({
            'success': True,
            'message': f'Extension {extension_id} enabled'
        })

    except Exception as e:
        logger.error(f"Failed to enable extension {extension_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@extensions_bp.route('/<extension_id>/disable', methods=['POST'])
def disable_extension(extension_id: str):
    """Disable an extension."""
    try:
        registry = get_extension_registry()

        if not registry.disable_extension(extension_id):
            return jsonify({
                'success': False,
                'error': 'Extension not found or already disabled'
            }), 404

        return jsonify({
            'success': True,
            'message': f'Extension {extension_id} disabled'
        })

    except Exception as e:
        logger.error(f"Failed to disable extension {extension_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@extensions_bp.route('/<extension_id>/reload', methods=['POST'])
def reload_extension(extension_id: str):
    """Reload an extension."""
    try:
        loader = get_extension_loader()

        if loader.reload_extension(extension_id):
            return jsonify({
                'success': True,
                'message': f'Extension {extension_id} reloaded'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to reload extension'
            }), 500

    except Exception as e:
        logger.error(f"Failed to reload extension {extension_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@extensions_bp.route('/install', methods=['POST'])
def install_extension():
    """Install a new extension."""
    try:
        data = request.get_json()

        if not data or 'source' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing source parameter'
            }), 400

        source = data['source']

        # Handle different installation sources
        if source.startswith('http'):
            # Install from URL
            extension_id = _install_from_url(source)
        elif Path(source).exists():
            # Install from local path
            loader = get_extension_loader()
            extension_id = loader.install_extension(Path(source))
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid source'
            }), 400

        if extension_id:
            return jsonify({
                'success': True,
                'message': f'Extension {extension_id} installed',
                'extension_id': extension_id
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Installation failed'
            }), 500

    except Exception as e:
        logger.error(f"Failed to install extension: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@extensions_bp.route('/<extension_id>/uninstall', methods=['DELETE'])
def uninstall_extension(extension_id: str):
    """Uninstall an extension."""
    try:
        loader = get_extension_loader()

        if loader.uninstall_extension(extension_id):
            return jsonify({
                'success': True,
                'message': f'Extension {extension_id} uninstalled'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to uninstall extension'
            }), 500

    except Exception as e:
        logger.error(f"Failed to uninstall extension {extension_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@extensions_bp.route('/marketplace', methods=['GET'])
def browse_marketplace():
    """Browse available extensions in marketplace."""
    try:
        # Mock marketplace data - in real implementation this would fetch from server
        marketplace_extensions = [
            {
                'id': 'sample_workflow_pack',
                'name': 'Sample Workflow Pack',
                'description': 'A collection of sample workflows',
                'version': '1.0.0',
                'author': 'Comfy Gimpy Team',
                'price': 0,
                'tags': ['workflows', 'samples'],
                'downloads': 150
            },
            {
                'id': 'advanced_copywriting',
                'name': 'Advanced Copywriting Tools',
                'description': 'Enhanced copywriting with AI assistance',
                'version': '2.1.0',
                'author': 'CopyMaster Inc',
                'price': 9.99,
                'tags': ['copywriting', 'ai'],
                'downloads': 89
            }
        ]

        return jsonify({
            'success': True,
            'extensions': marketplace_extensions
        })

    except Exception as e:
        logger.error(f"Failed to browse marketplace: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@extensions_bp.route('/marketplace/<extension_id>/install', methods=['POST'])
def install_from_marketplace(extension_id: str):
    """Install extension from marketplace."""
    try:
        # Mock installation - in real implementation this would download and install
        return jsonify({
            'success': True,
            'message': f'Extension {extension_id} installed from marketplace'
        })

    except Exception as e:
        logger.error(f"Failed to install from marketplace: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@extensions_bp.route('/settings', methods=['GET'])
def get_extension_settings():
    """Get extension system settings."""
    try:
        # Mock settings - in real implementation this would read from config
        settings = {
            'auto_update': True,
            'hot_reload': True,
            'max_extensions': 50,
            'trusted_sources': ['marketplace.comfy-gimpy.com']
        }

        return jsonify({
            'success': True,
            'settings': settings
        })

    except Exception as e:
        logger.error(f"Failed to get extension settings: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@extensions_bp.route('/settings', methods=['PUT'])
def update_extension_settings():
    """Update extension system settings."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': 'No settings provided'
            }), 400

        # Mock update - in real implementation this would save to config
        return jsonify({
            'success': True,
            'message': 'Extension settings updated'
        })

    except Exception as e:
        logger.error(f"Failed to update extension settings: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def _install_from_url(url: str) -> Optional[str]:
    """Install extension from URL."""
    # Mock implementation - in real implementation this would download and install
    return "installed_from_url"

# Register blueprint
def init_app(app):
    """Initialize the extensions API with the Flask app."""
    app.register_blueprint(extensions_bp)