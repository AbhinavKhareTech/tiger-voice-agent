"""Compliance gateway: the trust boundary between AI and enterprise systems.

Every data access and outbound action passes through this gateway.
It enforces: PII masking, consent verification, DND checks, call time
window restrictions, and rate limiting. The LLM never sees raw PII.
"""

import logging
import re

import httpx

from .config import settings
from .models import ComplianceResult

log = logging.getLogger("orchestrator.compliance")


class ComplianceGateway:
    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def connect(self):
        self._client = httpx.AsyncClient(
            base_url=settings.MOCK_BACKENDS_URL,
            timeout=5.0,
        )

    async def close(self):
        if self._client:
            await self._client.aclose()

    async def pre_call_check(self, customer_id: str) -> ComplianceResult:
        """Run all compliance checks before initiating a call.

        Checks: consent, DND registry, call time window (9AM-9PM IST), cooldown.
        Returns a ComplianceResult indicating whether the call can proceed.
        """
        try:
            resp = await self._client.get(f"/api/compliance/{customer_id}/check")
            resp.raise_for_status()
            data = resp.json()

            if data["cleared"]:
                return ComplianceResult(cleared=True, checks=data["checks"])

            # Build human-readable reason
            failed = [k for k, v in data["checks"].items() if not v]
            reason = f"Blocked: {', '.join(failed)}"
            log.warning(f"Compliance check failed for {customer_id}: {reason}")
            return ComplianceResult(cleared=False, checks=data["checks"], reason=reason)

        except httpx.HTTPStatusError as e:
            log.error(f"Compliance API error for {customer_id}: {e}")
            return ComplianceResult(
                cleared=False,
                checks={},
                reason=f"Compliance check failed: {e.response.status_code}",
            )
        except Exception as e:
            log.error(f"Compliance check exception for {customer_id}: {e}")
            return ComplianceResult(
                cleared=False,
                checks={},
                reason=f"Compliance check unavailable: {str(e)}",
            )

    @staticmethod
    def mask_pii(data: dict) -> dict:
        """Mask sensitive fields before exposing data to the LLM.

        PAN: XXXXX1234A (already masked in mock)
        Aadhaar: XXXX XXXX 5678 (already masked in mock)
        Phone: show only last 4 digits
        Card number: XXXX XXXX XXXX 5678 (already masked in mock)

        In production, this would tokenize via HSM rather than mask.
        """
        masked = dict(data)

        # Mask phone to last 4 only for LLM context
        if "phone" in masked and masked["phone"]:
            masked["phone"] = f"XXXXXX{masked['phone'][-4:]}"

        # Mask email
        if "email" in masked and masked["email"]:
            parts = masked["email"].split("@")
            if len(parts) == 2:
                masked["email"] = f"{parts[0][:2]}***@{parts[1]}"

        return masked

    @staticmethod
    def validate_agent_response(response_text: str) -> tuple[bool, str]:
        """Validate that the agent's response does not contain raw PII.

        Returns (is_valid, reason). If invalid, the response should be
        regenerated or blocked.
        """
        # Check for PAN patterns (10 char alphanumeric)
        pan_pattern = r"\b[A-Z]{5}\d{4}[A-Z]\b"
        if re.search(pan_pattern, response_text):
            # Allow masked format XXXXX1234X
            unmasked = re.findall(pan_pattern, response_text)
            for match in unmasked:
                if not match.startswith("XXXXX"):
                    return False, "Response contains unmasked PAN number"

        # Check for Aadhaar patterns (12 digits)
        aadhaar_pattern = r"\b\d{4}\s?\d{4}\s?\d{4}\b"
        if re.search(aadhaar_pattern, response_text):
            return False, "Response contains potential Aadhaar number"

        # Check for full card numbers (16 digits)
        card_pattern = r"\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b"
        if re.search(card_pattern, response_text):
            return False, "Response contains potential card number"

        return True, "OK"

    async def write_audit_log(self, customer_id: str, event_type: str, details: dict) -> None:
        """Write an immutable audit log entry."""
        try:
            await self._client.post(
                "/api/compliance/audit",
                json={
                    "customer_id": customer_id,
                    "event_type": event_type,
                    "details": details,
                },
            )
        except Exception as e:
            log.error(f"Audit log write failed for {customer_id}: {e}")


compliance_gateway = ComplianceGateway()
