"""Tests for the compliance gateway."""

from orchestrator.src.compliance_gateway import ComplianceGateway


class TestPIIMasking:

    def test_masks_phone(self):
        data = {"phone": "+919876543210", "name": "Priya"}
        masked = ComplianceGateway.mask_pii(data)
        assert masked["phone"] == "XXXXXX3210"
        assert masked["name"] == "Priya"  # name not masked

    def test_masks_email(self):
        data = {"email": "priya.sharma@example.com"}
        masked = ComplianceGateway.mask_pii(data)
        assert "priya.sharma" not in masked["email"]
        assert "@example.com" in masked["email"]

    def test_handles_missing_fields(self):
        data = {"name": "Test"}
        masked = ComplianceGateway.mask_pii(data)
        assert masked == {"name": "Test"}

    def test_handles_none_phone(self):
        data = {"phone": None}
        masked = ComplianceGateway.mask_pii(data)
        assert masked["phone"] is None


class TestResponseValidation:

    def test_clean_response_passes(self):
        valid, reason = ComplianceGateway.validate_agent_response(
            "Your card has been approved with a limit of Rs 150000."
        )
        assert valid
        assert reason == "OK"

    def test_masked_pan_passes(self):
        valid, _ = ComplianceGateway.validate_agent_response(
            "Your PAN on file is XXXXX1234A."
        )
        assert valid

    def test_unmasked_pan_blocked(self):
        valid, reason = ComplianceGateway.validate_agent_response(
            "Your PAN number is ABCDE1234F."
        )
        assert not valid
        assert "PAN" in reason

    def test_aadhaar_pattern_blocked(self):
        valid, reason = ComplianceGateway.validate_agent_response(
            "Your Aadhaar is 1234 5678 9012."
        )
        assert not valid
        assert "Aadhaar" in reason

    def test_card_number_blocked(self):
        valid, reason = ComplianceGateway.validate_agent_response(
            "Your card number is 4532 1234 5678 9012."
        )
        assert not valid
        assert "card number" in reason
