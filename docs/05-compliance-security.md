# Compliance and Security

## Regulatory Context

Financial product onboarding in India is subject to RBI (Reserve Bank of India), TRAI (Telecom Regulatory Authority of India), and IRDAI regulations. The compliance layer is not a bolt-on; it is a mandatory gateway in the orchestration pipeline.

## Consent Management

Before any outbound call, the system verifies explicit consent for voice communication. Consent records are stored with timestamp, channel, and scope. If consent is missing or expired, the system falls back to SMS-only and flags for manual review.

Test this with customer TC008 (Ravi Kumar), who has `consent_status: false`:

```bash
# This will be blocked by the compliance check
python scripts/trigger_event.py --event card_approved --customer TC008 --sync
```

## TRAI DND and Call Time Restrictions

Every outbound call is checked against the TRAI DND registry. Calls are only placed between 9 AM and 9 PM IST.

See [`compliance_gateway.py`](../orchestrator/src/compliance_gateway.py) and the `/api/compliance/{customer_id}/check` endpoint in mock backends.

## Sensitive Data Masking

The LLM never receives raw PII. The compliance gateway masks fields before context injection:

| Field | Raw | Masked (what LLM sees) |
|-------|-----|----------------------|
| PAN | ABCDE1234F | XXXXX1234A |
| Aadhaar | 1234 5678 9012 | XXXX XXXX 9012 |
| Phone | +919876543210 | XXXXXX3210 |
| Email | priya.sharma@example.com | pr***@example.com |
| Card Number | 4532 1234 5678 9012 | XXXX XXXX XXXX 9012 |

Masking happens at the data access layer. Even if the prompt accidentally requests a raw field, the masked version is returned.

**Output validation** provides a second layer: `compliance_gateway.validate_agent_response()` scans the agent's response for PAN, Aadhaar, and card number patterns before it reaches TTS. Responses containing raw PII are blocked and regenerated.

## Audit Logging

Every voice interaction generates an immutable audit trail: call timestamp, duration, customer ID, agent type (AI/human), redacted transcript, disposition code, actions taken, and data accessed. Logs are stored for the RBI-mandated retention period (minimum 8 years).

See the `/api/compliance/audit` endpoint in mock backends.

## Call Recording

All calls are recorded at the telephony layer. The system plays a mandatory disclosure at the start of each call. If the customer objects to recording, the call transfers to a human agent.

## Data Residency

All customer data, recordings, and transcripts stay within Indian data centers per RBI's data localization directive. The LLM inference endpoint must operate within Indian infrastructure.

## Speaker Verification

Before disclosing account information, the agent verifies identity using last 4 digits of the registered phone number. Verification uses the `verify_identity` tool function, validated through the compliance engine. The LLM collects the response, sends it to the tool, and receives pass/fail. The model never sees the verification data in its reasoning.

Max 3 attempts; lockout after 3 failures with escalation to human.

## Fraud Signal Detection

The system monitors for:

- **Social engineering patterns:** Requests for full card numbers, account changes not related to onboarding, attempts to extract info about other customers
- **Velocity checks:** Multiple calls from different numbers claiming to be the same customer
- **Prompt injection:** Adversarial instructions spoken by the customer to manipulate the LLM

Defenses: strong system prompt boundaries, input sanitization, output validation, and tool router policy enforcement (even a successfully manipulated LLM cannot execute actions outside its permitted tool set).

## Financial Data Tokenization

In production, sensitive identifiers are tokenized via HSM beyond masking. The voice agent, LLM, and logging systems only see tokens. Detokenization happens only at the point of use within the enterprise system. A complete compromise of the voice AI infrastructure would not expose raw financial identifiers.
