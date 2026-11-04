# RFC: Incident Copilot (MVP) — M1, Sprint S0

**Author:** mohak · **Status:** Draft · **Sprint:** S0 · **Reversibility:** Two-way door (MVP-scoped, cheap to change)

## 1. Problem / Context

When an alert fires (e.g. a Prometheus alert for a crashing pod), an on-call engineer has to: read the alert, remember or search for the relevant runbook, run `kubectl` commands to confirm the actual cluster state, form a diagnosis, and decide on an action. This is slow, inconsistent across engineers, and repetitive for well-known failure modes. Incident Copilot automates the *diagnosis* half of this loop — retrieve the right runbook, ground it in live cluster state, and propose next steps — while keeping a human in control of any action that changes state.

This is also the platform-founding product: the LLM gateway, RAG stack, eval harness, and deploy pipeline built here get reused by all five later products (M2–M5).

## 2. Goals

- Ingest an alert (simulated Prometheus JSON payload via webhook) and log it
- Retrieve the most relevant runbook from a small corpus using vector similarity search
- Ground the diagnosis in live (read-only) cluster state via `kubectl get/describe`
- Propose a diagnosis + next-step action, and require explicit human approval before any action is taken
- Produce quotable eval numbers (retrieval hit-rate, LLM-judge accuracy) on a 20-incident synthetic set
- Ship as a reusable platform: LLM gateway (rate-limited, cached), containerized, GitOps-deployed

## 3. Non-Goals (MVP)

- **No auto-remediation.** The agent never executes a write action (restart pod, scale deployment, etc.) without a human clicking approve. Auto-fix is explicitly out of scope for M1.
- No multi-cluster or multi-tenant support — one `kind` cluster, one demo scope.
- No Slack/Telegram integration until S8 (CLI approval is the interim UX).
- No production alert source integration (real Prometheus/Alertmanager wiring) — simulated JSON payloads only.
- No fine-tuning — retrieval + prompting only.

## 4. Architecture Sketch

```
Alert (simulated Prometheus JSON)
        │
        ▼
  FastAPI webhook  ──log──▶  (S1)
        │
        ▼
  LangGraph state machine  (S5)
   ┌─────────────┬───────────────┬────────────────┬──────────────────┐
   │  classify   │  retrieve     │  investigate    │  propose          │
   │  alert type │  runbook      │  (read-only     │  diagnosis +      │
   │             │  (pgvector/   │  kubectl        │  next-step action │
   │             │  Chroma, S2)  │  get/describe,  │                   │
   │             │               │  S6)            │                   │
   └─────────────┴───────────────┴────────────────┴────────┬──────────┘
                                                             ▼
                                                  Human-approval gate (S8)
                                                             │
                                                  approve ───┴─── reject
                                                     │              │
                                                (logged action)  (logged, no-op)
```

Shared platform pieces born here: LLM gateway (token-bucket rate limit + LRU cache, S10/S7), Langfuse/LangSmith tracing (S11), Dockerfile + Terraform + ArgoCD deploy (S12).

## 5. Alternatives Considered

### 5.1 Alert ingestion: Webhook vs. Polling

| | Webhook (push) | Polling (pull) |
|---|---|---|
| **Pros** | Real-time; matches how Alertmanager actually integrates in production; simpler mental model (one POST handler) | No public endpoint needed; agent controls its own pace/backoff |
| **Cons** | Needs a reachable endpoint (tunneling/ngrok for local dev); must handle retries/duplicate delivery | Adds latency (poll interval); wastes cycles polling when idle; doesn't match real Alertmanager behavior |

**Decision: Webhook.** It mirrors the real integration pattern (Alertmanager/PagerDuty webhooks), it's the pattern every later product reuses (P2's GitHub webhook, D-series don't need it but the gateway does), and idempotency can be handled cheaply with an alert-ID dedup check — a two-way door if it's wrong.

### 5.2 Vector store: pgvector vs. managed vector DB

| | pgvector (self-hosted, on Postgres) | Managed (Pinecone / Chroma Cloud) |
|---|---|---|
| **Pros** | One less external dependency/account; same DB can later hold app state; free; matches OCI DB 23ai swap planned for S13 | Zero ops, better default recall/perf at scale, faster to stand up today |
| **Cons** | More setup now (extension, indexing); performance tuning is on you | Vendor dependency; another API key/service to manage; costs money at scale; doesn't match the OCI-native direction this product is headed (S13) |

**Decision: pgvector (via local Chroma for S2, migrating to pgvector/OCI 23ai at S13).** The corpus is 10 runbooks — recall at this scale is a non-issue either way, so optimize for the path that matches where the product is going (S13: OCI Gen AI + DB 23ai vector search), not for premature scale.

### 5.3 Remediation: Human-approve vs. Auto-fix

| | Human-approve (HITL gate) | Auto-fix |
|---|---|---|
| **Pros** | Safe by construction — no blast radius from a bad LLM decision; matches enterprise trust story (relevant to every target company); the "approve" click is literally the demo moment (S8) | Faster MTTR in theory; more impressive automation claim |
| **Cons** | Slower resolution than full automation; still requires a human on-call | High blast radius if the agent misdiagnoses and acts — one bad auto-restart in a demo or in prod destroys credibility instantly |

**Decision: Human-approve for MVP, full stop.** This is a one-way-door-shaped risk (a bad auto-action is hard to undo and easy to regret publicly) disguised as a two-way technical choice — treat it accordingly. Auto-fix can be revisited post-M1 once eval numbers (S9) prove diagnosis accuracy.

## 6. Risks / Open Questions

- Retrieval quality on only 10 runbooks is untested — may need query rewriting if hit-rate is low (surface this at S9, not before).
- `kubectl` read-only tool-calling reliability (does the LLM call it correctly, every time?) is unproven until S6.
- LLM gateway rate-limiting design (S10) isn't decided yet — deferring until real usage patterns exist from S3 onward, per Progressive Complexity.

## 7. Success Metric

- Retrieval hit-rate ≥ 80% and a published LLM-judge diagnosis-usefulness score, both measured on a 20-incident synthetic eval set (S9).
- Cost-per-incident published from LangSmith/Langfuse tracing (S11).

## 8. Next Step

S1: Repo init + FastAPI webhook receiving and logging a simulated alert.
