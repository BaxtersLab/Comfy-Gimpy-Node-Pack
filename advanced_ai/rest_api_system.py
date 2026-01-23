"""
REST API System
Complete RESTful API for third-party integrations and webhooks
"""

import asyncio
import logging
import json
import secrets
import hashlib
import hmac
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid
import base64
import re

try:
    from aiohttp import web, hdrs
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

# Import collaborative studio components
from ..collaborative_studio import get_collaborative_studio
from .multi_modal_generator import get_multimodal_generator, GenerationRequest, ContentType, GenerationProvider
from .style_transfer_engine import get_style_transfer_engine, StyleTransferRequest
from .analytics_system import get_analytics_system


class APIKeyType(Enum):
    """API key types"""
    FULL_ACCESS = "full_access"
    READ_ONLY = "read_only"
    GENERATION_ONLY = "generation_only"
    ANALYTICS_ONLY = "analytics_only"


class WebhookEvent(Enum):
    """Webhook event types"""
    GENERATION_COMPLETED = "generation.completed"
    STYLE_TRANSFER_COMPLETED = "style_transfer.completed"
    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"
    USER_JOINED = "user.joined"
    USER_LEFT = "user.left"
    ERROR_OCCURRED = "error.occurred"


@dataclass
class APIKey:
    """API key data"""
    key_id: str
    key_hash: str
    name: str
    key_type: APIKeyType
    user_id: str
    created_at: datetime
    last_used: Optional[datetime] = None
    usage_count: int = 0
    rate_limit: int = 1000  # requests per hour
    is_active: bool = True
    permissions: List[str] = field(default_factory=list)

    def verify_key(self, provided_key: str) -> bool:
        """Verify API key"""
        return hmac.compare_digest(
            self.key_hash,
            hashlib.sha256(provided_key.encode()).hexdigest()
        )

    def can_access(self, endpoint: str, method: str) -> bool:
        """Check if key can access endpoint"""
        if not self.is_active:
            return False

        # Check rate limit (simplified)
        if self.usage_count >= self.rate_limit:
            return False

        # Check permissions based on key type
        if self.key_type == APIKeyType.READ_ONLY and method not in ['GET', 'HEAD']:
            return False
        elif self.key_type == APIKeyType.GENERATION_ONLY:
            if not endpoint.startswith('/api/generate'):
                return False
        elif self.key_type == APIKeyType.ANALYTICS_ONLY:
            if not endpoint.startswith('/api/analytics'):
                return False

        return True


@dataclass
class WebhookSubscription:
    """Webhook subscription data"""
    subscription_id: str
    url: str
    events: List[WebhookEvent]
    secret: str
    user_id: str
    created_at: datetime
    is_active: bool = True
    retry_count: int = 0
    last_delivery: Optional[datetime] = None

    def should_deliver(self, event: WebhookEvent) -> bool:
        """Check if webhook should receive this event"""
        return self.is_active and event in self.events


@dataclass
class APIRequest:
    """API request data"""
    request_id: str
    method: str
    path: str
    user_id: Optional[str] = None
    api_key_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    response_status: Optional[int] = None
    processing_time: Optional[float] = None
    ip_address: Optional[str] = None


class RESTAPISystem:
    """Complete REST API system for collaborative studio"""

    def __init__(self, host: str = "localhost", port: int = 8000):
        self.logger = logging.getLogger(__name__)

        # Server configuration
        self.host = host
        self.port = port

        # Web server
        self.app = None
        self.runner = None
        self.site = None

        # API keys
        self.api_keys: Dict[str, APIKey] = {}

        # Webhook subscriptions
        self.webhook_subscriptions: Dict[str, WebhookSubscription] = {}

        # Request tracking
        self.active_requests: Dict[str, APIRequest] = {}
        self.request_history: List[APIRequest] = []

        # Rate limiting
        self.rate_limits: Dict[str, Dict[str, Any]] = {}

        # CORS settings
        self.cors_origins = ["*"]  # Configure as needed

        # Initialize components
        self.studio = None
        self.generator = None
        self.style_engine = None
        self.analytics = None

    async def initialize(self):
        """Initialize the API system"""
        self.logger.info("Initializing REST API system")

        # Get component references
        self.studio = get_collaborative_studio()
        self.generator = get_multimodal_generator()
        self.style_engine = get_style_transfer_engine()
        self.analytics = get_analytics_system()

        # Setup web application
        self.app = web.Application(middlewares=[
            self.cors_middleware,
            self.auth_middleware,
            self.rate_limit_middleware,
            self.logging_middleware
        ])

        # Setup routes
        self._setup_routes()

        self.logger.info("REST API system initialized")

    async def start_server(self):
        """Start the API server"""
        if not self.app:
            await self.initialize()

        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()

        self.logger.info(f"REST API server started on http://{self.host}:{self.port}")

    async def stop_server(self):
        """Stop the API server"""
        if self.site:
            await self.site.stop()

        if self.runner:
            await self.runner.cleanup()

        self.logger.info("REST API server stopped")

    def _setup_routes(self):
        """Setup API routes"""

        # Health check
        self.app.router.add_get('/health', self.health_check_handler)

        # API v1 routes
        v1 = web.RouteTableDef()

        # Generation endpoints
        v1.add_post('/api/v1/generate/text', self.generate_text_handler)
        v1.add_post('/api/v1/generate/image', self.generate_image_handler)
        v1.add_post('/api/v1/generate/audio', self.generate_audio_handler)
        v1.add_post('/api/v1/generate/code', self.generate_code_handler)

        # Style transfer endpoints
        v1.add_post('/api/v1/style-transfer', self.style_transfer_handler)
        v1.add_get('/api/v1/styles', self.list_styles_handler)

        # Project endpoints
        v1.add_post('/api/v1/projects', self.create_project_handler)
        v1.add_get('/api/v1/projects', self.list_projects_handler)
        v1.add_get('/api/v1/projects/{project_id}', self.get_project_handler)

        # User endpoints
        v1.add_get('/api/v1/users', self.list_users_handler)
        v1.add_get('/api/v1/users/{user_id}', self.get_user_handler)

        # Analytics endpoints
        v1.add_get('/api/v1/analytics/users/{user_id}', self.user_analytics_handler)
        v1.add_get('/api/v1/analytics/performance', self.performance_analytics_handler)
        v1.add_get('/api/v1/analytics/system', self.system_analytics_handler)

        # Webhook endpoints
        v1.add_post('/api/v1/webhooks', self.create_webhook_handler)
        v1.add_get('/api/v1/webhooks', self.list_webhooks_handler)
        v1.add_delete('/api/v1/webhooks/{subscription_id}', self.delete_webhook_handler)

        # API key management
        v1.add_post('/api/v1/keys', self.create_api_key_handler)
        v1.add_get('/api/v1/keys', self.list_api_keys_handler)
        v1.add_delete('/api/v1/keys/{key_id}', self.delete_api_key_handler)

        self.app.add_routes(v1)

    # Middleware

    @web.middleware
    async def cors_middleware(self, request, handler):
        """CORS middleware"""
        response = await handler(request)

        response.headers['Access-Control-Allow-Origin'] = ','.join(self.cors_origins)
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-API-Key'

        if request.method == 'OPTIONS':
            return web.Response()

        return response

    @web.middleware
    async def auth_middleware(self, request, handler):
        """Authentication middleware"""
        # Skip auth for health check
        if request.path == '/health':
            return await handler(request)

        # Check for API key
        api_key = request.headers.get('X-API-Key') or request.query.get('api_key')

        if not api_key:
            return web.json_response(
                {'error': 'API key required'},
                status=401
            )

        # Verify API key
        key_data = self._verify_api_key(api_key)
        if not key_data:
            return web.json_response(
                {'error': 'Invalid API key'},
                status=401
            )

        # Check permissions
        if not key_data.can_access(request.path, request.method):
            return web.json_response(
                {'error': 'Insufficient permissions'},
                status=403
            )

        # Add user context to request
        request['user_id'] = key_data.user_id
        request['api_key_id'] = key_data.key_id

        return await handler(request)

    @web.middleware
    async def rate_limit_middleware(self, request, handler):
        """Rate limiting middleware"""
        api_key_id = request.get('api_key_id')
        if api_key_id and api_key_id in self.api_keys:
            key_data = self.api_keys[api_key_id]
            key_data.usage_count += 1
            key_data.last_used = datetime.now()

        return await handler(request)

    @web.middleware
    async def logging_middleware(self, request, handler):
        """Request logging middleware"""
        request_id = str(uuid.uuid4())
        start_time = asyncio.get_event_loop().time()

        # Create request record
        api_request = APIRequest(
            request_id=request_id,
            method=request.method,
            path=request.path,
            user_id=request.get('user_id'),
            api_key_id=request.get('api_key_id'),
            ip_address=request.remote
        )

        self.active_requests[request_id] = api_request

        try:
            response = await handler(request)
            api_request.response_status = response.status
            return response
        finally:
            processing_time = asyncio.get_event_loop().time() - start_time
            api_request.processing_time = processing_time

            self.request_history.append(api_request)
            if len(self.request_history) > 10000:
                self.request_history = self.request_history[-10000:]

            del self.active_requests[request_id]

            # Log request
            self.logger.info(
                f"API Request: {request.method} {request.path} "
                f"Status: {api_request.response_status} "
                f"Time: {processing_time:.3f}s"
            )

    # Route handlers

    async def health_check_handler(self, request):
        """Health check endpoint"""
        return web.json_response({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0'
        })

    async def generate_text_handler(self, request):
        """Generate text content"""
        try:
            data = await request.json()

            generation_request = GenerationRequest(
                request_id=str(uuid.uuid4()),
                content_type=ContentType.TEXT,
                prompt=data['prompt'],
                provider=GenerationProvider(data.get('provider', 'openai')),
                parameters=data.get('parameters', {}),
                user_id=request['user_id']
            )

            result = await self.generator.generate_content(generation_request)

            # Track analytics
            self.analytics.track_event(
                'content_generation',
                'text_generated',
                user_id=request['user_id'],
                properties={
                    'provider': generation_request.provider.value,
                    'prompt_length': len(generation_request.prompt)
                }
            )

            # Send webhook
            await self._send_webhook(WebhookEvent.GENERATION_COMPLETED, {
                'type': 'text',
                'result': result.to_dict()
            })

            return web.json_response(result.to_dict())

        except Exception as e:
            self.logger.error(f"Text generation error: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def generate_image_handler(self, request):
        """Generate image content"""
        try:
            data = await request.json()

            generation_request = GenerationRequest(
                request_id=str(uuid.uuid4()),
                content_type=ContentType.IMAGE,
                prompt=data['prompt'],
                provider=GenerationProvider(data.get('provider', 'openai')),
                parameters=data.get('parameters', {}),
                user_id=request['user_id']
            )

            result = await self.generator.generate_content(generation_request)

            # Convert image to base64 for JSON response
            response_data = result.to_dict()
            if isinstance(result.content, bytes):
                response_data['content'] = base64.b64encode(result.content).decode()

            return web.json_response(response_data)

        except Exception as e:
            self.logger.error(f"Image generation error: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def generate_audio_handler(self, request):
        """Generate audio content"""
        return web.json_response({'error': 'Audio generation not yet implemented'}, status=501)

    async def generate_code_handler(self, request):
        """Generate code content"""
        try:
            data = await request.json()

            generation_request = GenerationRequest(
                request_id=str(uuid.uuid4()),
                content_type=ContentType.CODE,
                prompt=data['prompt'],
                provider=GenerationProvider(data.get('provider', 'openai')),
                parameters=data.get('parameters', {}),
                user_id=request['user_id']
            )

            result = await self.generator.generate_content(generation_request)

            return web.json_response(result.to_dict())

        except Exception as e:
            self.logger.error(f"Code generation error: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def style_transfer_handler(self, request):
        """Perform style transfer"""
        try:
            data = await request.json()

            # Get image data
            image_data = base64.b64decode(data['image'])

            style_request = StyleTransferRequest(
                request_id=str(uuid.uuid4()),
                content_image=image_data,
                style_reference=data['style_id'],
                parameters=data.get('parameters', {}),
                user_id=request['user_id']
            )

            result = await self.style_engine.transfer_style(style_request)

            # Convert result image to base64
            response_data = result.to_dict()
            response_data['result_image'] = base64.b64encode(result.result_image).decode()

            return web.json_response(response_data)

        except Exception as e:
            self.logger.error(f"Style transfer error: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def list_styles_handler(self, request):
        """List available style references"""
        styles = self.style_engine.list_style_references()
        return web.json_response({
            'styles': [style.to_dict() for style in styles]
        })

    async def create_project_handler(self, request):
        """Create a new project"""
        try:
            data = await request.json()

            project_id = await self.studio.create_project(
                data['name'],
                data.get('description', ''),
                request['user_id']
            )

            return web.json_response({
                'project_id': project_id,
                'status': 'created'
            }, status=201)

        except Exception as e:
            self.logger.error(f"Project creation error: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def list_projects_handler(self, request):
        """List projects"""
        # Simplified - would need proper project listing from studio
        return web.json_response({'projects': []})

    async def get_project_handler(self, request):
        """Get project details"""
        project_id = request.match_info['project_id']
        return web.json_response({'error': 'Project retrieval not yet implemented'}, status=501)

    async def list_users_handler(self, request):
        """List users"""
        return web.json_response({'users': []})

    async def get_user_handler(self, request):
        """Get user details"""
        user_id = request.match_info['user_id']
        return web.json_response({'error': 'User retrieval not yet implemented'}, status=501)

    async def user_analytics_handler(self, request):
        """Get user analytics"""
        user_id = request.match_info['user_id']
        analytics = self.analytics.get_user_analytics(user_id)
        return web.json_response(analytics)

    async def performance_analytics_handler(self, request):
        """Get performance analytics"""
        analytics = self.analytics.get_performance_analytics()
        return web.json_response(analytics)

    async def system_analytics_handler(self, request):
        """Get system analytics"""
        health = self.analytics.get_system_health()
        return web.json_response(health)

    async def create_webhook_handler(self, request):
        """Create webhook subscription"""
        try:
            data = await request.json()

            subscription = WebhookSubscription(
                subscription_id=str(uuid.uuid4()),
                url=data['url'],
                events=[WebhookEvent(event) for event in data['events']],
                secret=secrets.token_hex(32),
                user_id=request['user_id']
            )

            self.webhook_subscriptions[subscription.subscription_id] = subscription

            return web.json_response({
                'subscription_id': subscription.subscription_id,
                'secret': subscription.secret
            }, status=201)

        except Exception as e:
            self.logger.error(f"Webhook creation error: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def list_webhooks_handler(self, request):
        """List webhook subscriptions"""
        user_webhooks = [
            {
                'subscription_id': sub.subscription_id,
                'url': sub.url,
                'events': [event.value for event in sub.events],
                'is_active': sub.is_active,
                'created_at': sub.created_at.isoformat()
            }
            for sub in self.webhook_subscriptions.values()
            if sub.user_id == request['user_id']
        ]

        return web.json_response({'webhooks': user_webhooks})

    async def delete_webhook_handler(self, request):
        """Delete webhook subscription"""
        subscription_id = request.match_info['subscription_id']

        if subscription_id in self.webhook_subscriptions:
            subscription = self.webhook_subscriptions[subscription_id]
            if subscription.user_id == request['user_id']:
                del self.webhook_subscriptions[subscription_id]
                return web.json_response({'status': 'deleted'})

        return web.json_response({'error': 'Webhook not found'}, status=404)

    async def create_api_key_handler(self, request):
        """Create API key"""
        try:
            data = await request.json()

            # Generate API key
            api_key_value = secrets.token_hex(32)
            key_hash = hashlib.sha256(api_key_value.encode()).hexdigest()

            api_key = APIKey(
                key_id=str(uuid.uuid4()),
                key_hash=key_hash,
                name=data['name'],
                key_type=APIKeyType(data.get('type', 'full_access')),
                user_id=request['user_id'],
                permissions=data.get('permissions', [])
            )

            self.api_keys[api_key.key_id] = api_key

            return web.json_response({
                'key_id': api_key.key_id,
                'api_key': api_key_value,  # Only returned once
                'name': api_key.name,
                'type': api_key.key_type.value
            }, status=201)

        except Exception as e:
            self.logger.error(f"API key creation error: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def list_api_keys_handler(self, request):
        """List API keys"""
        user_keys = [
            {
                'key_id': key.key_id,
                'name': key.name,
                'type': key.key_type.value,
                'created_at': key.created_at.isoformat(),
                'last_used': key.last_used.isoformat() if key.last_used else None,
                'usage_count': key.usage_count,
                'is_active': key.is_active
            }
            for key in self.api_keys.values()
            if key.user_id == request['user_id']
        ]

        return web.json_response({'api_keys': user_keys})

    async def delete_api_key_handler(self, request):
        """Delete API key"""
        key_id = request.match_info['key_id']

        if key_id in self.api_keys:
            api_key = self.api_keys[key_id]
            if api_key.user_id == request['user_id']:
                del self.api_keys[key_id]
                return web.json_response({'status': 'deleted'})

        return web.json_response({'error': 'API key not found'}, status=404)

    # Helper methods

    def _verify_api_key(self, provided_key: str) -> Optional[APIKey]:
        """Verify API key and return key data"""
        key_hash = hashlib.sha256(provided_key.encode()).hexdigest()

        for api_key in self.api_keys.values():
            if api_key.verify_key(provided_key):
                return api_key

        return None

    async def _send_webhook(self, event: WebhookEvent, payload: Dict[str, Any]):
        """Send webhook notification"""
        if not AIOHTTP_AVAILABLE:
            return

        for subscription in self.webhook_subscriptions.values():
            if subscription.should_deliver(event):
                try:
                    # Create signature
                    payload_str = json.dumps(payload, sort_keys=True)
                    signature = hmac.new(
                        subscription.secret.encode(),
                        payload_str.encode(),
                        hashlib.sha256
                    ).hexdigest()

                    headers = {
                        'Content-Type': 'application/json',
                        'X-Webhook-Signature': signature,
                        'X-Webhook-Event': event.value
                    }

                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            subscription.url,
                            json=payload,
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as response:
                            if response.status >= 200 and response.status < 300:
                                subscription.last_delivery = datetime.now()
                                subscription.retry_count = 0
                            else:
                                subscription.retry_count += 1

                except Exception as e:
                    self.logger.error(f"Webhook delivery failed: {e}")
                    subscription.retry_count += 1

    def get_api_stats(self) -> Dict[str, Any]:
        """Get API usage statistics"""
        total_requests = len(self.request_history)
        active_requests = len(self.active_requests)

        # Calculate response time stats
        response_times = [r.processing_time for r in self.request_history if r.processing_time]
        avg_response_time = statistics.mean(response_times) if response_times else 0

        # Status code distribution
        status_counts = {}
        for request in self.request_history:
            if request.response_status:
                status_counts[request.response_status] = status_counts.get(request.response_status, 0) + 1

        return {
            'total_requests': total_requests,
            'active_requests': active_requests,
            'avg_response_time': avg_response_time,
            'status_distribution': status_counts,
            'total_api_keys': len(self.api_keys),
            'total_webhooks': len(self.webhook_subscriptions)
        }


# Global instance
_rest_api_system = None

def get_rest_api_system() -> RESTAPISystem:
    """Get global REST API system instance"""
    global _rest_api_system
    if _rest_api_system is None:
        _rest_api_system = RESTAPISystem()
    return _rest_api_system

async def initialize_rest_api_system(host: str = "localhost", port: int = 8000) -> RESTAPISystem:
    """Initialize the global REST API system"""
    global _rest_api_system
    if _rest_api_system is None:
        _rest_api_system = RESTAPISystem(host, port)
        await _rest_api_system.initialize()
    return _rest_api_system</content>
<parameter name="filePath">c:\Users\Baxter\Documents\ComfyUI_env\ComfyUI\custom_nodes\Comfy Gimpy Node Pack\advanced_ai\rest_api_system.py