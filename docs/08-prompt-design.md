# Prompt Design

## Design Philosophy

The voice agent prompt is not a chatbot instruction. It is a runtime configuration that governs how a probabilistic system (LLM) interacts with deterministic enterprise systems in a regulated financial context. Every line serves one of four purposes: grounding (what the agent knows), flow control (what the agent does), safety (what the agent must not do), or personality (how the agent sounds).

The full production prompt is at [`agent/prompt.md`](../agent/prompt.md).

## Prompt Structure

The prompt is organized into sections that map to distinct runtime behaviors:

| Section | Purpose | Enforcement |
|---------|---------|-------------|
| Identity and Disclosure | RBI-mandated AI disclosure and recording notice | Prompt + compliance monitoring |
| System Variables | Data the agent can reference (injected at runtime) | Orchestration layer injection |
| Available Tools | Functions the agent can call | Tool router validation |
| Tool Usage Rules | When and how often tools can be used | Tool router rate limiting |
| Grounding Rules | What the agent is allowed to state as fact | Output validation |
| Voice and Tone | How the agent speaks | Prompt only |
| Conversation Flow | Stage-specific interaction logic | Prompt + state machine |
| Objection Handling | Predefined responses to common concerns | Prompt + system data |
| Escalation Rules | When to transfer to human | Prompt + state machine |
| Compliance Rules | Non-negotiable safety constraints | Prompt + policy gateway |
| Knowledge Base | Grounded product facts | Prompt only |

## Dual-Layer Enforcement

Every critical policy is enforced at two levels:

| Policy | Prompt-Level | System-Level |
|--------|-------------|-------------|
| No PII disclosure | "NEVER read out full PAN, Aadhaar, or card numbers" | Compliance gateway masks PII before injection; output validator blocks PII patterns |
| No unsupported promises | "NEVER promise increases not backed by data" | Response validator cross-checks claims against variables |
| No pressure selling | "If they say no, respect it" | Decision engine blocks further CTAs after 2 declines |
| Mandatory disclosures | "ALWAYS disclose AI identity and recording" | Compliance monitoring checks first 30 seconds |
| Escalation on frustration | "Transfer when strong frustration detected" | Sentiment analyzer flags negative >0.8 on 2+ turns |

## Structured Tool Calling

The agent interacts with systems through typed tool functions, not free-form API calls.

Tool definitions in [`agent/tools/`](../agent/tools/) specify: function name, description (guides the LLM on when to use it), parameter schema with types and enums, and required fields.

The tool router (`orchestrator/src/tool_handlers/handlers.py`) validates every call against schema, policy, and rate limits before executing against the backend.

## Context Injection

The orchestration layer assembles a `CustomerContext` object from multiple enterprise systems (CPS, CDE, KYC, CIS, CRM) and injects it into the prompt as system variables. Key design decisions:

- **PII is masked at injection time**, not by the prompt. The LLM literally cannot see raw PAN or Aadhaar.
- **Phone number is partially masked** (only last 4 visible) to prevent the agent from reading it aloud.
- **Credit limit is injected as an exact integer**, not a range. The prompt instructs the model to use this exact value, and the output validator cross-checks.
- **Call attempt count adjusts tone**: the prompt uses this to add urgency on later attempts.
- **Campaign source enables objection handling**: the ad miscommunication objection uses this to address specific campaign claims.

## Prompt Evolution Framework

### Weekly Review Process

1. Analytics pipeline processes all calls: objection frequency, new categories, duration, escalation rate, hallucination incidents, NLU confidence
2. AI Solutions team identifies: instructions being ignored, low-resolution objection responses, disengagement patterns, confused tool call patterns
3. Modifications drafted, reviewed by compliance, deployed to shadow environment
4. A/B test for 48-72 hours at 10% traffic. If target metric improves without degrading guardrails, promote to production.

### Version Control

Every prompt version is stored in Git with: full prompt text, analytics report motivating the change, hypothesis being tested, A/B results, and compliance sign-off. This creates an auditable history of why the prompt says what it says.

### Escalation-Driven Improvement

Every human escalation is reviewed to determine:
- **Prompt failure:** Objection was predefined but handling was not effective. Fix: improve the response.
- **Prompt gap:** New objection not in the predefined set. Fix: add a new handler.
- **System design:** This case should always go to a human. Fix: update escalation rules.

This loop ensures prompt coverage expands with each production week.

## Voice-Specific Considerations

Voice prompts differ from text chatbot prompts in several ways:

- **Sentence length matters.** Under 20 words per sentence. Longer sentences sound unnatural when spoken.
- **No visual formatting.** Never use numbered lists, bullet points, or headers in responses. Use transitions: "First... then... after that..."
- **One action per turn.** The customer cannot scroll back. Give one clear next step.
- **Name usage is limited.** Once in greeting, once mid-call. More feels robotic.
- **Jargon avoidance is stricter.** Say "video verification" not "VKYC" unless the customer uses the term first.
- **Pace mirroring.** The prompt instructs the agent to match the customer's energy. Short answers for rushed customers, thorough answers for engaged ones.
