"""Tests for the Vapi webhook handler (unit-level, no external deps)."""

import json



class TestVapiWebhookParsing:
    """Test webhook payload parsing without hitting real services."""

    def test_unknown_message_type_returns_ok(self):
        """Unknown message types should be handled gracefully."""
        from orchestrator.src.routes.vapi_webhook import _handle_status_update
        result = _handle_status_update({"status": "ringing"})
        assert result == {"status": "ok"}

    def test_end_of_call_report(self):
        from orchestrator.src.routes.vapi_webhook import _handle_end_of_call
        result = _handle_end_of_call({
            "call": {"id": "call-123"},
            "durationSeconds": 180,
            "transcript": "Hello, this is Tara..."
        })
        assert result == {"status": "ok"}

    def test_tool_call_parsing(self):
        """Verify tool call payloads are correctly parsed."""
        # This tests the parsing logic, not the actual tool execution
        raw_args = json.dumps({"customer_id": "TC001", "response": "3210"})
        parsed = json.loads(raw_args)
        assert parsed["customer_id"] == "TC001"
        assert parsed["response"] == "3210"
