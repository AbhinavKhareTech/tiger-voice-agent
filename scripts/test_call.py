#!/usr/bin/env python3
"""Initiate a test voice call via Vapi.ai.

Requires VAPI_API_KEY, VAPI_ASSISTANT_ID, and VAPI_PHONE_NUMBER_ID
to be set in the .env file.

Usage:
  python scripts/test_call.py --customer TC001 --phone +919876543210
  # or: make call
"""

import argparse
import os
import sys

import httpx


def main():
    parser = argparse.ArgumentParser(description="Initiate a test call via Vapi")
    parser.add_argument("--customer", default="TC001", help="Customer ID")
    parser.add_argument("--phone", default=None, help="Phone number to call (overrides customer phone)")
    args = parser.parse_args()

    api_key = os.getenv("VAPI_API_KEY", "")
    assistant_id = os.getenv("VAPI_ASSISTANT_ID", "")
    phone_number_id = os.getenv("VAPI_PHONE_NUMBER_ID", "")

    if not api_key:
        print("ERROR: VAPI_API_KEY not set.")
        print("Set it in your .env file or export it:")
        print("  export VAPI_API_KEY=your-key-here")
        sys.exit(1)

    if not assistant_id:
        print("ERROR: VAPI_ASSISTANT_ID not set.")
        sys.exit(1)

    # Get customer phone from mock backends if not overridden
    phone = args.phone
    if not phone:
        try:
            resp = httpx.get(f"http://localhost:8001/api/customers/{args.customer}")
            resp.raise_for_status()
            customer = resp.json()
            phone = customer["phone"]
            print(f"Customer: {customer['name']} ({args.customer})")
            print(f"Stage: {customer['onboarding_stage']}")
            print(f"Phone: {phone}")
        except Exception as e:
            print(f"ERROR: Could not fetch customer: {e}")
            sys.exit(1)

    # Create Vapi outbound call
    print(f"\nInitiating call to {phone}...")
    try:
        resp = httpx.post(
            "https://api.vapi.ai/call/phone",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "assistantId": assistant_id,
                "phoneNumberId": phone_number_id,
                "customer": {
                    "number": phone,
                },
                "assistantOverrides": {
                    "variableValues": {
                        "customer_id": args.customer,
                    },
                },
            },
        )
        resp.raise_for_status()
        call = resp.json()
        print(f"Call initiated: {call.get('id', 'unknown')}")
        print(f"Status: {call.get('status', 'unknown')}")
        print(f"\nCheck orchestrator logs: make logs-orchestrator")

    except httpx.HTTPStatusError as e:
        print(f"Vapi API error: {e.response.status_code}")
        print(e.response.text)
        sys.exit(1)
    except httpx.ConnectError:
        print("ERROR: Could not connect to Vapi API")
        sys.exit(1)


if __name__ == "__main__":
    main()
