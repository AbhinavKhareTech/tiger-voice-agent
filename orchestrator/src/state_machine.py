"""Conversation state machine for the voice agent.

The state machine governs what the agent is allowed to do at each point
in the conversation. System state (onboarding_stage) determines which
STAGE_FLOW the agent enters. Conversation state resets with each call.

State transitions are deterministic and logged for audit.
"""

import logging
from datetime import datetime, timezone

from .models import ConversationState, SessionState, OnboardingStage
from .config import settings

log = logging.getLogger("orchestrator.state_machine")

# Valid transitions: current_state -> set of allowed next states
TRANSITIONS: dict[ConversationState, set[ConversationState]] = {
    ConversationState.INIT: {
        ConversationState.COMPLIANCE_CHECK,
        ConversationState.BLOCKED,
    },
    ConversationState.COMPLIANCE_CHECK: {
        ConversationState.GREETING,
        ConversationState.BLOCKED,
    },
    ConversationState.BLOCKED: {
        ConversationState.END,
    },
    ConversationState.GREETING: {
        ConversationState.IDENTITY_VERIFY,
        ConversationState.RETRY,
    },
    ConversationState.IDENTITY_VERIFY: {
        ConversationState.STAGE_FLOW,
        ConversationState.ESCALATE,
    },
    ConversationState.STAGE_FLOW: {
        ConversationState.CONFIRMATION,
        ConversationState.OBJECTION_HANDLER,
        ConversationState.TOOL_EXECUTION,
        ConversationState.ESCALATE,
    },
    ConversationState.TOOL_EXECUTION: {
        ConversationState.STAGE_FLOW,
        ConversationState.ESCALATE,
    },
    ConversationState.OBJECTION_HANDLER: {
        ConversationState.STAGE_FLOW,
        ConversationState.ESCALATE,
    },
    ConversationState.CONFIRMATION: {
        ConversationState.WRAP_UP,
    },
    ConversationState.ESCALATE: {
        ConversationState.END,
    },
    ConversationState.RETRY: {
        ConversationState.END,
    },
    ConversationState.WRAP_UP: {
        ConversationState.END,
    },
    ConversationState.END: set(),  # terminal
}


class StateMachine:
    """Manages conversation state transitions with validation and logging."""

    @staticmethod
    def transition(session: SessionState, new_state: ConversationState) -> bool:
        """Attempt a state transition. Returns True if valid, False if rejected."""
        current = session.conversation_state
        allowed = TRANSITIONS.get(current, set())

        if new_state not in allowed:
            log.warning(
                f"Invalid transition rejected: {current.value} -> {new_state.value} "
                f"(session={session.session_id})"
            )
            return False

        old_state = session.conversation_state
        session.conversation_state = new_state
        session.last_updated = datetime.now(timezone.utc)

        log.info(
            f"State transition: {old_state.value} -> {new_state.value} "
            f"(session={session.session_id}, customer={session.customer_id})"
        )
        return True

    @staticmethod
    def can_transition(session: SessionState, new_state: ConversationState) -> bool:
        """Check if a transition is valid without executing it."""
        allowed = TRANSITIONS.get(session.conversation_state, set())
        return new_state in allowed

    @staticmethod
    def should_escalate(session: SessionState) -> bool:
        """Determine if the conversation should escalate to a human agent.

        Triggers:
        - 3+ unresolved objections
        - 10+ tool calls (indicates confused reasoning)
        """
        if session.objection_count >= settings.MAX_OBJECTIONS_BEFORE_ESCALATE:
            return True
        if session.tool_call_count >= 10:
            return True
        return False

    @staticmethod
    def get_stage_flow(stage: OnboardingStage) -> str:
        """Return the conversation flow identifier for a given onboarding stage."""
        return {
            OnboardingStage.EKYC_PENDING: "ekyc_flow",
            OnboardingStage.VKYC_PENDING: "vkyc_flow",
            OnboardingStage.ACTIVATION_PENDING: "activation_flow",
            OnboardingStage.CARD_ACTIVE: "active_flow",
        }.get(stage, "unknown_flow")

    @staticmethod
    def is_terminal(state: ConversationState) -> bool:
        """Check if a state is terminal (no further transitions possible)."""
        return state == ConversationState.END


state_machine = StateMachine()
