"""Tests for the conversation state machine."""

from orchestrator.src.state_machine import state_machine
from orchestrator.src.models import ConversationState, OnboardingStage


class TestStateMachineTransitions:

    def test_init_to_compliance_check(self, init_session):
        assert state_machine.transition(init_session, ConversationState.COMPLIANCE_CHECK)
        assert init_session.conversation_state == ConversationState.COMPLIANCE_CHECK

    def test_init_to_blocked(self, init_session):
        assert state_machine.transition(init_session, ConversationState.BLOCKED)
        assert init_session.conversation_state == ConversationState.BLOCKED

    def test_invalid_transition_rejected(self, init_session):
        # INIT -> STAGE_FLOW is not valid (must go through COMPLIANCE_CHECK first)
        assert not state_machine.transition(init_session, ConversationState.STAGE_FLOW)
        assert init_session.conversation_state == ConversationState.INIT  # unchanged

    def test_greeting_to_identity_verify(self, init_session):
        state_machine.transition(init_session, ConversationState.COMPLIANCE_CHECK)
        state_machine.transition(init_session, ConversationState.GREETING)
        assert state_machine.transition(init_session, ConversationState.IDENTITY_VERIFY)

    def test_stage_flow_to_objection(self, init_session):
        # Walk through the full path
        state_machine.transition(init_session, ConversationState.COMPLIANCE_CHECK)
        state_machine.transition(init_session, ConversationState.GREETING)
        state_machine.transition(init_session, ConversationState.IDENTITY_VERIFY)
        state_machine.transition(init_session, ConversationState.STAGE_FLOW)
        assert state_machine.transition(init_session, ConversationState.OBJECTION_HANDLER)

    def test_objection_back_to_stage_flow(self, init_session):
        state_machine.transition(init_session, ConversationState.COMPLIANCE_CHECK)
        state_machine.transition(init_session, ConversationState.GREETING)
        state_machine.transition(init_session, ConversationState.IDENTITY_VERIFY)
        state_machine.transition(init_session, ConversationState.STAGE_FLOW)
        state_machine.transition(init_session, ConversationState.OBJECTION_HANDLER)
        assert state_machine.transition(init_session, ConversationState.STAGE_FLOW)

    def test_end_is_terminal(self, init_session):
        init_session.conversation_state = ConversationState.END
        assert state_machine.is_terminal(init_session.conversation_state)
        assert not state_machine.transition(init_session, ConversationState.INIT)

    def test_happy_path_full_flow(self, init_session):
        """Test the complete happy path: INIT -> ... -> END."""
        transitions = [
            ConversationState.COMPLIANCE_CHECK,
            ConversationState.GREETING,
            ConversationState.IDENTITY_VERIFY,
            ConversationState.STAGE_FLOW,
            ConversationState.CONFIRMATION,
            ConversationState.WRAP_UP,
            ConversationState.END,
        ]
        for state in transitions:
            assert state_machine.transition(init_session, state), f"Failed at {state.value}"
        assert init_session.conversation_state == ConversationState.END


class TestStateMachineEscalation:

    def test_should_escalate_on_objections(self, init_session):
        init_session.objection_count = 3
        assert state_machine.should_escalate(init_session)

    def test_should_not_escalate_below_threshold(self, init_session):
        init_session.objection_count = 2
        assert not state_machine.should_escalate(init_session)

    def test_should_escalate_on_excessive_tool_calls(self, init_session):
        init_session.tool_call_count = 10
        assert state_machine.should_escalate(init_session)


class TestStageFlow:

    def test_get_ekyc_flow(self):
        assert state_machine.get_stage_flow(OnboardingStage.EKYC_PENDING) == "ekyc_flow"

    def test_get_activation_flow(self):
        assert state_machine.get_stage_flow(OnboardingStage.ACTIVATION_PENDING) == "activation_flow"
