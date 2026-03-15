"""Tests for the decision engine."""

from orchestrator.src.decision_engine import decision_engine
from orchestrator.src.models import OnboardingStage


class TestDecisionEngine:

    def test_first_contact_should_call(self, ekyc_customer):
        decision = decision_engine.decide(ekyc_customer)
        assert decision.should_call
        assert decision.delay_seconds == 0  # first attempt, immediate
        assert decision.channel == "voice"

    def test_no_consent_blocks_call(self, no_consent_customer):
        decision = decision_engine.decide(no_consent_customer)
        assert not decision.should_call
        assert decision.channel == "sms"
        assert "Consent" in decision.reason

    def test_max_attempts_stops_calling(self, ekyc_customer):
        ekyc_customer.call_attempt_count = 5
        decision = decision_engine.decide(ekyc_customer)
        assert not decision.should_call
        assert "Max attempts" in decision.reason

    def test_completed_stage_skipped(self, ekyc_customer):
        ekyc_customer.onboarding_stage = OnboardingStage.COMPLETED
        decision = decision_engine.decide(ekyc_customer)
        assert not decision.should_call

    def test_activation_higher_priority_than_ekyc(self, ekyc_customer, activation_customer):
        ekyc_decision = decision_engine.decide(ekyc_customer)
        activation_decision = decision_engine.decide(activation_customer)
        assert activation_decision.priority < ekyc_decision.priority  # lower = higher priority

    def test_backoff_on_second_attempt(self, ekyc_customer):
        ekyc_customer.call_attempt_count = 1
        decision = decision_engine.decide(ekyc_customer)
        assert decision.should_call
        assert decision.delay_seconds == 4 * 3600  # 4 hours

    def test_high_value_customer_priority_boost(self, activation_customer):
        # 300K limit customer gets a priority boost
        decision = decision_engine.decide(activation_customer)
        low_limit = activation_customer.model_copy()
        low_limit.credit_limit = 50000
        decision_low = decision_engine.decide(low_limit)
        assert decision.priority < decision_low.priority
