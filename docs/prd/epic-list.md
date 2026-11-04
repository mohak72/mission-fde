# Epic List

- **Epic 1: Foundation, Ingestion & Minimal CI** — Repo scaffolding, FastAPI webhook that ingests and logs a deduplicated alert, a 10-runbook corpus retrievable by vector similarity, and a minimal CI pipeline (lint + unit tests) running from day one — not bolted on at the end.
- **Epic 2: Evidence-Grounded Diagnosis Loop** — Rebuild the alert→retrieve→diagnose flow as an explicit LangGraph state machine, add the read-only `kubectl` tool so every diagnosis cites live cluster evidence instead of guessing.
- **Epic 3: Human-in-the-Loop & Quality Proof** — Ship the approve/reject gate (the actual demo moment), the rate limiter/cache/dedup inside the LLM gateway, and the 20-incident eval harness producing the hit-rate and judge numbers the whole product is judged on.
- **Epic 4: Platform Hardening & GitOps Deploy** — Add tracing + cost-per-incident, promote the eval harness into a CI gate that can fail a build, and deploy the whole thing via Docker + Terraform + ArgoCD to a real cluster — no manual `kubectl apply`.
- **Epic 5: Cloud Portability & Agent Interop** — Swap the model/vector backends to OCI Gen AI + Oracle DB 23ai behind the existing interfaces (proving NFR1/NFR8 actually hold), and expose a FastMCP tool so external agents (Claude Code) can call "triage this alert" directly.
- **Epic 6: Ship** — Demo video, case-study README, landing page, and launch post — the portfolio-grade artifact, not a side effect.

---

**⚠️ Elicitation required before continuing.**

Rationale / flags:
- 6 epics for 15 sprints (S1–S15) — erring toward slightly more epics than "fewest possible" because each one ends in a genuinely different deployable capability (ingest-only → evidence-grounded → trustworthy+measured → deployed → portable+agent-callable → shipped), and I think collapsing further would blur distinct review/demo points. Happy to merge Epic 5 into Epic 4 if you'd rather have 5.
- I pulled "minimal CI" into Epic 1 instead of leaving it at S11 as the sheet schedules — Epic 1 should never ship without a CI gate per modern SDLC practice; S11's contribution becomes "promote CI to also gate on eval regressions," which I moved into Epic 4.
- S4's DSA/retro/public-repo-push content isn't a product epic — the "push public" part lands as a task inside Epic 1's last story; the DSA/interview-prep content stays tracked in the roadmap sheets and becomes "concepts you need" framing in SM-authored stories, per your teaching decision.
