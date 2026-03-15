"""Shared test fixtures."""

import pytest
from datetime import datetime, timezone

from orchestrator.src.models import (
    CustomerContext, KYCStatus, CardDetails, OnboardingStage,
    SessionState, ConversationState, StageChangeEvent,
)


@pytest.fixture
def ekyc_customer() -> CustomerContext:
    return CustomerContext(
        customer_id="TC001",
        customer_name="Priya Sharma",
        phone="XXXXXX3210",
        onboarding_stage=OnboardingStage.EKYC_PENDING,
        credit_limit=150000,
        risk_tier="LOW",
        limit_revision_eligible=True,
        kyc_status=KYCStatus(ekyc_done=False, vkyc_done=False),
        consent_status=True,
        call_attempt_count=0,
        campaign_source="instagram_reels_q1",
    )


@pytest.fixture
def activation_customer() -> CustomerContext:
    return CustomerContext(
        customer_id="TC005",
        customer_name="Deepika Nair",
        phone="XXXXXX3214",
        onboarding_stage=OnboardingStage.ACTIVATION_PENDING,
        credit_limit=300000,
        risk_tier="LOW",
        limit_revision_eligible=True,
        kyc_status=KYCStatus(ekyc_done=True, vkyc_done=True, vkyc_attempts=1),
        card_details=CardDetails(virtual_card_ready=True, physical_card_eta="2026-03-18"),
        consent_status=True,
        call_attempt_count=0,
    )


@pytest.fixture
def no_consent_customer() -> CustomerContext:
    return CustomerContext(
        customer_id="TC008",
        customer_name="Ravi Kumar",
        phone="XXXXXX3217",
        onboarding_stage=OnboardingStage.EKYC_PENDING,
        credit_limit=125000,
        consent_status=False,
        call_attempt_count=0,
    )


@pytest.fixture
def init_session(ekyc_customer) -> SessionState:
    return SessionState(
        session_id="sess-test-001",
        customer_id="TC001",
        conversation_state=ConversationState.INIT,
        onboarding_stage=OnboardingStage.EKYC_PENDING,
        context=ekyc_customer,
        started_at=datetime.now(timezone.utc),
        last_updated=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_event() -> StageChangeEvent:
    return StageChangeEvent(
        event_id="evt-test-001",
        event_type="card_approved",
        customer_id="TC001",
        timestamp=datetime.now(timezone.utc),
        source_system="credit_decision_engine",
        correlation_id="corr-test-001",
    )
