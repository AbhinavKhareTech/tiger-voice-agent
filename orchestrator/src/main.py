"""Tiger Voice Agent Orchestrator - FastAPI Application.

The orchestration layer sits between the voice AI agent and Tiger's
enterprise systems. It manages conversation state, enforces compliance,
routes tool calls, and consumes stage-change events.

Architecture:
  Vapi (voice agent) -> webhook -> tool router -> mock backends
  Redis (events)     -> consumer -> pipeline  -> mock backends
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .session_store import session_store
from .dedup import dedup_cache
from .compliance_gateway import compliance_gateway
from .event_consumer import start_consumer
from .routes.health import router as health_router
from .routes.events import router as events_router
from .routes.vapi_webhook import router as vapi_router

# ---- Logging ----
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
log = logging.getLogger("orchestrator")


# ---- Lifespan ----

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: connect to Redis, start event consumer.
    Shutdown: close connections gracefully.
    """
    log.info("Starting Tiger Voice Agent Orchestrator...")
    log.info(f"  Mock mode: {settings.MOCK_MODE}")
    log.info(f"  Vapi configured: {settings.vapi_configured}")
    log.info(f"  Redis: {settings.REDIS_URL}")
    log.info(f"  Backends: {settings.MOCK_BACKENDS_URL}")

    # Connect to Redis
    await session_store.connect()
    await dedup_cache.connect()
    await compliance_gateway.connect()
    log.info("All connections established")

    # Start event consumer as background task
    consumer_task = asyncio.create_task(start_consumer())

    yield

    # Shutdown
    log.info("Shutting down...")
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    await session_store.close()
    await dedup_cache.close()
    await compliance_gateway.close()
    log.info("Shutdown complete")


# ---- App ----

app = FastAPI(
    title="Tiger Voice Agent Orchestrator",
    version="0.1.0",
    description=(
        "Orchestration layer for the Tiger Credit Card AI voice agent. "
        "Manages conversation state, enforces compliance, routes tool calls, "
        "and processes stage-change events."
    ),
    lifespan=lifespan,
)

# Register routes
app.include_router(health_router)
app.include_router(events_router)
app.include_router(vapi_router)


@app.get("/")
async def root():
    return {
        "service": "Tiger Voice Agent Orchestrator",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "webhook": "/api/vapi/webhook",
        "events": "/api/events/publish",
    }
