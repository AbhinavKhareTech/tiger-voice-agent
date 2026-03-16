"""Event ingestion endpoint.

Accepts stage-change events via HTTP POST (for testing and webhook-based
integrations) and publishes them to the Redis event channel. In production,
events would arrive via Kafka. This endpoint provides an HTTP bridge for
demo and testing scenarios.
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter
import redis.asyncio as redis

from ..config import settings
from ..event_consumer import process_event, CHANNEL
from ..models import StageChangeEvent

log = logging.getLogger("orchestrator.routes.events")

router = APIRouter(prefix="/api/events", tags=["Events"])


@router.post("/publish")
async def publish_event(
    event_type: str,
    customer_id: str,
    source_system: str = "manual",
    metadata: dict | None = None,
):
    """Publish a stage-change event to the event channel.

    This is the HTTP bridge for testing. In production, events arrive via Kafka.
    """
    event = StageChangeEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        customer_id=customer_id,
        timestamp=datetime.now(timezone.utc),
        source_system=source_system,
        correlation_id=str(uuid.uuid4()),
        metadata=metadata or {},
    )

    # Publish to Redis channel
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await r.publish(CHANNEL, event.model_dump_json())
        log.info(f"Event published: {event.event_type} for {event.customer_id}")
        return {
            "status": "published",
            "event_id": event.event_id,
            "event_type": event.event_type,
            "customer_id": event.customer_id,
        }
    finally:
        await r.close()


@router.post("/process")
async def process_event_sync(
    event_type: str,
    customer_id: str,
    source_system: str = "manual",
    metadata: dict | None = None,
):
    """Process an event synchronously (bypassing the pub/sub channel).

    Useful for testing the full pipeline without the event consumer.
    Returns the processing result directly.
    """
    event = StageChangeEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        customer_id=customer_id,
        timestamp=datetime.now(timezone.utc),
        source_system=source_system,
        correlation_id=str(uuid.uuid4()),
        metadata=metadata or {},
    )
    result = await process_event(event)
    return {"event_id": event.event_id, "result": result}
