"""
Tiger Credit Card - Mock Enterprise Systems

Simulates all backend systems that the voice agent integrates with.
Each router represents one enterprise system with realistic API contracts.
These API contracts ARE the integration specification.

Systems:
  - Customer Profile System (CPS)
  - Credit Decision Engine (CDE)
  - KYC Provider
  - Card Issuer System (CIS)
  - CRM / Sales System
  - Notification System
  - Compliance Engine

Configure failure injection via environment variables:
  FAILURE_RATE: probability of 500 error (0.0 - 1.0)
  LATENCY_MS: artificial latency per request (ms)
"""

import asyncio
import json
import logging
import os
import random
import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ---- Config ----

FAILURE_RATE = float(os.getenv("FAILURE_RATE", "0.0"))
LATENCY_MS = int(os.getenv("LATENCY_MS", "0"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
log = logging.getLogger("mock-backends")

# ---- In-Memory Store ----

CUSTOMERS: dict[str, dict[str, Any]] = {}
AUDIT_LOG: list[dict[str, Any]] = []
VKYC_SLOTS: list[str] = []


def load_seed_data():
    """Load test customers from seed_data/customers.json."""
    seed_path = Path("/app/seed_data/customers.json")
    if not seed_path.exists():
        seed_path = Path(__file__).parent.parent / "seed_data" / "customers.json"
    if seed_path.exists():
        with open(seed_path) as f:
            customers = json.load(f)
        for c in customers:
            CUSTOMERS[c["customer_id"]] = c
        log.info(f"Loaded {len(CUSTOMERS)} test customers from seed data")
    else:
        log.warning("No seed data found. Start with empty store.")

    # Generate VKYC slots for the next 7 days
    now = datetime.now(timezone.utc)
    for day_offset in range(7):
        day = now + timedelta(days=day_offset)
        for hour in [9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20]:
            slot = day.replace(hour=hour, minute=0, second=0, microsecond=0)
            if slot > now:
                VKYC_SLOTS.append(slot.isoformat())


# ---- Failure Injection ----

async def maybe_fail_and_delay():
    """Inject configurable failures and latency for resilience testing."""
    if LATENCY_MS > 0:
        jitter = random.randint(0, max(1, LATENCY_MS // 2))
        await asyncio.sleep((LATENCY_MS + jitter) / 1000.0)
    if FAILURE_RATE > 0 and random.random() < FAILURE_RATE:
        raise HTTPException(status_code=503, detail="Simulated backend failure")


# ---- App ----

app = FastAPI(
    title="Tiger Credit Card - Mock Enterprise Systems",
    version="0.1.0",
    description="Simulated backend APIs for voice agent development and testing",
)


@app.on_event("startup")
async def startup():
    load_seed_data()


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "mock-backends",
        "customers_loaded": len(CUSTOMERS),
        "failure_rate": FAILURE_RATE,
        "latency_ms": LATENCY_MS,
    }


# ═══════════════════════════════════════════════════════════
# CUSTOMER PROFILE SYSTEM (CPS)
# ═══════════════════════════════════════════════════════════

@app.get("/api/customers/{customer_id}", tags=["Customer Profile"])
async def get_customer(customer_id: str):
    """Read customer profile. Returns masked PII only."""
    await maybe_fail_and_delay()
    if customer_id not in CUSTOMERS:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return CUSTOMERS[customer_id]


@app.patch("/api/customers/{customer_id}/stage", tags=["Customer Profile"])
async def update_stage(customer_id: str, stage: str):
    """Update customer onboarding stage."""
    await maybe_fail_and_delay()
    if customer_id not in CUSTOMERS:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    valid_stages = ["EKYC_PENDING", "VKYC_PENDING", "ACTIVATION_PENDING", "CARD_ACTIVE", "COMPLETED"]
    if stage not in valid_stages:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of: {valid_stages}")
    CUSTOMERS[customer_id]["onboarding_stage"] = stage
    log.info(f"Customer {customer_id} stage updated to {stage}")
    return {"customer_id": customer_id, "onboarding_stage": stage}


# ═══════════════════════════════════════════════════════════
# CREDIT DECISION ENGINE (CDE)
# ═══════════════════════════════════════════════════════════

@app.get("/api/credit/{customer_id}", tags=["Credit Decision"])
async def get_credit_decision(customer_id: str):
    """Read credit decision for a customer."""
    await maybe_fail_and_delay()
    if customer_id not in CUSTOMERS:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    c = CUSTOMERS[customer_id]
    return {
        "customer_id": customer_id,
        "credit_limit": c["credit_limit"],
        "risk_tier": c["risk_tier"],
        "limit_revision_eligible": c["limit_revision_eligible"],
        "application_id": c["application_id"],
    }


# ═══════════════════════════════════════════════════════════
# KYC PROVIDER
# ═══════════════════════════════════════════════════════════

@app.get("/api/kyc/{customer_id}/status", tags=["KYC Provider"])
async def get_kyc_status(customer_id: str):
    """Read eKYC and VKYC status."""
    await maybe_fail_and_delay()
    if customer_id not in CUSTOMERS:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    c = CUSTOMERS[customer_id]
    return {
        "customer_id": customer_id,
        "ekyc_done": c["kyc_status"]["ekyc_done"],
        "vkyc_done": c["kyc_status"]["vkyc_done"],
        "vkyc_attempts": c["kyc_status"]["vkyc_attempts"],
        "failure_reason": c["kyc_status"]["failure_reason"],
        "ekyc_link": f"https://tiger.app/ekyc/{customer_id}" if not c["kyc_status"]["ekyc_done"] else None,
    }


@app.get("/api/kyc/vkyc-slots", tags=["KYC Provider"])
async def get_vkyc_slots(date: str | None = None):
    """Get available VKYC video verification slots. VKYC operates 9 AM - 9 PM IST."""
    await maybe_fail_and_delay()
    slots = VKYC_SLOTS
    if date:
        slots = [s for s in slots if s.startswith(date)]
    return {"available_slots": slots[:10]}


class VKYCBooking(BaseModel):
    customer_id: str
    slot: str


@app.post("/api/kyc/vkyc-book", tags=["KYC Provider"])
async def book_vkyc_slot(booking: VKYCBooking):
    """Book a VKYC slot for a customer."""
    await maybe_fail_and_delay()
    if booking.customer_id not in CUSTOMERS:
        raise HTTPException(status_code=404, detail="Customer not found")
    if booking.slot not in VKYC_SLOTS:
        raise HTTPException(status_code=400, detail="Slot not available")
    # Remove slot from availability
    VKYC_SLOTS.remove(booking.slot)
    log.info(f"VKYC slot booked for {booking.customer_id}: {booking.slot}")
    return {
        "booking_id": f"VKYC-{uuid.uuid4().hex[:8].upper()}",
        "customer_id": booking.customer_id,
        "slot": booking.slot,
        "status": "CONFIRMED",
    }


@app.post("/api/kyc/{customer_id}/complete-ekyc", tags=["KYC Provider"])
async def complete_ekyc(customer_id: str):
    """Simulate eKYC completion (for testing)."""
    await maybe_fail_and_delay()
    if customer_id not in CUSTOMERS:
        raise HTTPException(status_code=404, detail="Customer not found")
    CUSTOMERS[customer_id]["kyc_status"]["ekyc_done"] = True
    CUSTOMERS[customer_id]["onboarding_stage"] = "VKYC_PENDING"
    log.info(f"eKYC completed for {customer_id}")
    return {"customer_id": customer_id, "ekyc_done": True}


@app.post("/api/kyc/{customer_id}/complete-vkyc", tags=["KYC Provider"])
async def complete_vkyc(customer_id: str):
    """Simulate VKYC completion (for testing)."""
    await maybe_fail_and_delay()
    if customer_id not in CUSTOMERS:
        raise HTTPException(status_code=404, detail="Customer not found")
    CUSTOMERS[customer_id]["kyc_status"]["vkyc_done"] = True
    CUSTOMERS[customer_id]["onboarding_stage"] = "ACTIVATION_PENDING"
    log.info(f"VKYC completed for {customer_id}")
    return {"customer_id": customer_id, "vkyc_done": True}


# ═══════════════════════════════════════════════════════════
# CARD ISSUER SYSTEM (CIS)
# ═══════════════════════════════════════════════════════════

@app.get("/api/card/{customer_id}", tags=["Card Issuer"])
async def get_card_status(customer_id: str):
    """Read card issuance and activation status."""
    await maybe_fail_and_delay()
    if customer_id not in CUSTOMERS:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {
        "customer_id": customer_id,
        **CUSTOMERS[customer_id]["card_details"],
        "welcome_reward_status": CUSTOMERS[customer_id]["welcome_reward_status"],
    }


@app.post("/api/card/{customer_id}/activate", tags=["Card Issuer"])
async def activate_card(customer_id: str):
    """Activate a customer's credit card. Requires VKYC completion."""
    await maybe_fail_and_delay()
    if customer_id not in CUSTOMERS:
        raise HTTPException(status_code=404, detail="Customer not found")
    c = CUSTOMERS[customer_id]
    if not c["kyc_status"]["vkyc_done"]:
        raise HTTPException(status_code=400, detail="VKYC must be completed before activation")
    c["card_details"]["activation_status"] = "ACTIVE"
    c["onboarding_stage"] = "CARD_ACTIVE"
    c["welcome_reward_status"] = "credited"
    log.info(f"Card activated for {customer_id}")
    return {
        "customer_id": customer_id,
        "activation_status": "ACTIVE",
        "welcome_reward_status": "credited",
        "virtual_card_ready": True,
    }


# ═══════════════════════════════════════════════════════════
# CRM / SALES SYSTEM
# ═══════════════════════════════════════════════════════════

@app.get("/api/crm/{customer_id}/history", tags=["CRM"])
async def get_call_history(customer_id: str):
    """Read call interaction history."""
    await maybe_fail_and_delay()
    if customer_id not in CUSTOMERS:
        raise HTTPException(status_code=404, detail="Customer not found")
    c = CUSTOMERS[customer_id]
    return {
        "customer_id": customer_id,
        "call_count": len(c["call_history"]),
        "last_call": c["call_history"][-1] if c["call_history"] else None,
        "history": c["call_history"],
        "campaign_source": c["campaign_source"],
    }


class Disposition(BaseModel):
    customer_id: str
    disposition: str
    notes: str = ""
    agent_type: str = "AI"


@app.post("/api/crm/disposition", tags=["CRM"])
async def log_disposition(disposition: Disposition):
    """Log call disposition and outcome."""
    await maybe_fail_and_delay()
    if disposition.customer_id not in CUSTOMERS:
        raise HTTPException(status_code=404, detail="Customer not found")
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "outcome": disposition.disposition,
        "agent": disposition.agent_type,
        "notes": disposition.notes,
    }
    CUSTOMERS[disposition.customer_id]["call_history"].append(entry)
    log.info(f"Disposition logged for {disposition.customer_id}: {disposition.disposition}")
    return {"status": "logged", **entry}


# ═══════════════════════════════════════════════════════════
# NOTIFICATION SYSTEM
# ═══════════════════════════════════════════════════════════

class SMSRequest(BaseModel):
    customer_id: str
    link_type: str  # "ekyc_deeplink", "vkyc_deeplink", "activation_deeplink"
    message: str = ""


@app.post("/api/notifications/sms", tags=["Notifications"])
async def send_sms(req: SMSRequest):
    """Send an SMS with a deep link. In production, this calls an SMS gateway."""
    await maybe_fail_and_delay()
    if req.customer_id not in CUSTOMERS:
        raise HTTPException(status_code=404, detail="Customer not found")
    c = CUSTOMERS[req.customer_id]
    link = f"https://tiger.app/{req.link_type}/{req.customer_id}"
    log.info(f"SMS sent to {c['phone']}: {req.link_type} -> {link}")
    return {
        "status": "delivered",
        "phone": c["phone"],
        "link": link,
        "link_type": req.link_type,
        "message_id": f"SMS-{uuid.uuid4().hex[:8].upper()}",
    }


# ═══════════════════════════════════════════════════════════
# COMPLIANCE ENGINE
# ═══════════════════════════════════════════════════════════

@app.get("/api/compliance/{customer_id}/check", tags=["Compliance"])
async def compliance_check(customer_id: str):
    """Pre-call compliance check: consent, DND, call time window."""
    await maybe_fail_and_delay()
    if customer_id not in CUSTOMERS:
        raise HTTPException(status_code=404, detail="Customer not found")
    c = CUSTOMERS[customer_id]

    # Check consent
    consent_ok = c.get("consent_status", False)

    # Check call time window (9 AM - 9 PM IST = UTC+5:30)
    ist_offset = timedelta(hours=5, minutes=30)
    now_ist = datetime.now(timezone.utc) + ist_offset
    time_ok = 9 <= now_ist.hour < 21

    # Simulated DND check (all test customers pass)
    dnd_ok = True

    # Cooldown check: no call within last 24 hours
    cooldown_ok = True
    if c["call_history"]:
        last_call_ts = c["call_history"][-1]["timestamp"]
        last_call = datetime.fromisoformat(last_call_ts)
        if last_call.tzinfo is None:
            last_call = last_call.replace(tzinfo=timezone.utc)
        hours_since = (datetime.now(timezone.utc) - last_call).total_seconds() / 3600
        cooldown_ok = hours_since >= 24

    cleared = consent_ok and time_ok and dnd_ok and cooldown_ok

    return {
        "customer_id": customer_id,
        "cleared": cleared,
        "checks": {
            "consent": consent_ok,
            "call_time_window": time_ok,
            "dnd_registry": dnd_ok,
            "cooldown_24h": cooldown_ok,
        },
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


class IdentityVerification(BaseModel):
    customer_id: str
    response: str  # Last 4 digits of phone or PAN


@app.post("/api/compliance/verify-identity", tags=["Compliance"])
async def verify_identity(req: IdentityVerification):
    """Verify customer identity using last 4 digits of registered phone."""
    await maybe_fail_and_delay()
    if req.customer_id not in CUSTOMERS:
        raise HTTPException(status_code=404, detail="Customer not found")
    c = CUSTOMERS[req.customer_id]
    phone_last4 = c["phone"][-4:]
    passed = req.response == phone_last4
    log.info(f"Identity verification for {req.customer_id}: {'PASS' if passed else 'FAIL'}")
    return {
        "customer_id": req.customer_id,
        "verified": passed,
        "method": "phone_last4",
    }


class AuditEntry(BaseModel):
    customer_id: str
    event_type: str
    details: dict[str, Any] = {}


@app.post("/api/compliance/audit", tags=["Compliance"])
async def write_audit_log(entry: AuditEntry):
    """Write an immutable audit log entry."""
    await maybe_fail_and_delay()
    record = {
        "audit_id": f"AUD-{uuid.uuid4().hex[:8].upper()}",
        "customer_id": entry.customer_id,
        "event_type": entry.event_type,
        "details": entry.details,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    AUDIT_LOG.append(record)
    log.info(f"Audit log: {entry.event_type} for {entry.customer_id}")
    return record


@app.get("/api/compliance/audit/{customer_id}", tags=["Compliance"])
async def get_audit_log(customer_id: str):
    """Read audit log for a customer."""
    await maybe_fail_and_delay()
    entries = [e for e in AUDIT_LOG if e["customer_id"] == customer_id]
    return {"customer_id": customer_id, "entries": entries}


# ═══════════════════════════════════════════════════════════
# BULK / ADMIN ENDPOINTS (for seeding and testing)
# ═══════════════════════════════════════════════════════════

@app.post("/api/admin/seed", tags=["Admin"])
async def seed_data():
    """Reload seed data from disk. Used by scripts/seed.sh."""
    load_seed_data()
    return {"status": "seeded", "customers": len(CUSTOMERS)}


@app.get("/api/admin/customers", tags=["Admin"])
async def list_customers():
    """List all customers with their current stage."""
    return [
        {
            "customer_id": c["customer_id"],
            "name": c["name"],
            "onboarding_stage": c["onboarding_stage"],
            "consent_status": c["consent_status"],
        }
        for c in CUSTOMERS.values()
    ]


@app.post("/api/admin/reset", tags=["Admin"])
async def reset_data():
    """Reset all data to seed state."""
    CUSTOMERS.clear()
    AUDIT_LOG.clear()
    VKYC_SLOTS.clear()
    load_seed_data()
    return {"status": "reset", "customers": len(CUSTOMERS)}
