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

    def __init__(self, host: str = "localhost", port: int = 8080, mobile_bridge=None):
        """
        Initialize the web server.

        Args:
            host (str): Server host
            port (int): Server port
            mobile_bridge: Mobile bridge instance for mobile integration
        """
        self.host = host
        self.port = port
        self.mobile_bridge = mobile_bridge
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

        # Mobile API routes (Phase 20)
        if self.mobile_bridge:
            self.app.router.add_get('/api/mobile/qr', self._handle_mobile_qr)
            self.app.router.add_get('/api/mobile/devices', self._handle_mobile_devices)
            self.app.router.add_post('/api/mobile/pair', self._handle_mobile_pair)
            self.app.router.add_post('/api/mobile/push/{device_id}', self._handle_mobile_push)
            self.app.router.add_post('/api/mobile/pull/{device_id}', self._handle_mobile_pull)
            self.app.router.add_post('/api/mobile/preview/start', self._handle_preview_start)
            self.app.router.add_post('/api/mobile/preview/frame', self._handle_preview_frame)
            self.app.router.add_post('/api/mobile/preview/stop', self._handle_preview_stop)
            self.app.router.add_post('/api/mobile/remote/{device_id}', self._handle_remote_command)
            self.app.router.add_get('/api/mobile/status', self._handle_mobile_status)

        # UI routes
        self.app.router.add_get('/', self._handle_index)
        self.app.router.add_get('/templates', self._handle_templates_page)
        self.app.router.add_get('/styles', self._handle_styles_page)
        self.app.router.add_get('/models', self._handle_models_page)
        self.app.router.add_get('/workflows', self._handle_workflows_page)
        self.app.router.add_get('/settings', self._handle_settings_page)
        self.app.router.add_get('/execution', self._handle_execution_page)
        self.app.router.add_get('/mobile', self._handle_mobile_page)

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

    async def _handle_mobile_page(self, request):
        """Handle mobile page."""
        return web.FileResponse(Path(__file__).parent / "ui" / "mobile.html")

    # Mobile API handlers
    async def _handle_mobile_qr(self, request):
        """Handle mobile QR code generation."""
        if not self.mobile_bridge:
            return web.json_response({"error": "Mobile bridge not available"}, status=503)

        try:
            # Generate pairing QR code
            pairing_token = self.mobile_bridge.auth.generate_pairing_token()

            # Generate QR code data URL
            import qrcode
            import io
            import base64

            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(f"comfy-gimpy://pair?token={pairing_token}")
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            qr_data = base64.b64encode(buffer.getvalue()).decode()

            return web.json_response({
                "qr_data": f"data:image/png;base64,{qr_data}",
                "pairing_token": pairing_token,
                "expires_in": 300
            })

        except Exception as e:
            logger.error(f"Failed to generate mobile QR: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_mobile_devices(self, request):
        """Handle mobile devices list."""
        if not self.mobile_bridge:
            return web.json_response({"error": "Mobile bridge not available"}, status=503)

        try:
            devices = self.mobile_bridge.get_mobile_devices()
            return web.json_response({"devices": devices})

        except Exception as e:
            logger.error(f"Failed to get mobile devices: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_mobile_pair(self, request):
        """Handle mobile device pairing."""
        if not self.mobile_bridge:
            return web.json_response({"error": "Mobile bridge not available"}, status=503)

        try:
            data = await request.json()
            device_id = data.get('device_id')
            pairing_token = data.get('pairing_token')

            if not device_id or not pairing_token:
                return web.json_response({"error": "Device ID and pairing token required"}, status=400)

            # Handle pairing through mobile bridge
            result = self.mobile_bridge.handle_mobile_message(device_id, {
                'type': 'auth_request',
                'pairing_token': pairing_token
            })

            return web.json_response(result)

        except Exception as e:
            logger.error(f"Failed to pair mobile device: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_mobile_push(self, request):
        """Handle mobile asset push."""
        if not self.mobile_bridge:
            return web.json_response({"error": "Mobile bridge not available"}, status=503)

        try:
            device_id = request.match_info['device_id']
            data = await request.json()

            asset_path = data.get('asset_path')
            asset_type = data.get('asset_type', 'file')

            if not asset_path:
                return web.json_response({"error": "Asset path required"}, status=400)

            push_id = self.mobile_bridge.push_asset_to_device(device_id, asset_path, asset_type)
            return web.json_response({"push_id": push_id, "status": "queued"})

        except Exception as e:
            logger.error(f"Failed to push to mobile device: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_mobile_pull(self, request):
        """Handle mobile asset pull."""
        if not self.mobile_bridge:
            return web.json_response({"error": "Mobile bridge not available"}, status=503)

        try:
            device_id = request.match_info['device_id']
            data = await request.json()

            pull_type = data.get('type', 'asset')
            asset_type = data.get('asset_type')
            asset_path = data.get('asset_path')

            if pull_type == 'asset':
                pull_id = self.mobile_bridge.request_asset_from_device(device_id, asset_type, asset_path)
            elif pull_type == 'workflow':
                pull_id = self.mobile_bridge.request_workflow_from_device(device_id, data.get('workflow_name'))
            else:
                return web.json_response({"error": "Invalid pull type"}, status=400)

            return web.json_response({"pull_id": pull_id, "status": "requested"})

        except Exception as e:
            logger.error(f"Failed to pull from mobile device: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_preview_start(self, request):
        """Handle preview stream start."""
        if not self.mobile_bridge:
            return web.json_response({"error": "Mobile bridge not available"}, status=503)

        try:
            data = await request.json()
            preview_id = data.get('preview_id', 'default_preview')
            preview_type = data.get('preview_type', 'image')

            self.mobile_bridge.start_preview_stream(preview_id, preview_type)
            return web.json_response({"preview_id": preview_id, "status": "started"})

        except Exception as e:
            logger.error(f"Failed to start preview: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_preview_frame(self, request):
        """Handle preview frame sending."""
        if not self.mobile_bridge:
            return web.json_response({"error": "Mobile bridge not available"}, status=503)

        try:
            data = await request.json()
            preview_id = data.get('preview_id', 'default_preview')
            frame_data = data.get('frame_data')
            frame_type = data.get('frame_type', 'image')

            if frame_data:
                self.mobile_bridge.send_preview_frame(preview_id, frame_data, frame_type)

            return web.json_response({"status": "sent"})

        except Exception as e:
            logger.error(f"Failed to send preview frame: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_preview_stop(self, request):
        """Handle preview stream stop."""
        if not self.mobile_bridge:
            return web.json_response({"error": "Mobile bridge not available"}, status=503)

        try:
            data = await request.json()
            preview_id = data.get('preview_id', 'default_preview')

            self.mobile_bridge.preview.stop_preview_stream(preview_id)
            return web.json_response({"status": "stopped"})

        except Exception as e:
            logger.error(f"Failed to stop preview: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_remote_command(self, request):
        """Handle remote control command."""
        if not self.mobile_bridge:
            return web.json_response({"error": "Mobile bridge not available"}, status=503)

        try:
            device_id = request.match_info['device_id']
            data = await request.json()

            result = self.mobile_bridge.handle_mobile_message(device_id, {
                'type': 'remote_command',
                'session_id': data.get('session_id'),
                'command': data.get('command'),
                'parameters': data.get('parameters', {})
            })

            return web.json_response(result)

        except Exception as e:
            logger.error(f"Failed to send remote command: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_mobile_status(self, request):
        """Handle mobile bridge status."""
        if not self.mobile_bridge:
            return web.json_response({"error": "Mobile bridge not available"}, status=503)

        try:
            status = self.mobile_bridge.get_system_status()
            return web.json_response({"status": status})

        except Exception as e:
            logger.error(f"Failed to get mobile status: {e}")
            return web.json_response({"error": str(e)}, status=500)

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