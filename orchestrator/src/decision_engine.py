"""Decision engine: computes the next-best-action for a customer.

Given a customer's context (stage, call history, engagement signals),
the engine determines: should we call now? what priority? what flow?

This is the business logic layer that sits between events and actions.
"""

import logging

from .models import CustomerContext, OnboardingStage

log = logging.getLogger("orchestrator.decision")


class CallDecision:
    """Result of a next-best-action computation."""

    def __init__(
        self,
        should_call: bool,
        priority: int = 50,
        reason: str = "",
        delay_seconds: int = 0,
        channel: str = "voice",
    ):
        self.should_call = should_call
        self.priority = priority  # 0 = highest, 100 = lowest
        self.reason = reason
        self.delay_seconds = delay_seconds
        self.channel = channel  # "voice" or "sms"

    def to_dict(self) -> dict:
        return {
            "should_call": self.should_call,
            "priority": self.priority,
            "reason": self.reason,
            "delay_seconds": self.delay_seconds,
            "channel": self.channel,
        }


class DecisionEngine:
    """Computes call priority and timing based on customer context."""

    # Stage priority: closer to activation = higher priority
    STAGE_PRIORITY = {
        OnboardingStage.ACTIVATION_PENDING: 10,
        OnboardingStage.VKYC_PENDING: 30,
        OnboardingStage.EKYC_PENDING: 50,
        OnboardingStage.CARD_ACTIVE: 70,
        OnboardingStage.COMPLETED: 100,
    }

    # Backoff schedule based on attempt count (seconds)
    BACKOFF_SCHEDULE = {
        0: 0,           # First attempt: immediate
        1: 4 * 3600,    # 4 hours
        2: 24 * 3600,   # 24 hours
        3: 72 * 3600,   # 72 hours
        4: 168 * 3600,  # 7 days
    }

    MAX_ATTEMPTS = 5

    def decide(self, context: CustomerContext) -> CallDecision:
        """Determine whether and when to call this customer."""

        # Already completed
        if context.onboarding_stage == OnboardingStage.COMPLETED:
            return CallDecision(
                should_call=False,
                reason="Onboarding already completed",
            )

        # No consent
        if not context.consent_status:
            return CallDecision(
                should_call=False,
                channel="sms",
                reason="Consent not provided; SMS-only engagement",
            )

        # Max attempts exceeded
        if context.call_attempt_count >= self.MAX_ATTEMPTS:
            return CallDecision(
                should_call=False,
                channel="sms",
                reason=f"Max attempts ({self.MAX_ATTEMPTS}) exceeded; assign to human sales",
            )

        # Calculate backoff delay
        delay = self.BACKOFF_SCHEDULE.get(
            context.call_attempt_count,
            self.BACKOFF_SCHEDULE[4],
        )

        # Compute priority
        base_priority = self.STAGE_PRIORITY.get(context.onboarding_stage, 50)

        # Adjust for engagement signals
        priority = base_priority
        if context.call_attempt_count == 0:
            priority -= 10  # First contact gets boost
        if context.call_attempt_count >= 3:
            priority += 20  # Repeated attempts get deprioritized

        # High-value customers get a boost
        if context.credit_limit >= 300000:
            priority -= 5

        priority = max(0, min(100, priority))

        return CallDecision(
            should_call=True,
            priority=priority,
            delay_seconds=delay,
            reason=f"Stage={context.onboarding_stage.value}, attempt={context.call_attempt_count + 1}",
        )


decision_engine = DecisionEngine()
