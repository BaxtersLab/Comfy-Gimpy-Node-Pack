"""
Pack API handlers for Comfy Gimpy Studio marketplace.
Provides aiohttp handlers for pack creation, validation, installation, and management.
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from aiohttp import web

from ...shared.config import Config
from ...shared.types import PackManifest, PackInfo, PackInstallationResult, PackUpdateResult
from ...packs.packager import Packager
from ...packs.validator import PackValidator
from ...packs.registry import PackRegistry
from ...packs.installer import PackInstaller

logger = logging.getLogger(__name__)

# Initialize pack management components
config = Config()
packager = Packager(config)
validator = PackValidator(config)
registry = PackRegistry(config)
installer = PackInstaller(config, registry)


async def handle_create_pack(request: web.Request) -> web.Response:
    """
    Create a new pack from provided data.

    POST /api/packs/create
    Form data: pack_type, name, version, description, author, license, tags,
               content, metadata, dependencies, preview_files[]
    """
    try:
        data = await request.post()

        # Extract form data
        pack_type = data.get('pack_type')
        name = data.get('name')
        version = data.get('version')
        description = data.get('description')
        author = data.get('author')
        license = data.get('license', 'MIT')
        tags = data.get('tags', '[]')
        content = data.get('content', '{}')
        metadata = data.get('metadata', '{}')
        dependencies = data.get('dependencies', '[]')

        if not all([pack_type, name, version, description, author]):
            return web.json_response(
                {"error": "Missing required fields: pack_type, name, version, description, author"},
                status=400
            )

        # Parse JSON strings
        content_data = json.loads(content)
        metadata_data = json.loads(metadata)
        dependencies_data = json.loads(dependencies)
        tags_list = json.loads(tags) if tags else []

        # Handle preview files
        previews = []
        if 'preview_files' in data:
            preview_files = data.getall('preview_files')
            for preview_file in preview_files:
                if hasattr(preview_file, 'filename') and preview_file.filename:
                    # Save preview file temporarily
                    preview_path = config.temp_dir / f"preview_{preview_file.filename}"
                    with open(preview_path, "wb") as f:
                        f.write(preview_file.file.read())

                    previews.append({
                        "filename": preview_file.filename,
                        "path": str(preview_path),
                        "checksum": packager._calculate_checksum(preview_path),
                        "size": preview_path.stat().st_size
                    })

        # Create pack
        result = await packager.create_pack(
            pack_type=pack_type,
            name=name,
            version=version,
            description=description,
            author=author,
            license=license,
            tags=tags_list,
            content=content_data,
            metadata=metadata_data,
            dependencies=dependencies_data,
            previews=previews
        )

        return web.json_response({
            "success": True,
            "pack_id": result["pack_id"],
            "pack_path": result["pack_path"],
            "manifest": result["manifest"]
        })

    except Exception as e:
        logger.error(f"Pack creation failed: {e}")
        return web.json_response({"error": f"Pack creation failed: {str(e)}"}, status=400)


async def handle_export_pack(request: web.Request) -> web.Response:
    """
    Export a pack to ZIP or directory format.

    GET /api/packs/export/{pack_id}?format=zip
    """
    try:
        pack_id = request.match_info['pack_id']
        format_type = request.query.get('format', 'zip')

        # Get pack info
        pack_info = registry.get_pack(pack_id)
        if not pack_info:
            return web.json_response({"error": f"Pack {pack_id} not found"}, status=404)

        # Export pack
        export_result = await packager.export_pack(pack_id, format=format_type)

        if format_type == "zip":
            # Return ZIP file
            return web.FileResponse(
                path=export_result["export_path"],
                headers={
                    'Content-Disposition': f'attachment; filename="{pack_info.name}-{pack_info.version}.zip"'
                }
            )
        else:
            # For directory export, return JSON with path
            return web.json_response({
                "success": True,
                "export_path": export_result["export_path"],
                "format": "directory"
            })

    except Exception as e:
        logger.error(f"Pack export failed: {e}")
        return web.json_response({"error": f"Pack export failed: {str(e)}"}, status=400)


async def handle_validate_pack(request: web.Request) -> web.Response:
    """
    Validate a pack file or directory.

    POST /api/packs/validate
    Form data: file (pack file)
    """
    try:
        data = await request.post()
        pack_file = data.get('file')

        if not pack_file or not hasattr(pack_file, 'filename'):
            return web.json_response({"error": "Pack file required"}, status=400)

        # Save uploaded file temporarily
        temp_path = config.temp_dir / f"validate_{pack_file.filename}"
        with open(temp_path, "wb") as f:
            f.write(pack_file.file.read())

        # Validate pack
        is_valid, errors, manifest = await validator.validate_pack(temp_path)

        # Clean up temp file
        temp_path.unlink(missing_ok=True)

        return web.json_response({
            "valid": is_valid,
            "errors": errors,
            "manifest": manifest.dict() if manifest else None
        })

    except Exception as e:
        logger.error(f"Pack validation failed: {e}")
        return web.json_response({"error": f"Pack validation failed: {str(e)}"}, status=400)


async def handle_install_pack(request: web.Request) -> web.Response:
    """
    Install a pack from uploaded file.

    POST /api/packs/install
    Form data: file (pack file)
    """
    try:
        data = await request.post()
        pack_file = data.get('file')

        if not pack_file or not hasattr(pack_file, 'filename'):
            return web.json_response({"error": "Pack file required"}, status=400)

        # Save uploaded file temporarily
        temp_path = config.temp_dir / f"install_{pack_file.filename}"
        with open(temp_path, "wb") as f:
            f.write(pack_file.file.read())

        # Install pack
        result = await installer.install_pack(temp_path)

        # Clean up temp file
        temp_path.unlink(missing_ok=True)

        return web.json_response(result.dict())

    except Exception as e:
        logger.error(f"Pack installation failed: {e}")
        return web.json_response({"error": f"Pack installation failed: {str(e)}"}, status=400)


async def handle_update_pack(request: web.Request) -> web.Response:
    """
    Update an installed pack.

    POST /api/packs/update/{pack_id}
    Form data: file (new pack file)
    """
    try:
        pack_id = request.match_info['pack_id']
        data = await request.post()
        pack_file = data.get('file')

        if not pack_file or not hasattr(pack_file, 'filename'):
            return web.json_response({"error": "Pack file required"}, status=400)

        # Save uploaded file temporarily
        temp_path = config.temp_dir / f"update_{pack_file.filename}"
        with open(temp_path, "wb") as f:
            f.write(pack_file.file.read())

        # Update pack
        result = await installer.update_pack(pack_id, temp_path)

        # Clean up temp file
        temp_path.unlink(missing_ok=True)

        return web.json_response(result.dict())

    except Exception as e:
        logger.error(f"Pack update failed: {e}")
        return web.json_response({"error": f"Pack update failed: {str(e)}"}, status=400)


async def handle_uninstall_pack(request: web.Request) -> web.Response:
    """
    Uninstall a pack.

    DELETE /api/packs/uninstall/{pack_id}
    """
    try:
        pack_id = request.match_info['pack_id']

        # Uninstall pack
        result = await installer.uninstall_pack(pack_id)

        return web.json_response({
            "success": result,
            "pack_id": pack_id
        })

    except Exception as e:
        logger.error(f"Pack uninstallation failed: {e}")
        return web.json_response({"error": f"Pack uninstallation failed: {str(e)}"}, status=400)


async def handle_list_packs(request: web.Request) -> web.Response:
    """
    List installed packs with optional filtering.

    GET /api/packs/?pack_type=template&author=user&tag=art&limit=50&offset=0
    """
    try:
        pack_type = request.query.get('pack_type')
        author = request.query.get('author')
        tag = request.query.get('tag')
        limit = int(request.query.get('limit', 50))
        offset = int(request.query.get('offset', 0))

        packs = registry.list_packs(
            pack_type=pack_type,
            author=author,
            tag=tag,
            limit=limit,
            offset=offset
        )

        return web.json_response({
            "packs": [pack.dict() for pack in packs],
            "total": len(packs),
            "limit": limit,
            "offset": offset
        })

    except Exception as e:
        logger.error(f"Failed to list packs: {e}")
        return web.json_response({"error": f"Failed to list packs: {str(e)}"}, status=400)


async def handle_get_pack(request: web.Request) -> web.Response:
    """
    Get detailed information about a specific pack.

    GET /api/packs/{pack_id}
    """
    try:
        pack_id = request.match_info['pack_id']

        pack = registry.get_pack(pack_id)
        if not pack:
            return web.json_response({"error": f"Pack {pack_id} not found"}, status=404)

        return web.json_response(pack.dict())

    except Exception as e:
        logger.error(f"Failed to get pack: {e}")
        return web.json_response({"error": f"Failed to get pack: {str(e)}"}, status=400)


async def handle_search_packs(request: web.Request) -> web.Response:
    """
    Search packs by name, description, or tags.

    GET /api/packs/search?q=query&pack_type=template&limit=20
    """
    try:
        query = request.query.get('q', '')
        pack_type = request.query.get('pack_type')
        limit = int(request.query.get('limit', 20))

        if not query:
            return web.json_response({"error": "Search query required"}, status=400)

        results = registry.search_packs(query, pack_type=pack_type, limit=limit)

        return web.json_response({
            "query": query,
            "results": [pack.dict() for pack in results],
            "total": len(results)
        })

    except Exception as e:
        logger.error(f"Pack search failed: {e}")
        return web.json_response({"error": f"Pack search failed: {str(e)}"}, status=400)


async def handle_get_pack_types(request: web.Request) -> web.Response:
    """
    Get available pack types.

    GET /api/packs/types
    """
    return web.json_response({
        "types": ["template", "style", "workflow", "model"]
    })


async def handle_get_pack_stats(request: web.Request) -> web.Response:
    """
    Get pack statistics.

    GET /api/packs/stats
    """
    try:
        stats = registry.get_stats()
        return web.json_response(stats)

    except Exception as e:
        logger.error(f"Failed to get pack stats: {e}")
        return web.json_response({"error": f"Failed to get pack stats: {str(e)}"}, status=400)