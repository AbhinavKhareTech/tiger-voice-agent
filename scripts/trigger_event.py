#!/usr/bin/env python3
"""Trigger a stage-change event for a test customer.

Usage:
  python scripts/trigger_event.py --event card_approved --customer TC001
  python scripts/trigger_event.py --event ekyc_completed --customer TC003
  python scripts/trigger_event.py --event vkyc_completed --customer TC005
  python scripts/trigger_event.py --event card_activated --customer TC007

  # or: make trigger (defaults to card_approved for TC001)
"""

import argparse
import httpx
import sys


VALID_EVENTS = [
    "card_approved",
    "ekyc_completed",
    "vkyc_completed",
    "card_activated",
]


def main():
    parser = argparse.ArgumentParser(description="Trigger a stage-change event")
    parser.add_argument("--event", default="card_approved", choices=VALID_EVENTS)
    parser.add_argument("--customer", default="TC001")
    parser.add_argument("--sync", action="store_true", help="Process synchronously (bypass pub/sub)")
    args = parser.parse_args()

    base = "http://localhost:8000"
    endpoint = "/api/events/process" if args.sync else "/api/events/publish"

    try:
        resp = httpx.post(
            f"{base}{endpoint}",
            params={
                "event_type": args.event,
                "customer_id": args.customer,
                "source_system": "manual_trigger",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        print(f"Event: {args.event}")
        print(f"Customer: {args.customer}")
        print(f"Result: {data}")

    except httpx.ConnectError:
        print("ERROR: Cannot connect to orchestrator at localhost:8000")
        print("Run 'make run' first to start the services.")
        sys.exit(1)


if __name__ == "__main__":
    main()
