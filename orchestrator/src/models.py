"""Pydantic models for events, state, API contracts, and Vapi webhook payloads."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---- Onboarding Stages ----

class OnboardingStage(str, Enum):
    EKYC_PENDING = "EKYC_PENDING"
    VKYC_PENDING = "VKYC_PENDING"
    ACTIVATION_PENDING = "ACTIVATION_PENDING"
    CARD_ACTIVE = "CARD_ACTIVE"
    COMPLETED = "COMPLETED"


# ---- Conversation States ----

class ConversationState(str, Enum):
    INIT = "INIT"
    COMPLIANCE_CHECK = "COMPLIANCE_CHECK"
    BLOCKED = "BLOCKED"
    GREETING = "GREETING"
    IDENTITY_VERIFY = "IDENTITY_VERIFY"
    STAGE_FLOW = "STAGE_FLOW"
    OBJECTION_HANDLER = "OBJECTION_HANDLER"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    CONFIRMATION = "CONFIRMATION"
    ESCALATE = "ESCALATE"
    WRAP_UP = "WRAP_UP"
    RETRY = "RETRY"
    END = "END"


# ---- Events ----

class StageChangeEvent(BaseModel):
    event_id: str = Field(description="Unique event ID for idempotency")
    event_type: str = Field(description="e.g. card_approved, ekyc_completed")
    customer_id: str
    timestamp: datetime
    source_system: str
    correlation_id: str = ""
    metadata: dict[str, Any] = {}


# ---- Customer Context (assembled by orchestrator) ----

class KYCStatus(BaseModel):
    ekyc_done: bool = False
    vkyc_done: bool = False
    vkyc_attempts: int = 0
    failure_reason: str | None = None


class CardDetails(BaseModel):
    virtual_card_ready: bool = False
    physical_card_eta: str | None = None
    card_number_masked: str | None = None
    activation_status: str = "INACTIVE"


class CallHistoryEntry(BaseModel):
    timestamp: str
    outcome: str
    agent: str = "AI"
    notes: str = ""


class CustomerContext(BaseModel):
    """Full customer context assembled from multiple enterprise systems.
    This is what gets injected into the voice agent prompt."""
    customer_id: str
    customer_name: str
    phone: str
    language_preference: str = "en"
    onboarding_stage: OnboardingStage
    credit_limit: int = 0
    risk_tier: str = "MEDIUM"
    limit_revision_eligible: bool = False
    kyc_status: KYCStatus = KYCStatus()
    card_details: CardDetails = CardDetails()
    welcome_reward_status: str = "pending"
    campaign_source: str = ""
    consent_status: bool = False
    call_attempt_count: int = 0
    last_call_attempt: str | None = None
    verification_status: str = "pending"


# ---- Session State ----

class SessionState(BaseModel):
    session_id: str
    customer_id: str
    conversation_state: ConversationState = ConversationState.INIT
    onboarding_stage: OnboardingStage
    context: CustomerContext
    objection_count: int = 0
    tool_call_count: int = 0
    identity_verified: bool = False
    started_at: datetime
    last_updated: datetime


# ---- Vapi Webhook Payloads ----

class VapiToolCallPayload(BaseModel):
    """Payload from Vapi when the voice agent invokes a tool function."""
    message: dict[str, Any]


class ToolCallRequest(BaseModel):
    """Parsed tool call from Vapi webhook."""
    tool_call_id: str
    function_name: str
    parameters: dict[str, Any]


class ToolCallResponse(BaseModel):
    """Response sent back to Vapi after tool execution."""
    results: list[dict[str, Any]]


# ---- Compliance Check ----

class ComplianceResult(BaseModel):
    cleared: bool
    checks: dict[str, bool]
    reason: str = ""


# ---- Disposition ----

class DispositionCode(str, Enum):
    EKYC_LINK_SENT = "EKYC_LINK_SENT"
    EKYC_STARTED = "EKYC_STARTED"
    VKYC_SLOT_BOOKED = "VKYC_SLOT_BOOKED"
    VKYC_EXPLAINED = "VKYC_EXPLAINED"
    ACTIVATION_COMPLETED = "ACTIVATION_COMPLETED"
    ACTIVATION_EXPLAINED = "ACTIVATION_EXPLAINED"
    ORIENTATION_COMPLETED = "ORIENTATION_COMPLETED"
    OBJECTION_RESOLVED = "OBJECTION_RESOLVED"
    DEFERRED = "DEFERRED"
    ESCALATED_TO_HUMAN = "ESCALATED_TO_HUMAN"
    NO_ANSWER = "NO_ANSWER"
    CONSENT_BLOCKED = "CONSENT_BLOCKED"
    SOFT_DECLINE = "SOFT_DECLINE"
