# Goals and Background Context

## Goals

- Ingest a simulated Prometheus alert via webhook and log it reliably.
- Retrieve the most relevant runbook from a 10-doc corpus via vector similarity search.
- Ground the diagnosis in live, read-only cluster state (`kubectl get/describe`).
- Propose a diagnosis + next-step action; require explicit human approval before any state-changing action.
- Produce quotable eval numbers (retrieval hit-rate ≥80%, LLM-judge diagnosis-usefulness) on a 20-incident synthetic set.
- Ship as a reusable platform: LLM gateway (rate-limited, cached), containerized, GitOps-deployed — because M2–M6 all build on what M1 lays down.
- Produce a concrete, demo-able, portfolio-grade artifact (8-min demo, case-study README, landing page) — not a toy.

## Background Context

On-call engineers spend repetitive, inconsistent effort triaging well-known failure modes: read alert → find runbook → run `kubectl` → diagnose → decide. Incident Copilot automates the diagnosis half of that loop while keeping a human in control of any action with real blast radius — a human-approve gate was chosen deliberately over auto-remediation (see RFC §5.3, `docs/design.md`) because a bad autonomous action is a one-way-door risk disguised as a two-way one.

This PRD also carries a second, equally real goal for this specific build: it is sprints S1–S15 of a 26-week "6 products in 6 months" program (`Mohak_FDE_Master_Roadmap.xlsx`) whose explicit purpose is learning an FDE-caliber skill set while shipping real software, in parallel with AWS AI Practitioner/Professional (AIP-C01) cert labs G1–G5, which are wired into this same build (Bedrock Converse, model-selection harness, Knowledge Bases, PII filtering, grounded citations). This PRD scopes the product; story-level docs carry the teaching/exam-domain tie-ins per sprint.

## Change Log

| Date | Version | Description | Author |
|---|---|---|---|
| 2026-11-04 | 0.1 | Initial PRD draft for M1 Incident Copilot, derived from RFC (docs/design.md) and roadmap sprints S0-S15 | John (PM) |
