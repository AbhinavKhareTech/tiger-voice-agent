"""Vapi.ai webhook handler.

Vapi calls this endpoint when the voice agent invokes a tool function.
The webhook receives the tool call request, routes it to the appropriate
handler, and returns the result to Vapi for injection into the conversation.

Vapi webhook format:
  POST /api/vapi/webhook
  Body: { "message": { "type": "tool-calls", "toolCallList": [...] } }

Response format:
  { "results": [{ "toolCallId": "...", "result": "..." }] }
"""

import json
import logging

from fastapi import APIRouter, Request

from ..tool_handlers.handlers import route_tool_call

log = logging.getLogger("orchestrator.routes.vapi")

router = APIRouter(prefix="/api/vapi", tags=["Vapi Webhook"])


@router.post("/webhook")
async def vapi_webhook(request: Request):
    """Handle Vapi tool-call webhooks.

    Vapi sends tool calls when the voice agent decides to use a function.
    We route each call to the appropriate handler and return results.
    """
    body = await request.json()
    message = body.get("message", {})
    message_type = message.get("type", "")

    log.info(f"Vapi webhook received: type={message_type}")

    # Handle different Vapi message types
    if message_type == "tool-calls":
        return await _handle_tool_calls(message)
    elif message_type == "status-update":
        return _handle_status_update(message)
    elif message_type == "end-of-call-report":
        return _handle_end_of_call(message)
    elif message_type == "assistant-request":
        return _handle_assistant_request(message)
    else:
        log.debug(f"Unhandled Vapi message type: {message_type}")
        return {"status": "ok"}


async def _handle_tool_calls(message: dict) -> dict:
    """Process tool calls from the voice agent."""
    tool_calls = message.get("toolCallList", [])
    results = []

    for tc in tool_calls:
        tool_call_id = tc.get("id", "")
        function = tc.get("function", {})
        function_name = function.get("name", "")

        # Parse parameters (Vapi sends them as a JSON string in "arguments")
        raw_args = function.get("arguments", "{}")
        if isinstance(raw_args, str):
            try:
                parameters = json.loads(raw_args)
            except json.JSONDecodeError:
                parameters = {}
        else:
            parameters = raw_args

        # Route to handler
        result = await route_tool_call(function_name, parameters)

        results.append({
            "toolCallId": tool_call_id,
            "result": json.dumps(result),
        })

    return {"results": results}


def _handle_status_update(message: dict) -> dict:
    """Handle call status updates (ringing, answered, ended)."""
    status = message.get("status", "")
    log.info(f"Call status update: {status}")
    return {"status": "ok"}


def _handle_end_of_call(message: dict) -> dict:
    """Handle end-of-call report with transcript and analytics."""
    call_id = message.get("call", {}).get("id", "unknown")
    duration = message.get("durationSeconds", 0)
    transcript = message.get("transcript", "")
    log.info(f"Call ended: id={call_id}, duration={duration}s, transcript_length={len(transcript)}")
    # In production: store transcript, run analytics, compute metrics
    return {"status": "ok"}


def _handle_assistant_request(message: dict) -> dict:
    """Handle assistant configuration requests.

    Vapi calls this to get dynamic assistant configuration.
    We can inject customer-specific variables here.
    """
    log.info("Assistant request received (dynamic config)")
    # Return empty to use the default assistant config
    return {}
