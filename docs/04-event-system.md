# Event System

## Event-Driven Model

Stage transitions in Tiger's backend publish events. The Orchestration Layer consumes these events, enriches them with customer context, and triggers voice interactions. This decouples event producers (KYC Provider, Card Issuer) from the action system (Voice AI).

### Global Event Pipeline

Every onboarding stage follows this pattern:

1. Backend publishes a `stage_change` event (e.g., `card_approved`, `ekyc_completed`)
2. Orchestrator consumes the event, reads customer profile from CPS and CRM
3. Compliance Engine performs pre-call checks: consent, DND, call time window, cooldown
4. If checks pass, the orchestrator schedules the voice interaction
5. Voice agent initiates conversation using stage-specific prompt and injected variables
6. During conversation, agent reads additional data via tool calls (e.g., VKYC slot availability)
7. Post-call, orchestrator writes outcomes to CRM and CPS
8. If customer did not complete the action, a retry event is scheduled with backoff

### Stage Flows

**Stage 1: Card Approved to eKYC Pending**
- Trigger: `card_approved` from Credit Decision Engine
- Data Read: customer name, phone, language (CPS); call history, campaign (CRM); eKYC deep link (KYC)
- Agent Action: congratulate, communicate limit, guide to eKYC
- Data Write: disposition to CRM, audit log to Compliance

**Stage 2: eKYC Done to VKYC Pending**
- Trigger: `ekyc_completed` from KYC Provider
- Data Read: VKYC slot availability (KYC); timezone (CPS); current time (system)
- Agent Action: acknowledge eKYC, explain VKYC, offer/book slots
- Data Write: VKYC booking (KYC); disposition to CRM

**Stage 3: VKYC Done to Activation Pending**
- Trigger: `vkyc_completed` from KYC Provider
- Data Read: card status, virtual card readiness (CIS); reward eligibility (CDE)
- Agent Action: congratulate, walk through one-tap activation
- Data Write: activation trigger (CIS); disposition to CRM

**Stage 4: Card Active (Orientation)**
- Trigger: `card_activated` from Card Issuer
- Agent Action: congratulate, orient on card features and Jewels system
- Data Write: journey complete (CPS); final disposition (CRM)

## Event Schema Registry

All events follow a versioned schema. Producers cannot publish non-conforming events.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_id` | UUID | Yes | Globally unique (idempotency key) |
| `event_type` | string | Yes | e.g., `card_approved`, `ekyc_completed` |
| `event_version` | string | Yes | Schema version (e.g., `v2.1`) |
| `timestamp` | ISO-8601 | Yes | UTC production timestamp |
| `customer_id` | string | Yes | Tiger internal customer ID |
| `application_id` | string | Yes | Card application reference |
| `source_system` | string | Yes | System that produced the event |
| `correlation_id` | UUID | Yes | End-to-end trace ID |
| `metadata` | object | No | Event-specific payload |

Schema evolution follows Avro compatibility: new optional fields can be added, existing required fields cannot be removed.

## Idempotency and Deduplication

Every event carries a unique `event_id`. The orchestrator maintains a deduplication cache (Redis, 7-day TTL). Before processing, the consumer checks this cache. If seen before, the event is acknowledged and discarded.

This prevents duplicate calls caused by at-least-once delivery during consumer rebalancing.

See [`orchestrator/src/dedup.py`](../orchestrator/src/dedup.py).

## Dead Letter Queues

Events failing after 3 retries route to a DLQ (separate topic/channel). The operations team monitors DLQ depth. Failed events can be inspected, fixed, and replayed. Typical failures: `customer_id` not found (data sync delay), consent expired, downstream API timeout.

## Race Condition Prevention

A customer may complete eKYC while the orchestrator is preparing to call about eKYC. Without safeguards, the customer receives a call about a step they already completed.

The system prevents this with a **pre-call state refresh**: immediately before initiating a call, the orchestrator re-reads `onboarding_stage` from CPS. If the stage has advanced, the call is skipped or redirected.

See `event_consumer.py`, Step 3 in `process_event()`.

## Redis vs Kafka

This implementation uses Redis pub/sub for the event channel. The event consumer interface is identical to what a Kafka consumer would look like. Swapping to Kafka in production requires changing the transport layer, not the processing logic. Redis was chosen to keep Docker compose simple and avoid requiring a Kafka cluster for the demo.
