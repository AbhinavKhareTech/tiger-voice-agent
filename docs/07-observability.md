# Observability

## Three-Layer Monitoring

Voice AI observability spans three layers, each serving different stakeholders and requiring different tools.

## Layer 1: System Metrics

Infrastructure health. Is the system working?

| Metric | Target | Alert Threshold | Source |
|--------|--------|----------------|--------|
| ASR Latency (p95) | <300ms | >500ms for 5 min | ASR engine metrics |
| LLM First Token (p95) | <400ms | >800ms for 5 min | LLM inference metrics |
| TTS First Chunk (p95) | <300ms | >500ms for 5 min | TTS engine metrics |
| End-to-End Latency (p95) | <800ms | >1500ms for 5 min | Session manager |
| Call Completion Rate | >95% | <90% for 1 hour | Telephony CDRs |
| API Gateway Error Rate | <1% | >2% for 5 min | API gateway logs |
| Event Consumer Lag | <60 sec | >300 sec | Consumer group offsets |
| Redis Hit Rate | >99% | <95% | Redis cluster metrics |
| Circuit Breaker Open | 0 systems | Any system open | Orchestrator health |

## Layer 2: Conversation Quality Metrics

Is the AI performing well in conversations?

| Metric | Definition | Target | Measurement |
|--------|-----------|--------|-------------|
| Talk-to-Listen Ratio | Agent speaking / total call time | 35-45% | Audio VAD analysis |
| Average Turn Length | Mean agent speaking turn duration | 5-12 seconds | TTS output timing |
| Sentiment Trajectory | Sentiment delta (end vs start) | Positive or neutral | Per-turn scoring |
| Objection Frequency | Objections per call | <2.0 avg | Intent classifier |
| NLU Confidence (mean) | Average intent classification confidence | >0.75 | Intent detector |
| Silence Duration (max) | Longest silence in conversation | <5 seconds | Audio analysis |
| Barge-in Rate | % turns where customer interrupts | <15% | Media server events |
| Repeat Rate | Agent repeats same info >1 time | <10% of calls | Transcript analysis |

## Layer 3: AI Quality Metrics

Is the AI safe and accurate?

| Metric | Definition | Target | Alert |
|--------|-----------|--------|-------|
| Hallucination Rate | % turns with ungrounded claims | <0.5% | >1% in 24h |
| Tool Call Accuracy | % tool calls with correct function + params | >98% | <95% in 24h |
| Intent Detection Accuracy | % intents correctly classified | >90% | <85% in 24h |
| Compliance Violation Rate | % calls with any rule breach | <0.1% | Any single violation |
| Escalation Appropriateness | % escalations rated necessary by review | >85% | <70% weekly |
| Grounding Score | % factual claims traceable to a variable | >99% | <97% in 24h |

## Monitoring Stack

### Prometheus + Grafana
System metrics scraped by Prometheus, visualized in Grafana. Pre-built dashboards: Voice Pipeline Health, Event Pipeline Health, Integration Health, Infrastructure Health.

### OpenTelemetry (Distributed Tracing)
Every call generates a trace spanning all four layers: SIP signaling, audio pipeline, LLM inference, tool calls, and enterprise API timing. Traces stored in Jaeger or Grafana Tempo, correlated by call ID.

### Conversation Analytics Pipeline
Custom pipeline (Spark or Databricks) processes transcripts and session metadata. Runs in real-time (compliance violations, hallucinations) and batch (weekly aggregates). Dashboards for: AI Solutions team (prompt performance), customer operations (conversion rates), customer business team (funnel analytics).

### Alerting
Alerts tiered by severity:
- **P1** (compliance violation, outage): immediate page + customer notification
- **P2** (degraded performance): Slack notification, 30-min response SLA
- **P3** (metric drift): captured in weekly review

All alerts include a runbook link with diagnostic steps.

## Business Metrics

| Metric | Definition | Baseline (Human) | Target (AI) |
|--------|-----------|------------------|-------------|
| Onboarding Completion Rate | % approved reaching Card Active | 35-40% | 55-65% |
| Stage Conversion Rate | % completing each transition | 60-70% | 75-85% |
| Activation Rate (30-day) | % activated within 30 days | 25-30% | 45-55% |
| Cost Per Activation | Total voice cost / activations | Rs 150-200 | Rs 30-50 |
| Average Handle Time | Mean call duration | 5-7 min | 3-4 min |
| Customer Satisfaction | Post-call CSAT (1-5) | 3.2-3.5 | 3.8-4.2 |
| First Call Resolution | % resolving in one call | 40-50% | 55-65% |
