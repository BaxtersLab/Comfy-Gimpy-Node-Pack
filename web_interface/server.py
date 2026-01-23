"""
Web server for Comfy Gimpy Studio web interface.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import threading
import time

from gimp_comfy_bridge.shared.config import load_config

logger = logging.getLogger(__name__)

try:
    from aiohttp import web, ClientSession
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logger.warning("aiohttp not available, web interface disabled")


class WebServer:
    """
    Web server for the Comfy Gimpy Studio interface.
    """

    def __init__(self, host: str = "localhost", port: int = 8080):
        """
        Initialize the web server.

        Args:
            host (str): Server host
            port (int): Server port
        """
        self.host = host
        self.port = port
        self.app = None
        self.runner = None
        self.site = None
        self.thread = None
        self.running = False

        if not AIOHTTP_AVAILABLE:
            logger.error("Cannot start web server: aiohttp not available")
            return

        self.app = web.Application()
        self._setup_routes()
        self._load_config()

    def _load_config(self):
        """Load configuration for the web server."""
        try:
            self.config = load_config()
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self.config = None

    def _setup_routes(self):
        """Set up web routes."""
        # Static files
        static_path = Path(__file__).parent / "static"
        self.app.router.add_static('/static/', static_path)

        # API routes
        self.app.router.add_get('/api/models/list', self._handle_models_list)
        self.app.router.add_post('/api/models/install', self._handle_models_install)
        self.app.router.add_get('/api/templates/list', self._handle_templates_list)
        self.app.router.add_get('/api/templates/preview/{category}/{name}', self._handle_template_preview)
        self.app.router.add_get('/api/styles/list', self._handle_styles_list)
        self.app.router.add_get('/api/styles/preview/{category}/{name}', self._handle_style_preview)
        self.app.router.add_get('/api/workflows/list', self._handle_workflows_list)
        self.app.router.add_get('/api/settings/get', self._handle_settings_get)
        self.app.router.add_post('/api/settings/set', self._handle_settings_set)

        # Pack API routes
        self.app.router.add_post('/api/packs/create', self._handle_create_pack)
        self.app.router.add_get('/api/packs/export/{pack_id}', self._handle_export_pack)
        self.app.router.add_post('/api/packs/validate', self._handle_validate_pack)
        self.app.router.add_post('/api/packs/install', self._handle_install_pack)
        self.app.router.add_post('/api/packs/update/{pack_id}', self._handle_update_pack)
        self.app.router.add_delete('/api/packs/uninstall/{pack_id}', self._handle_uninstall_pack)
        self.app.router.add_get('/api/packs/', self._handle_list_packs)
        self.app.router.add_get('/api/packs/{pack_id}', self._handle_get_pack)
        self.app.router.add_get('/api/packs/search', self._handle_search_packs)
        self.app.router.add_get('/api/packs/types', self._handle_get_pack_types)
        self.app.router.add_get('/api/packs/stats', self._handle_get_pack_stats)

        # Execution API routes (Phase 9)
        self.app.router.add_post('/api/execution/execute', self._handle_execute_workflow)
        self.app.router.add_post('/api/execution/execute-fusion', self._handle_execute_fusion)
        self.app.router.add_get('/api/execution/status/{job_id}', self._handle_get_job_status)
        self.app.router.add_post('/api/execution/cancel/{job_id}', self._handle_cancel_job)
        self.app.router.add_get('/api/execution/system-status', self._handle_get_system_status)
        self.app.router.add_get('/api/execution/performance', self._handle_get_performance)
        self.app.router.add_post('/api/execution/process/{job_id}', self._handle_process_output)
        self.app.router.add_get('/api/execution/jobs', self._handle_list_jobs)
        self.app.router.add_post('/api/execution/batch-status', self._handle_batch_status)

        # UI routes
        self.app.router.add_get('/', self._handle_index)
        self.app.router.add_get('/templates', self._handle_templates_page)
        self.app.router.add_get('/styles', self._handle_styles_page)
        self.app.router.add_get('/models', self._handle_models_page)
        self.app.router.add_get('/workflows', self._handle_workflows_page)
        self.app.router.add_get('/settings', self._handle_settings_page)
        self.app.router.add_get('/execution', self._handle_execution_page)

    async def _handle_index(self, request):
        """Handle index page."""
        return web.FileResponse(Path(__file__).parent / "ui" / "index.html")

    async def _handle_templates_page(self, request):
        """Handle templates page."""
        return web.FileResponse(Path(__file__).parent / "ui" / "templates.html")

    async def _handle_styles_page(self, request):
        """Handle styles page."""
        return web.FileResponse(Path(__file__).parent / "ui" / "styles.html")

    async def _handle_models_page(self, request):
        """Handle models page."""
        return web.FileResponse(Path(__file__).parent / "ui" / "models.html")

    async def _handle_workflows_page(self, request):
        """Handle workflows page."""
        return web.FileResponse(Path(__file__).parent / "ui" / "workflows.html")

    async def _handle_settings_page(self, request):
        """Handle settings page."""
        return web.FileResponse(Path(__file__).parent / "ui" / "settings.html")

    async def _handle_models_list(self, request):
        """Handle models list API."""
        try:
            from gimp_comfy_bridge.shared.model_registry import scan_models
            models = scan_models()
            return web.json_response({"models": models})
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_models_install(self, request):
        """Handle model installation API."""
        try:
            data = await request.json()
            model_url = data.get('url')
            model_type = data.get('type', 'checkpoint')

            if not model_url:
                return web.json_response({"error": "Model URL required"}, status=400)

            # Stub implementation - would download and install model
            logger.info(f"Installing model from {model_url} (type: {model_type})")
            return web.json_response({"status": "installing", "message": "Model installation started"})

        except Exception as e:
            logger.error(f"Failed to install model: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_templates_list(self, request):
        """Handle templates list API."""
        try:
            from gimp_comfy_bridge.gimp_plugin.plugin import list_template_categories, list_templates_in_category

            categories = list_template_categories()
            result = []

            for cat in categories:
                templates = list_templates_in_category(cat['name'])
                result.append({
                    "category": cat,
                    "templates": templates
                })

            return web.json_response({"data": result})

        except Exception as e:
            logger.error(f"Failed to list templates: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_template_preview(self, request):
        """Handle template preview API."""
        try:
            category = request.match_info['category']
            name = request.match_info['name']

            # Stub - would return preview image
            return web.json_response({"error": "Preview not implemented"}, status=501)

        except Exception as e:
            logger.error(f"Failed to get template preview: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_styles_list(self, request):
        """Handle styles list API."""
        try:
            from gimp_comfy_bridge.gimp_plugin.plugin import list_style_categories, list_styles_in_category

            categories = list_style_categories()
            result = []

            for cat in categories:
                styles = list_styles_in_category(cat['name'])
                result.append({
                    "category": cat,
                    "styles": styles
                })

            return web.json_response({"data": result})

        except Exception as e:
            logger.error(f"Failed to list styles: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_style_preview(self, request):
        """Handle style preview API."""
        try:
            category = request.match_info['category']
            name = request.match_info['name']

            # Stub - would return preview image
            return web.json_response({"error": "Preview not implemented"}, status=501)

        except Exception as e:
            logger.error(f"Failed to get style preview: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_workflows_list(self, request):
        """Handle workflows list API."""
        try:
            # Stub - would list available workflows
            workflows = [
                {"name": "txt2img_basic", "description": "Basic text to image"},
                {"name": "img2img_basic", "description": "Basic image to image"},
                {"name": "inpaint_basic", "description": "Basic inpainting"}
            ]
            return web.json_response({"workflows": workflows})

        except Exception as e:
            logger.error(f"Failed to list workflows: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_settings_get(self, request):
        """Handle settings get API."""
        try:
            if not self.config:
                return web.json_response({"error": "Config not loaded"}, status=500)

            settings = {
                "comfyui_host": self.config.comfyui_host,
                "comfyui_port": self.config.comfyui_port,
                "bridge_host": self.config.host,
                "bridge_port": self.config.port,
                "log_level": self.config.log_level
            }
            return web.json_response({"settings": settings})

        except Exception as e:
            logger.error(f"Failed to get settings: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_settings_set(self, request):
        """Handle settings set API."""
        try:
            data = await request.json()
            # Stub - would update settings
            logger.info(f"Updating settings: {data}")
            return web.json_response({"status": "updated"})

        except Exception as e:
            logger.error(f"Failed to set settings: {e}")
            return web.json_response({"error": str(e)}, status=500)

    # Pack API handlers
    async def _handle_create_pack(self, request):
        """Handle pack creation API."""
        from .api.packs import handle_create_pack
        return await handle_create_pack(request)

    async def _handle_export_pack(self, request):
        """Handle pack export API."""
        from .api.packs import handle_export_pack
        return await handle_export_pack(request)

    async def _handle_validate_pack(self, request):
        """Handle pack validation API."""
        from .api.packs import handle_validate_pack
        return await handle_validate_pack(request)

    async def _handle_install_pack(self, request):
        """Handle pack installation API."""
        from .api.packs import handle_install_pack
        return await handle_install_pack(request)

    async def _handle_update_pack(self, request):
        """Handle pack update API."""
        from .api.packs import handle_update_pack
        return await handle_update_pack(request)

    async def _handle_uninstall_pack(self, request):
        """Handle pack uninstallation API."""
        from .api.packs import handle_uninstall_pack
        return await handle_uninstall_pack(request)

    async def _handle_list_packs(self, request):
        """Handle pack listing API."""
        from .api.packs import handle_list_packs
        return await handle_list_packs(request)

    async def _handle_get_pack(self, request):
        """Handle get pack API."""
        from .api.packs import handle_get_pack
        return await handle_get_pack(request)

    async def _handle_search_packs(self, request):
        """Handle pack search API."""
        from .api.packs import handle_search_packs
        return await handle_search_packs(request)

    async def _handle_get_pack_types(self, request):
        """Handle get pack types API."""
        from .api.packs import handle_get_pack_types
        return await handle_get_pack_types(request)

    async def _handle_get_pack_stats(self, request):
        """Handle get pack stats API."""
        from .api.packs import handle_get_pack_stats
        return await handle_get_pack_stats(request)

    async def _handle_execution_page(self, request):
        """Handle execution page."""
        return web.FileResponse(Path(__file__).parent / "ui" / "execution.html")

    # Phase 9 - Execution API handlers
    async def _handle_execute_workflow(self, request):
        """Handle workflow execution API."""
        from .api.execution import execute_workflow_handler
        return await execute_workflow_handler(request)

    async def _handle_execute_fusion(self, request):
        """Handle fusion execution API."""
        from .api.execution import execute_fusion_handler
        return await execute_fusion_handler(request)

    async def _handle_get_job_status(self, request):
        """Handle get job status API."""
        from .api.execution import get_job_status_handler
        return await get_job_status_handler(request)

    async def _handle_cancel_job(self, request):
        """Handle cancel job API."""
        from .api.execution import cancel_job_handler
        return await cancel_job_handler(request)

    async def _handle_get_system_status(self, request):
        """Handle get system status API."""
        from .api.execution import get_system_status_handler
        return await get_system_status_handler(request)

    async def _handle_get_performance(self, request):
        """Handle get performance API."""
        from .api.execution import get_performance_handler
        return await get_performance_handler(request)

    async def _handle_process_output(self, request):
        """Handle process output API."""
        from .api.execution import process_output_handler
        return await process_output_handler(request)

    async def _handle_list_jobs(self, request):
        """Handle list jobs API."""
        from .api.execution import list_jobs_handler
        return await list_jobs_handler(request)

    async def _handle_batch_status(self, request):
        """Handle batch status API."""
        from .api.execution import batch_status_handler
        return await batch_status_handler(request)

    def start(self):
        """Start the web server in a background thread."""
        if not AIOHTTP_AVAILABLE or not self.app:
            logger.error("Cannot start web server")
            return

        def run_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                self.runner = web.AppRunner(self.app)
                loop.run_until_complete(self.runner.setup())
                self.site = web.TCPSite(self.runner, self.host, self.port)
                loop.run_until_complete(self.site.start())
                self.running = True
                logger.info(f"Web server started on http://{self.host}:{self.port}")

                # Keep the server running
                try:
                    loop.run_forever()
                except KeyboardInterrupt:
                    pass

            except Exception as e:
                logger.error(f"Failed to start web server: {e}")
            finally:
                if self.site:
                    loop.run_until_complete(self.site.stop())
                if self.runner:
                    loop.run_until_complete(self.runner.cleanup())
                loop.close()

        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the web server."""
        self.running = False
        logger.info("Web server stopped")

    def is_running(self) -> bool:
        """Check if the server is running."""
        return self.running