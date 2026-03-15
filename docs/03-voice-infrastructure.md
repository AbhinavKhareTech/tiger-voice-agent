# Voice Infrastructure

## Why Voice Latency Matters

Perceived latency is the single most important quality metric in voice AI. Humans expect a response within 500-800ms. Above 1.5 seconds feels unnatural. Above 3 seconds causes the customer to ask "Hello? Are you there?" and erodes trust.

## The Latency Budget

| Stage | Non-Streaming | Streaming | How |
|-------|--------------|-----------|-----|
| ASR (full utterance) | 800-1500ms | 100-300ms | Partial transcripts start immediately |
| Intent + Slot Filling | 50ms | 50ms | Already fast |
| LLM Agent Planner | 500-1000ms | 200-400ms | Streaming inference, speculative decoding |
| Tool Execution | 100-300ms | 100-300ms | Depends on backend (no change) |
| Response Generation | 500-1000ms | 200-400ms | Stream tokens to TTS immediately |
| TTS (full synthesis) | 500-1000ms | 150-300ms | Chunk-based synthesis on first sentence |
| **TOTAL (perceived)** | **2.5-5.0s** | **400-800ms** | **Pipelining eliminates sequential wait** |

The key insight: every component operates on partial data. ASR does not wait for the customer to finish speaking. The agent does not wait for the full transcript. TTS does not wait for the full response text.

## Streaming Audio Pipeline

1. Customer speaks. Audio captured at 8kHz (PSTN) or 16kHz (WebRTC/app), packetized into 20ms RTP frames.
2. RTP frames arrive at media server. Jitter buffering, echo cancellation, noise suppression applied.
3. Clean audio forwarded to ASR via WebSocket as a continuous byte stream.
4. ASR produces partial transcripts (every 100-300ms) and final transcripts (at VAD silence boundaries).
5. Agent processes transcript, generates response. Text streamed token-by-token to TTS.
6. TTS synthesizes audio in chunks (200-400ms each), streams to media server.
7. Media server transmits synthesized audio back to customer as RTP frames.

## Turn-Taking and Barge-In

**Barge-in detection:** The media server monitors customer audio even while the agent is speaking. When Voice Activity Detection triggers on customer audio during agent speech, the system has 200ms to distinguish genuine interruption from backchannel ("uh-huh", "okay"). Genuine interruptions stop TTS playback immediately and route new audio to ASR.

**Endpointing:** Determining when the customer has finished speaking uses a combination of silence duration (primary, 500-700ms), syntactic completeness (secondary, partial transcript analysis), and prosodic cues (falling intonation). Default: 600ms silence threshold, adjusted dynamically per customer within the call.

**Graceful interruption:** When interrupted, the agent preserves its partially generated response. The planner receives both the interrupted response and the customer's new input, allowing it to continue from where it was cut off or pivot to a new topic.

## SIP Gateway

Handles call signaling for outbound calls. When the orchestrator decides to call a customer, it sends a SIP INVITE to the gateway. The gateway handles codec negotiation (G.711 for PSTN, Opus for WebRTC), call progress detection (ring, busy, voicemail), and call teardown. Must support SIP REFER for warm transfers to human agents.

**Production requirement:** Deploy across at least two availability zones. In India, connect to local PSTN carriers via direct SIP trunks to minimize latency and comply with data localization.

## In-App Voice (WebRTC)

For customers interacting through the Tiger app, WebRTC provides: higher audio quality (Opus at 16kHz vs G.711 at 8kHz), lower latency (direct peer connection), visual prompts alongside voice (showing the eKYC deep link on screen while explaining), and zero telephony costs.
