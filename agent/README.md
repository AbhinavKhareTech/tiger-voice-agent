# Voice Agent Configuration

This directory contains everything needed to deploy the Tiger Credit Card voice agent on Vapi.ai.

## Files

| File | Purpose |
|------|---------|
| `prompt.md` | Full system prompt with conversation flows, objection handling, compliance rules |
| `vapi_config.json` | Vapi assistant configuration (model, voice, transcriber settings) |
| `knowledge_base.md` | Grounded product facts the agent can reference |
| `tools/*.json` | Tool function definitions in Vapi format |

## Setup on Vapi.ai

### 1. Create an Assistant

1. Go to [Vapi Dashboard](https://dashboard.vapi.ai)
2. Create a new assistant
3. Copy the contents of `prompt.md` into the System Prompt field
4. Configure model: GPT-4o, temperature 0.3
5. Configure voice: ElevenLabs, select a professional Indian English female voice
6. Set transcriber: Deepgram Nova-2, language "en"

### 2. Register Tool Functions

For each file in `tools/`, create a corresponding tool in the Vapi assistant:

1. Go to the assistant's Tools section
2. Add each tool with the function definition from the JSON file
3. Set the server URL to your orchestrator's webhook endpoint:
   `https://your-orchestrator-url.com/api/vapi/webhook`

### 3. Configure Webhook

1. Set the assistant's Server URL to your orchestrator webhook
2. Set a webhook secret for security
3. The orchestrator will handle all tool calls at `/api/vapi/webhook`

### 4. Get a Phone Number

1. In Vapi dashboard, acquire a phone number (or bring your own via SIP)
2. Assign it to the Tiger Credit Card assistant
3. Note the Phone Number ID for outbound calls

### 5. Update Environment

Add to your `.env`:

```
VAPI_API_KEY=your-api-key
VAPI_ASSISTANT_ID=your-assistant-id
VAPI_PHONE_NUMBER_ID=your-phone-number-id
MOCK_MODE=false
```

### 6. Test

```bash
# Restart with real Vapi credentials
make restart

# Call a test number
python scripts/test_call.py --customer TC001 --phone +91XXXXXXXXXX
```

## Mock Mode

When `MOCK_MODE=true` (default), the system runs without Vapi. You can still:

- Test the webhook handler: `curl -X POST http://localhost:8000/api/vapi/webhook -H "Content-Type: application/json" -d '...'`
- Test the event pipeline: `make trigger`
- Run all unit tests: `make test`

This allows development and testing of the full orchestration layer without a Vapi account.
