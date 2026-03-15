"""Redis-backed session store for voice agent conversations.

Each active call has a session in Redis containing the full customer context
and conversation state. Sessions expire after 1 hour (configurable).
The agent is stateless across sessions but stateful within a session.
"""

import json
import logging
import uuid
from datetime import datetime, timezone

import redis.asyncio as redis

from .config import settings
from .models import CustomerContext, OnboardingStage, SessionState, ConversationState

log = logging.getLogger("orchestrator.session")


class SessionStore:
    def __init__(self):
        self._redis: redis.Redis | None = None

    async def connect(self):
        self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        log.info(f"Session store connected to Redis at {settings.REDIS_URL}")

    async def close(self):
        if self._redis:
            await self._redis.close()

    def _key(self, session_id: str) -> str:
        return f"session:{session_id}"

    async def create(self, customer_id: str, context: CustomerContext) -> SessionState:
        """Create a new session for a voice interaction."""
        now = datetime.now(timezone.utc)
        session = SessionState(
            session_id=f"sess-{uuid.uuid4().hex[:12]}",
            customer_id=customer_id,
            conversation_state=ConversationState.INIT,
            onboarding_stage=context.onboarding_stage,
            context=context,
            started_at=now,
            last_updated=now,
        )
        await self._redis.setex(
            self._key(session.session_id),
            settings.SESSION_TTL_SECONDS,
            session.model_dump_json(),
        )
        log.info(f"Session created: {session.session_id} for customer {customer_id}")
        return session

    async def get(self, session_id: str) -> SessionState | None:
        """Retrieve a session by ID."""
        data = await self._redis.get(self._key(session_id))
        if not data:
            return None
        return SessionState.model_validate_json(data)

    async def update(self, session: SessionState) -> None:
        """Update a session. Resets TTL."""
        session.last_updated = datetime.now(timezone.utc)
        await self._redis.setex(
            self._key(session.session_id),
            settings.SESSION_TTL_SECONDS,
            session.model_dump_json(),
        )

    async def delete(self, session_id: str) -> None:
        """Delete a session (call ended)."""
        await self._redis.delete(self._key(session_id))
        log.info(f"Session deleted: {session_id}")

    async def ping(self) -> bool:
        """Health check."""
        try:
            return await self._redis.ping()
        except Exception:
            return False


session_store = SessionStore()
