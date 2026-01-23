"""
Webhook System
Event-driven webhook delivery with retry logic and dead letter queues
"""

import asyncio
import logging
import json
import hashlib
import hmac
import secrets
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid
import aiohttp
import statistics
from collections import defaultdict, deque

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False


class WebhookEvent(Enum):
    """Webhook event types"""
    GENERATION_COMPLETED = "generation.completed"
    STYLE_TRANSFER_COMPLETED = "style_transfer.completed"
    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"
    USER_JOINED = "user.joined"
    USER_LEFT = "user.left"
    ERROR_OCCURRED = "error.occurred"
    CONTENT_ANALYZED = "content.analyzed"
    PERFORMANCE_METRIC = "performance.metric"
    SYSTEM_HEALTH = "system.health"


class WebhookStatus(Enum):
    """Webhook delivery status"""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


@dataclass
class WebhookDelivery:
    """Webhook delivery attempt"""
    delivery_id: str
    subscription_id: str
    event: WebhookEvent
    payload: Dict[str, Any]
    signature: str
    status: WebhookStatus
    attempt_count: int = 0
    max_attempts: int = 5
    created_at: datetime = field(default_factory=datetime.now)
    last_attempt: Optional[datetime] = None
    next_attempt: Optional[datetime] = None
    last_error: Optional[str] = None
    response_status: Optional[int] = None
    response_body: Optional[str] = None

    def should_retry(self) -> bool:
        """Check if delivery should be retried"""
        return (
            self.attempt_count < self.max_attempts and
            self.status in [WebhookStatus.PENDING, WebhookStatus.FAILED, WebhookStatus.RETRYING]
        )

    def calculate_backoff(self) -> timedelta:
        """Calculate exponential backoff delay"""
        # Exponential backoff: 1s, 2s, 4s, 8s, 16s
        delay_seconds = 2 ** self.attempt_count
        return timedelta(seconds=min(delay_seconds, 300))  # Max 5 minutes

    def mark_attempt(self, status: WebhookStatus, error: Optional[str] = None,
                    response_status: Optional[int] = None, response_body: Optional[str] = None):
        """Mark delivery attempt"""
        self.attempt_count += 1
        self.status = status
        self.last_attempt = datetime.now()
        self.last_error = error
        self.response_status = response_status
        self.response_body = response_body

        if self.should_retry():
            self.next_attempt = self.last_attempt + self.calculate_backoff()
        else:
            self.next_attempt = None


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
    total_deliveries: int = 0
    failed_deliveries: int = 0
    description: Optional[str] = None
    filters: Dict[str, Any] = field(default_factory=dict)  # Event filtering rules

    def should_deliver(self, event: WebhookEvent, payload: Dict[str, Any]) -> bool:
        """Check if webhook should receive this event"""
        if not self.is_active:
            return False

        if event not in self.events:
            return False

        # Apply filters
        return self._matches_filters(payload)

    def _matches_filters(self, payload: Dict[str, Any]) -> bool:
        """Check if payload matches subscription filters"""
        for key, expected_value in self.filters.items():
            if key not in payload:
                return False

            actual_value = payload[key]
            if isinstance(expected_value, dict):
                # Nested filter matching
                if not isinstance(actual_value, dict):
                    return False
                if not self._matches_nested_filter(actual_value, expected_value):
                    return False
            elif actual_value != expected_value:
                return False

        return True

    def _matches_nested_filter(self, actual: Dict[str, Any], expected: Dict[str, Any]) -> bool:
        """Check nested filter matching"""
        for key, expected_value in expected.items():
            if key not in actual or actual[key] != expected_value:
                return False
        return True


@dataclass
class DeadLetterEntry:
    """Dead letter queue entry"""
    delivery_id: str
    subscription_id: str
    event: WebhookEvent
    payload: Dict[str, Any]
    reason: str
    failed_at: datetime
    error_details: Optional[str] = None


class WebhookSystem:
    """Complete webhook delivery system with retry logic and dead letter queues"""

    def __init__(self, max_concurrent_deliveries: int = 10):
        self.logger = logging.getLogger(__name__)

        # Webhook subscriptions
        self.subscriptions: Dict[str, WebhookSubscription] = {}

        # Delivery queues
        self.pending_deliveries: asyncio.Queue = asyncio.Queue()
        self.retry_deliveries: Dict[str, WebhookDelivery] = {}

        # Dead letter queue
        self.dead_letter_queue: deque = deque(maxlen=1000)  # Keep last 1000 failed deliveries

        # Delivery tracking
        self.delivery_history: Dict[str, WebhookDelivery] = {}
        self.max_history_size = 10000

        # Processing control
        self.max_concurrent_deliveries = max_concurrent_deliveries
        self.delivery_semaphore = asyncio.Semaphore(max_concurrent_deliveries)
        self.is_running = False
        self.delivery_task: Optional[asyncio.Task] = None
        self.retry_task: Optional[asyncio.Task] = None

        # HTTP client session
        self.session: Optional[aiohttp.ClientSession] = None

        # Statistics
        self.stats = {
            'total_deliveries': 0,
            'successful_deliveries': 0,
            'failed_deliveries': 0,
            'retry_deliveries': 0,
            'dead_letter_count': 0
        }

    async def initialize(self):
        """Initialize the webhook system"""
        self.logger.info("Initializing webhook system")

        if AIOHTTP_AVAILABLE:
            # Configure HTTP client with connection pooling
            connector = aiohttp.TCPConnector(
                limit=self.max_concurrent_deliveries,
                limit_per_host=self.max_concurrent_deliveries,
                ttl_dns_cache=300,
                use_dns_cache=True
            )

            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=30, connect=10)
            )

        # Start delivery processing
        self.is_running = True
        self.delivery_task = asyncio.create_task(self._process_deliveries())
        self.retry_task = asyncio.create_task(self._process_retries())

        self.logger.info("Webhook system initialized")

    async def shutdown(self):
        """Shutdown the webhook system"""
        self.logger.info("Shutting down webhook system")

        self.is_running = False

        # Cancel tasks
        if self.delivery_task:
            self.delivery_task.cancel()
            try:
                await self.delivery_task
            except asyncio.CancelledError:
                pass

        if self.retry_task:
            self.retry_task.cancel()
            try:
                await self.retry_task
            except asyncio.CancelledError:
                pass

        # Close HTTP session
        if self.session:
            await self.session.close()

        self.logger.info("Webhook system shutdown complete")

    def create_subscription(self, url: str, events: List[WebhookEvent],
                          user_id: str, description: Optional[str] = None,
                          filters: Optional[Dict[str, Any]] = None) -> WebhookSubscription:
        """Create a new webhook subscription"""
        subscription = WebhookSubscription(
            subscription_id=str(uuid.uuid4()),
            url=url,
            events=events,
            secret=secrets.token_hex(32),
            user_id=user_id,
            description=description,
            filters=filters or {}
        )

        self.subscriptions[subscription.subscription_id] = subscription
        self.logger.info(f"Created webhook subscription {subscription.subscription_id} for user {user_id}")

        return subscription

    def update_subscription(self, subscription_id: str, updates: Dict[str, Any]) -> bool:
        """Update webhook subscription"""
        if subscription_id not in self.subscriptions:
            return False

        subscription = self.subscriptions[subscription_id]

        for key, value in updates.items():
            if hasattr(subscription, key):
                setattr(subscription, key, value)

        self.logger.info(f"Updated webhook subscription {subscription_id}")
        return True

    def delete_subscription(self, subscription_id: str) -> bool:
        """Delete webhook subscription"""
        if subscription_id in self.subscriptions:
            del self.subscriptions[subscription_id]
            self.logger.info(f"Deleted webhook subscription {subscription_id}")
            return True
        return False

    def get_subscription(self, subscription_id: str) -> Optional[WebhookSubscription]:
        """Get webhook subscription"""
        return self.subscriptions.get(subscription_id)

    def list_subscriptions(self, user_id: Optional[str] = None) -> List[WebhookSubscription]:
        """List webhook subscriptions"""
        subscriptions = list(self.subscriptions.values())

        if user_id:
            subscriptions = [s for s in subscriptions if s.user_id == user_id]

        return subscriptions

    async def trigger_event(self, event: WebhookEvent, payload: Dict[str, Any],
                          user_id: Optional[str] = None):
        """Trigger webhook event for all matching subscriptions"""
        self.logger.debug(f"Triggering webhook event: {event.value}")

        # Find matching subscriptions
        matching_subscriptions = []
        for subscription in self.subscriptions.values():
            if user_id and subscription.user_id != user_id:
                continue

            if subscription.should_deliver(event, payload):
                matching_subscriptions.append(subscription)

        if not matching_subscriptions:
            self.logger.debug(f"No matching subscriptions for event {event.value}")
            return

        # Create deliveries for each subscription
        for subscription in matching_subscriptions:
            await self._queue_delivery(subscription, event, payload)

    async def _queue_delivery(self, subscription: WebhookSubscription,
                            event: WebhookEvent, payload: Dict[str, Any]):
        """Queue webhook delivery"""
        # Create signature
        payload_str = json.dumps(payload, sort_keys=True, default=str)
        signature = hmac.new(
            subscription.secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()

        delivery = WebhookDelivery(
            delivery_id=str(uuid.uuid4()),
            subscription_id=subscription.subscription_id,
            event=event,
            payload=payload,
            signature=signature
        )

        # Add to pending queue
        await self.pending_deliveries.put(delivery)
        self.delivery_history[delivery.delivery_id] = delivery

        # Maintain history size
        if len(self.delivery_history) > self.max_history_size:
            # Remove oldest entries
            oldest_keys = sorted(
                self.delivery_history.keys(),
                key=lambda k: self.delivery_history[k].created_at
            )[:100]  # Remove 100 oldest

            for key in oldest_keys:
                del self.delivery_history[key]

        self.logger.debug(f"Queued webhook delivery {delivery.delivery_id} for subscription {subscription.subscription_id}")

    async def _process_deliveries(self):
        """Process pending webhook deliveries"""
        while self.is_running:
            try:
                # Get delivery from queue
                delivery = await self.pending_deliveries.get()

                # Acquire semaphore for concurrent limit
                async with self.delivery_semaphore:
                    await self._deliver_webhook(delivery)

                self.pending_deliveries.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error processing webhook delivery: {e}")
                await asyncio.sleep(1)

    async def _deliver_webhook(self, delivery: WebhookDelivery):
        """Deliver webhook to endpoint"""
        if not self.session:
            self.logger.error("HTTP session not available for webhook delivery")
            return

        subscription = self.subscriptions.get(delivery.subscription_id)
        if not subscription:
            self.logger.warning(f"Subscription {delivery.subscription_id} not found for delivery {delivery.delivery_id}")
            return

        try:
            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'X-Webhook-Signature': delivery.signature,
                'X-Webhook-Event': delivery.event.value,
                'X-Webhook-Delivery': delivery.delivery_id,
                'X-Webhook-Subscription': delivery.subscription_id,
                'User-Agent': 'ComfyStudio-Webhook/1.0'
            }

            self.logger.debug(f"Delivering webhook to {subscription.url}")

            # Send request
            async with self.session.post(
                subscription.url,
                json=delivery.payload,
                headers=headers
            ) as response:

                response_body = await response.text()
                delivery.mark_attempt(
                    WebhookStatus.DELIVERED if response.ok else WebhookStatus.FAILED,
                    response_body if not response.ok else None,
                    response.status,
                    response_body
                )

                if response.ok:
                    # Successful delivery
                    self.stats['total_deliveries'] += 1
                    self.stats['successful_deliveries'] += 1
                    subscription.total_deliveries += 1
                    subscription.last_delivery = datetime.now()

                    self.logger.debug(f"Webhook delivered successfully: {delivery.delivery_id}")
                else:
                    # Failed delivery
                    await self._handle_delivery_failure(delivery, subscription, response.status, response_body)

        except asyncio.TimeoutError:
            await self._handle_delivery_failure(delivery, subscription, None, "Timeout")
        except aiohttp.ClientError as e:
            await self._handle_delivery_failure(delivery, subscription, None, str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error delivering webhook: {e}")
            await self._handle_delivery_failure(delivery, subscription, None, str(e))

    async def _handle_delivery_failure(self, delivery: WebhookDelivery,
                                     subscription: WebhookSubscription,
                                     status: Optional[int], error: str):
        """Handle webhook delivery failure"""
        self.logger.warning(f"Webhook delivery failed: {delivery.delivery_id} - {error}")

        delivery.mark_attempt(WebhookStatus.FAILED, error, status)

        if delivery.should_retry():
            # Queue for retry
            delivery.status = WebhookStatus.RETRYING
            self.retry_deliveries[delivery.delivery_id] = delivery
            self.stats['retry_deliveries'] += 1

            self.logger.debug(f"Queued webhook for retry: {delivery.delivery_id}")
        else:
            # Move to dead letter queue
            await self._move_to_dead_letter(delivery, f"Max retries exceeded: {error}")

        self.stats['failed_deliveries'] += 1
        subscription.failed_deliveries += 1

    async def _move_to_dead_letter(self, delivery: WebhookDelivery, reason: str):
        """Move delivery to dead letter queue"""
        dead_letter = DeadLetterEntry(
            delivery_id=delivery.delivery_id,
            subscription_id=delivery.subscription_id,
            event=delivery.event,
            payload=delivery.payload,
            reason=reason,
            failed_at=datetime.now(),
            error_details=delivery.last_error
        )

        self.dead_letter_queue.append(dead_letter)
        self.stats['dead_letter_count'] += 1

        self.logger.warning(f"Moved delivery to dead letter queue: {delivery.delivery_id} - {reason}")

    async def _process_retries(self):
        """Process retry deliveries"""
        while self.is_running:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds

                current_time = datetime.now()
                ready_retries = []

                # Find deliveries ready for retry
                for delivery_id, delivery in list(self.retry_deliveries.items()):
                    if delivery.next_attempt and current_time >= delivery.next_attempt:
                        ready_retries.append(delivery_id)

                # Process ready retries
                for delivery_id in ready_retries:
                    delivery = self.retry_deliveries.pop(delivery_id)
                    await self.pending_deliveries.put(delivery)

                    self.logger.debug(f"Retrying webhook delivery: {delivery_id}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error processing webhook retries: {e}")
                await asyncio.sleep(5)

    def get_delivery_stats(self) -> Dict[str, Any]:
        """Get webhook delivery statistics"""
        total_subscriptions = len(self.subscriptions)
        active_subscriptions = len([s for s in self.subscriptions.values() if s.is_active])

        # Calculate success rate
        total_attempts = self.stats['total_deliveries'] + self.stats['failed_deliveries']
        success_rate = (self.stats['successful_deliveries'] / total_attempts * 100) if total_attempts > 0 else 0

        # Calculate average delivery time (simplified)
        recent_deliveries = [
            d for d in self.delivery_history.values()
            if d.status == WebhookStatus.DELIVERED and d.last_attempt
        ][:100]  # Last 100 successful deliveries

        avg_delivery_time = 0
        if recent_deliveries:
            delivery_times = [
                (d.last_attempt - d.created_at).total_seconds()
                for d in recent_deliveries
            ]
            avg_delivery_time = statistics.mean(delivery_times)

        return {
            'total_subscriptions': total_subscriptions,
            'active_subscriptions': active_subscriptions,
            'total_deliveries': self.stats['total_deliveries'],
            'successful_deliveries': self.stats['successful_deliveries'],
            'failed_deliveries': self.stats['failed_deliveries'],
            'retry_deliveries': self.stats['retry_deliveries'],
            'dead_letter_count': len(self.dead_letter_queue),
            'success_rate': round(success_rate, 2),
            'avg_delivery_time': round(avg_delivery_time, 2),
            'pending_deliveries': self.pending_deliveries.qsize(),
            'retry_queue_size': len(self.retry_deliveries)
        }

    def get_dead_letter_queue(self, limit: int = 50) -> List[DeadLetterEntry]:
        """Get dead letter queue entries"""
        return list(self.dead_letter_queue)[-limit:]

    def replay_dead_letter(self, delivery_id: str) -> bool:
        """Replay a dead letter delivery"""
        for entry in self.dead_letter_queue:
            if entry.delivery_id == delivery_id:
                # Recreate delivery
                subscription = self.subscriptions.get(entry.subscription_id)
                if subscription:
                    asyncio.create_task(self.trigger_event(
                        entry.event,
                        entry.payload,
                        subscription.user_id
                    ))
                    return True
        return False


# Global instance
_webhook_system = None

def get_webhook_system() -> WebhookSystem:
    """Get global webhook system instance"""
    global _webhook_system
    if _webhook_system is None:
        _webhook_system = WebhookSystem()
    return _webhook_system

async def initialize_webhook_system(max_concurrent_deliveries: int = 10) -> WebhookSystem:
    """Initialize the global webhook system"""
    global _webhook_system
    if _webhook_system is None:
        _webhook_system = WebhookSystem(max_concurrent_deliveries)
        await _webhook_system.initialize()
    return _webhook_system</content>
<parameter name="filePath">c:\Users\Baxter\Documents\ComfyUI_env\ComfyUI\custom_nodes\Comfy Gimpy Node Pack\advanced_ai\webhook_system.py