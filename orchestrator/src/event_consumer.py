"""Event consumer: listens for stage-change events and triggers voice interactions.

In production, this would consume from Kafka. For the demo, we use Redis
pub/sub which provides the same event-driven semantics without requiring
a Kafka cluster in Docker compose.

The consumer follows this pipeline:
  1. Receive event
  2. Dedup check (skip if already processed)
  3. Enrich with customer context from backends
  4. Run compliance pre-call checks
  5. Compute next-best-action (call now, delay, skip)
  6. If call: create session + initiate voice interaction
"""

import asyncio
import json
import logging

import httpx
import redis.asyncio as redis

from .config import settings
from .dedup import dedup_cache
from .compliance_gateway import compliance_gateway
from .decision_engine import decision_engine
from .session_store import session_store
from .models import (
    StageChangeEvent,
    CustomerContext,
    KYCStatus,
    CardDetails,
    OnboardingStage,
)

log = logging.getLogger("orchestrator.events")

CHANNEL = "tiger:stage_events"


async def build_customer_context(customer_id: str) -> CustomerContext | None:
    """Assemble full customer context from mock backend APIs."""
    base_url = settings.MOCK_BACKENDS_URL
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=5.0) as client:
            # Fetch customer profile
            resp = await client.get(f"/api/customers/{customer_id}")
            resp.raise_for_status()
            profile = resp.json()

            # Fetch CRM history
            crm_resp = await client.get(f"/api/crm/{customer_id}/history")
            crm_resp.raise_for_status()
            crm = crm_resp.json()

        # Apply PII masking
        masked = compliance_gateway.mask_pii(profile)

        return CustomerContext(
            customer_id=customer_id,
            customer_name=profile["name"],
            phone=masked.get("phone", ""),
            language_preference=profile.get("language_preference", "en"),
            onboarding_stage=OnboardingStage(profile["onboarding_stage"]),
            credit_limit=profile.get("credit_limit", 0),
            risk_tier=profile.get("risk_tier", "MEDIUM"),
            limit_revision_eligible=profile.get("limit_revision_eligible", False),
            kyc_status=KYCStatus(**profile.get("kyc_status", {})),
            card_details=CardDetails(**profile.get("card_details", {})),
            welcome_reward_status=profile.get("welcome_reward_status", "pending"),
            campaign_source=crm.get("campaign_source", ""),
            consent_status=profile.get("consent_status", False),
            call_attempt_count=crm.get("call_count", 0),
            last_call_attempt=crm["last_call"]["timestamp"] if crm.get("last_call") else None,
        )
    except Exception as e:
        log.error(f"Failed to build context for {customer_id}: {e}")
        return None


async def process_event(event: StageChangeEvent) -> dict:
    """Process a single stage-change event through the full pipeline.

    Returns a dict describing the action taken.
    """
    log.info(f"Processing event: {event.event_type} for {event.customer_id} (id={event.event_id})")

    # Step 1: Dedup check
    if await dedup_cache.is_duplicate(event.event_id):
        return {"action": "skipped", "reason": "duplicate_event"}
    await dedup_cache.mark_processed(event.event_id)

    # Step 2: Build customer context
    context = await build_customer_context(event.customer_id)
    if not context:
        return {"action": "failed", "reason": "context_build_failed"}

    # Step 3: Pre-call state refresh (race condition prevention)
    # The customer's stage may have advanced since the event was produced
    if context.onboarding_stage.value != event.metadata.get("expected_stage", context.onboarding_stage.value):
        log.info(
            f"Stage advanced for {event.customer_id}: "
            f"expected={event.metadata.get('expected_stage')}, "
            f"actual={context.onboarding_stage.value}"
        )
        return {"action": "skipped", "reason": "stage_advanced"}

    # Step 4: Compliance check
    compliance = await compliance_gateway.pre_call_check(event.customer_id)
    if not compliance.cleared:
        await compliance_gateway.write_audit_log(
            event.customer_id,
            "call_blocked",
            {"reason": compliance.reason, "checks": compliance.checks},
        )
        return {"action": "blocked", "reason": compliance.reason}

    # Step 5: Decision engine
    decision = decision_engine.decide(context)
    if not decision.should_call:
        return {"action": "skipped", "reason": decision.reason, "channel": decision.channel}

    # Step 6: Create session
    session = await session_store.create(event.customer_id, context)

    # Step 7: Audit log
    await compliance_gateway.write_audit_log(
        event.customer_id,
        "call_initiated",
        {
            "session_id": session.session_id,
            "event_id": event.event_id,
            "stage": context.onboarding_stage.value,
            "priority": decision.priority,
        },
    )

    log.info(
        f"Call scheduled for {event.customer_id}: "
        f"session={session.session_id}, priority={decision.priority}, "
        f"delay={decision.delay_seconds}s"
    )

    return {
        "action": "call_scheduled",
        "session_id": session.session_id,
        "priority": decision.priority,
        "delay_seconds": decision.delay_seconds,
        "stage": context.onboarding_stage.value,
    }


async def start_consumer():
    """Start the Redis pub/sub event consumer.

    Runs as a background task in the FastAPI app. In production,
    this would be a Kafka consumer group.
    """
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe(CHANNEL)
    log.info(f"Event consumer listening on channel: {CHANNEL}")

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                data = json.loads(message["data"])
                event = StageChangeEvent(**data)
                result = await process_event(event)
                log.info(f"Event result: {result}")
            except Exception as e:
                log.error(f"Event processing error: {e}", exc_info=True)
    except asyncio.CancelledError:
        log.info("Event consumer shutting down")
    finally:
        await pubsub.unsubscribe(CHANNEL)
        await r.close()
