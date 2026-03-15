"""Idempotency cache for event deduplication.

Every event carries a unique event_id. Before processing, we check this cache.
If the event_id has been seen, we skip it. This prevents duplicate outbound
calls caused by Kafka's at-least-once delivery during rebalancing.

Uses Redis with a 7-day TTL so old event IDs are automatically cleaned up.
"""

import logging

import redis.asyncio as redis

from .config import settings

log = logging.getLogger("orchestrator.dedup")


class DedupCache:
    def __init__(self):
        self._redis: redis.Redis | None = None

    async def connect(self):
        self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def close(self):
        if self._redis:
            await self._redis.close()

    def _key(self, event_id: str) -> str:
        return f"dedup:{event_id}"

    async def is_duplicate(self, event_id: str) -> bool:
        """Check if this event has already been processed."""
        exists = await self._redis.exists(self._key(event_id))
        if exists:
            log.info(f"Duplicate event detected: {event_id}")
        return bool(exists)

    async def mark_processed(self, event_id: str) -> None:
        """Mark an event as processed. TTL prevents unbounded growth."""
        await self._redis.setex(
            self._key(event_id),
            settings.DEDUP_TTL_SECONDS,
            "1",
        )
        log.debug(f"Event marked processed: {event_id}")


dedup_cache = DedupCache()
