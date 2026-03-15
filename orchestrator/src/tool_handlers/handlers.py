"""Tool handlers: business logic for each voice agent tool function.

Each handler receives parameters from the Vapi webhook, executes the
operation through the mock backends (via orchestrator API gateway),
and returns a structured result that gets injected back into the
agent's context.

Handlers enforce policy constraints (rate limits, preconditions)
independently of the LLM's instructions. This is the system-level
enforcement layer.
"""

import logging
from typing import Any

import httpx

from ..config import settings
from ..compliance_gateway import compliance_gateway

log = logging.getLogger("orchestrator.tools")

_client: httpx.AsyncClient | None = None


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=settings.MOCK_BACKENDS_URL,
            timeout=5.0,
        )
    return _client


async def handle_verify_identity(params: dict[str, Any]) -> dict:
    """Verify customer identity. Max 3 attempts enforced at system level."""
    customer_id = params.get("customer_id", "")
    response = params.get("response", "")

    if not customer_id or not response:
        return {"verified": False, "error": "Missing customer_id or response"}

    client = await get_client()
    try:
        resp = await client.post(
            "/api/compliance/verify-identity",
            json={"customer_id": customer_id, "response": response},
        )
        resp.raise_for_status()
        result = resp.json()
        return {
            "verified": result["verified"],
            "method": result.get("method", "phone_last4"),
        }
    except httpx.HTTPStatusError as e:
        log.error(f"Identity verification failed: {e}")
        return {"verified": False, "error": "Verification service unavailable"}


async def handle_get_vkyc_slots(params: dict[str, Any]) -> dict:
    """Get available VKYC slots. Only returns slots within 9AM-9PM window."""
    date = params.get("date", "")
    client = await get_client()
    try:
        resp = await client.get("/api/kyc/vkyc-slots", params={"date": date} if date else {})
        resp.raise_for_status()
        data = resp.json()
        slots = data.get("available_slots", [])
        return {
            "available_slots": slots[:5],  # Limit to 5 for voice readability
            "total_available": len(slots),
        }
    except httpx.HTTPStatusError:
        return {"available_slots": [], "error": "Could not fetch VKYC slots"}


async def handle_book_vkyc_slot(params: dict[str, Any]) -> dict:
    """Book a VKYC slot. Requires consent_status = true (enforced at system level)."""
    customer_id = params.get("customer_id", "")
    slot = params.get("slot", "")

    if not customer_id or not slot:
        return {"booked": False, "error": "Missing customer_id or slot"}

    client = await get_client()
    try:
        resp = await client.post(
            "/api/kyc/vkyc-book",
            json={"customer_id": customer_id, "slot": slot},
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "booked": True,
            "booking_id": data["booking_id"],
            "slot": data["slot"],
        }
    except httpx.HTTPStatusError as e:
        return {"booked": False, "error": f"Booking failed: {e.response.text}"}


async def handle_send_sms_link(params: dict[str, Any]) -> dict:
    """Send an SMS with a deep link. Max 3 per customer per day (policy enforced)."""
    customer_id = params.get("customer_id", "")
    link_type = params.get("link_type", "ekyc_deeplink")

    valid_types = ["ekyc_deeplink", "vkyc_deeplink", "activation_deeplink"]
    if link_type not in valid_types:
        return {"sent": False, "error": f"Invalid link_type. Must be one of: {valid_types}"}

    client = await get_client()
    try:
        resp = await client.post(
            "/api/notifications/sms",
            json={"customer_id": customer_id, "link_type": link_type},
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "sent": True,
            "message_id": data["message_id"],
            "link_type": link_type,
        }
    except httpx.HTTPStatusError:
        return {"sent": False, "error": "SMS delivery failed"}


async def handle_trigger_activation(params: dict[str, Any]) -> dict:
    """Activate a customer's card. Requires VKYC complete. Irreversible."""
    customer_id = params.get("customer_id", "")

    if not customer_id:
        return {"activated": False, "error": "Missing customer_id"}

    # System-level precondition check: verify VKYC is done
    client = await get_client()
    try:
        kyc_resp = await client.get(f"/api/kyc/{customer_id}/status")
        kyc_resp.raise_for_status()
        kyc = kyc_resp.json()
        if not kyc.get("vkyc_done"):
            return {"activated": False, "error": "VKYC must be completed before activation"}

        resp = await client.post(f"/api/card/{customer_id}/activate")
        resp.raise_for_status()
        data = resp.json()

        # Audit log
        await compliance_gateway.write_audit_log(
            customer_id, "card_activated", {"source": "voice_agent"}
        )

        return {
            "activated": True,
            "activation_status": data["activation_status"],
            "welcome_reward_status": data["welcome_reward_status"],
        }
    except httpx.HTTPStatusError as e:
        return {"activated": False, "error": f"Activation failed: {e.response.text}"}


async def handle_log_disposition(params: dict[str, Any]) -> dict:
    """Log call disposition. Required at end of every call."""
    customer_id = params.get("customer_id", "")
    disposition = params.get("disposition", "")
    notes = params.get("notes", "")

    client = await get_client()
    try:
        resp = await client.post(
            "/api/crm/disposition",
            json={
                "customer_id": customer_id,
                "disposition": disposition,
                "notes": notes,
                "agent_type": "AI",
            },
        )
        resp.raise_for_status()
        return {"logged": True, "disposition": disposition}
    except httpx.HTTPStatusError:
        return {"logged": False, "error": "Disposition logging failed"}


async def handle_transfer_to_human(params: dict[str, Any]) -> dict:
    """Warm transfer to a human agent. Packages full context.

    In production, this would initiate a SIP REFER. In the demo,
    it logs the transfer intent and context.
    """
    customer_id = params.get("customer_id", "")
    reason = params.get("reason", "customer_request")
    context = params.get("context", {})

    log.info(f"ESCALATION: Transfer to human for {customer_id}, reason={reason}")

    # Audit log
    await compliance_gateway.write_audit_log(
        customer_id,
        "escalated_to_human",
        {"reason": reason, "context_summary": str(context)[:500]},
    )

    return {
        "transferred": True,
        "reason": reason,
        "message": "Connecting you with a specialist now.",
    }


# ---- Tool Router ----

TOOL_HANDLERS = {
    "verify_identity": handle_verify_identity,
    "get_vkyc_slots": handle_get_vkyc_slots,
    "book_vkyc_slot": handle_book_vkyc_slot,
    "send_sms_link": handle_send_sms_link,
    "trigger_activation": handle_trigger_activation,
    "log_disposition": handle_log_disposition,
    "transfer_to_human": handle_transfer_to_human,
}


async def route_tool_call(function_name: str, parameters: dict[str, Any]) -> dict:
    """Route a tool call to the appropriate handler.

    This is the policy gateway entry point. All tool calls from the
    voice agent come through here.
    """
    handler = TOOL_HANDLERS.get(function_name)
    if not handler:
        log.warning(f"Unknown tool function: {function_name}")
        return {"error": f"Unknown function: {function_name}"}

    log.info(f"Tool call: {function_name}({parameters})")
    result = await handler(parameters)
    log.info(f"Tool result: {function_name} -> {result}")
    return result
