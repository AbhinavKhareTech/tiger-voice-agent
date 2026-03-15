#!/usr/bin/env python3
"""Seed test data into mock backends.

Usage:
  python scripts/seed.py
  # or: make seed
"""

import httpx
import sys


def main():
    base = "http://localhost:8001"
    try:
        resp = httpx.post(f"{base}/api/admin/seed")
        resp.raise_for_status()
        data = resp.json()
        print(f"Seeded {data['customers']} test customers.")

        # List them
        resp = httpx.get(f"{base}/api/admin/customers")
        resp.raise_for_status()
        customers = resp.json()
        print(f"\n{'ID':<8} {'Name':<20} {'Stage':<22} {'Consent'}")
        print("-" * 65)
        for c in customers:
            consent = "Yes" if c["consent_status"] else "NO"
            print(f"{c['customer_id']:<8} {c['name']:<20} {c['onboarding_stage']:<22} {consent}")

    except httpx.ConnectError:
        print("ERROR: Cannot connect to mock backends at localhost:8001")
        print("Run 'make run' first to start the services.")
        sys.exit(1)


if __name__ == "__main__":
    main()
