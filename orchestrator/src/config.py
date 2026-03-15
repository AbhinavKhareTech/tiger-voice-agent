"""Application configuration loaded from environment variables."""

import os


class Settings:
    PORT: int = int(os.getenv("PORT", "8000"))
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    MOCK_BACKENDS_URL: str = os.getenv("MOCK_BACKENDS_URL", "http://localhost:8001")
    VAPI_API_KEY: str = os.getenv("VAPI_API_KEY", "")
    VAPI_ASSISTANT_ID: str = os.getenv("VAPI_ASSISTANT_ID", "")
    VAPI_PHONE_NUMBER_ID: str = os.getenv("VAPI_PHONE_NUMBER_ID", "")
    MOCK_MODE: bool = os.getenv("MOCK_MODE", "true").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Operational thresholds
    MAX_CALL_ATTEMPTS: int = 5
    COOLDOWN_HOURS: int = 24
    MAX_OBJECTIONS_BEFORE_ESCALATE: int = 3
    DEDUP_TTL_SECONDS: int = 7 * 24 * 3600  # 7 days
    SESSION_TTL_SECONDS: int = 3600  # 1 hour

    @property
    def vapi_configured(self) -> bool:
        return bool(self.VAPI_API_KEY and self.VAPI_ASSISTANT_ID)


settings = Settings()
