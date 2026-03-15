"""Health and readiness endpoints."""

from fastapi import APIRouter

from ..config import settings
from ..session_store import session_store

router = APIRouter()


@router.get("/health")
async def health():
    """Liveness check. Returns 200 if the service is running."""
    redis_ok = await session_store.ping()
    return {
        "status": "healthy" if redis_ok else "degraded",
        "service": "orchestrator",
        "redis": "connected" if redis_ok else "disconnected",
        "mock_mode": settings.MOCK_MODE,
        "vapi_configured": settings.vapi_configured,
    }


@router.get("/ready")
async def ready():
    """Readiness check. Returns 200 only if all dependencies are available."""
    redis_ok = await session_store.ping()
    if not redis_ok:
        return {"status": "not_ready", "reason": "redis_unavailable"}
    return {"status": "ready"}
