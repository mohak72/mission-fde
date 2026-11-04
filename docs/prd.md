# Incident Copilot (M1) Product Requirements Document (PRD)

## Goals and Background Context

### Goals

- Ingest a simulated Prometheus alert via webhook and log it reliably.
- Retrieve the most relevant runbook from a 10-doc corpus via vector similarity search.
- Ground the diagnosis in live, read-only cluster state (`kubectl get/describe`).
- Propose a diagnosis + next-step action; require explicit human approval before any state-changing action.
- Produce quotable eval numbers (retrieval hit-rate ≥80%, LLM-judge diagnosis-usefulness) on a 20-incident synthetic set.
- Ship as a reusable platform: LLM gateway (rate-limited, cached), containerized, GitOps-deployed — because M2–M6 all build on what M1 lays down.
- Produce a concrete, demo-able, portfolio-grade artifact (8-min demo, case-study README, landing page) — not a toy.

### Background Context

On-call engineers spend repetitive, inconsistent effort triaging well-known failure modes: read alert → find runbook → run `kubectl` → diagnose → decide. Incident Copilot automates the diagnosis half of that loop while keeping a human in control of any action with real blast radius — a human-approve gate was chosen deliberately over auto-remediation (see RFC §5.3, `docs/design.md`) because a bad autonomous action is a one-way-door risk disguised as a two-way one.

This PRD also carries a second, equally real goal for this specific build: it is sprints S1–S15 of a 26-week "6 products in 6 months" program (`Mohak_FDE_Master_Roadmap.xlsx`) whose explicit purpose is learning an FDE-caliber skill set while shipping real software, in parallel with AWS AI Practitioner/Professional (AIP-C01) cert labs G1–G5, which are wired into this same build (Bedrock Converse, model-selection harness, Knowledge Bases, PII filtering, grounded citations). This PRD scopes the product; story-level docs carry the teaching/exam-domain tie-ins per sprint.

### Change Log

| Date | Version | Description | Author |
|---|---|---|---|
| 2026-11-04 | 0.1 | Initial PRD draft for M1 Incident Copilot, derived from RFC (docs/design.md) and roadmap sprints S0-S15 | John (PM) |

## Requirements

### Functional

1. FR1: The system exposes a webhook endpoint that accepts a simulated Prometheus alert JSON payload and persists it (logged, with an alert ID) before any processing begins.
2. FR2: The system deduplicates alerts by alert ID so a retried/duplicate webhook delivery does not trigger a second diagnosis pipeline run.
3. FR3: The system maintains a corpus of at least 10 runbooks (Markdown) and retrieves the most relevant one for a given alert using vector similarity search.
4. FR4: The system executes read-only `kubectl get`/`describe` calls against a target cluster to ground its diagnosis in live pod/resource state, and the diagnosis must cite the specific evidence retrieved.
5. FR5: The system produces a diagnosis (probable cause) and a proposed next-step action from the alert + runbook + live cluster evidence, via an explicit, inspectable state machine (not a single opaque LLM call).
6. FR6: The system never executes a state-changing action (e.g., restart, scale) without an explicit human approval step; a rejected proposal is logged as a no-op and takes no action.
7. FR7: The system supports a human approval interface (CLI acceptable for MVP; Slack/Telegram deferred) that presents the proposed action and records approve/reject with a timestamp and actor.
8. FR8: The system runs an evaluation harness against a fixed 20-incident synthetic set and reports retrieval hit-rate and an LLM-judge usefulness score as numbers that can be quoted.
9. FR9: The system exposes a FastMCP tool interface so an external agent (e.g., Claude Code) can invoke "triage this alert" directly.
10. FR10: The system filters/scrubs PII from alert payloads before they are indexed or sent to any model.
11. FR11: The system supports per-team/per-cluster metadata filters on runbook retrieval so one team's alert cannot surface another team's runbook/data.

### Non Functional

1. NFR1: All LLM calls route through a single internal gateway that enforces rate limiting (token-bucket) and response caching (LRU) — no component calls a model provider directly.
2. NFR2: The system is fully containerized and deployed via GitOps (Terraform + ArgoCD) to a real cluster (OKE/kind), not run only from a developer machine.
3. NFR3: Every LLM call is traced (Langfuse/LangSmith) with cost-per-incident computed and reported.
4. NFR4: Evaluation (FR8) runs in CI (GitHub Actions) on every change, and a regression in retrieval hit-rate or judge score fails the build.
5. NFR5: No auto-remediation code path exists in the codebase for MVP — this is an architectural constraint, not just a UI gate, so a prompt-injected or misbehaving LLM cannot cause a write action even if the approval step is bypassed in code.
6. NFR6: The system targets a single `kind`/OKE cluster and single-tenant scope for MVP; multi-cluster/multi-tenant is explicitly out of scope.
7. NFR7: Secrets and credentials (cluster kubeconfig, model API keys) are never logged or sent to the model provider, including inside traces.
8. NFR8: The vector store choice (Chroma for MVP, migrating to pgvector/OCI DB 23ai) must be swappable behind one interface so the S13 migration does not require touching retrieval call sites.
9. NFR9: The webhook endpoint verifies the authenticity of incoming requests (e.g., HMAC signature or shared-secret header) and rejects unsigned/invalid requests — added during PM checklist review; a production-shaped webhook that trusts any POST body is a real vulnerability, not an acceptable MVP shortcut, and mirrors how Alertmanager webhooks are actually secured.

### Out of Scope for MVP

Carried forward from the RFC (`docs/design.md` §3) so the Architect doesn't need to cross-reference a second document:

- No auto-remediation — the agent never executes a write action without explicit human approval (see NFR5).
- No multi-cluster or multi-tenant support — one `kind`/OKE cluster, single scope.
- No Slack/Telegram integration for MVP — CLI approval is the interim UX (FR7); chat-based approval is a post-MVP enhancement.
- No production Alertmanager/Prometheus wiring — simulated JSON payloads only.
- No fine-tuning — retrieval + prompting only.

### Key Risks (carried from RFC §6, for Architect visibility)

- Retrieval quality on only 10 runbooks is untested — may need query rewriting if hit-rate is low; this is exactly what Story 3.4's eval harness will surface, not something to pre-solve.
- `kubectl` read-only tool-calling reliability (does the LLM call it correctly, every time?) is unproven until Story 2.3 — Story 2.3 AC4's graceful-degradation behavior exists because of this risk.
- LLM gateway rate-limiting design was deferred until real usage patterns existed — now being built in Story 3.2; Architect should keep the token-bucket parameters configurable rather than hardcoded, since they're still a guess.

## Technical Assumptions

### Repository Structure: Monorepo

A single monorepo (not polyrepo) because the explicit point of M1 is that it "births the platform" — LLM gateway, eval harness, deploy pipeline, landing-page template — and M2–M6 (`PipelineMedic`, `DocuMind`, `ChurnCast`, `ReconAI`) all reuse those pieces wholesale per the roadmap's "Reuses → New" column. A polyrepo would force premature versioning/publishing of internal packages for code that has exactly one consumer today. Structure: `apps/incident-copilot/` for the product-specific agent/webhook code, `platform/` for the gateway, tracing, and deploy templates meant for reuse, `docs/` for BMad artifacts.

### Service Architecture: Modular Monolith (single deployable), LangGraph-orchestrated

One FastAPI service containing the LangGraph state machine (classify → retrieve → investigate → propose → human-approval), not microservices. Rationale: the RFC's whole shape is one alert → one pipeline run; splitting into services now would add network hops and deploy complexity with no corresponding scaling need (NFR6: single-cluster, single-tenant MVP). The LLM gateway (NFR1) is a logical module inside the same deployable for M1, structured so it *can* be extracted into its own service for M2+ without a rewrite (it's already called through one internal interface, never bypassed).

### Testing Requirements: Unit + Integration + Eval-as-Test

Three tiers, deliberately not a full e2e/UI pyramid (there is no UI to test):
- **Unit**: pure functions — dedup logic, rate limiter, LRU cache, PII scrubber, runbook retrieval scoring.
- **Integration**: webhook → pipeline → (mocked LLM + real local vector store) → proposal, and the human-approval state transitions, run against a local `kind` cluster for the `kubectl` tool.
- **Eval-as-test (NFR4)**: the 20-incident synthetic eval (FR8) runs in CI like a test suite — a drop in retrieval hit-rate or judge score fails the build, not just a dashboard metric reviewed later. This is the FDE-grade practice the RFC's "Success Metric" section implies but doesn't operationalize into CI; I'm making it explicit here.

### Additional Technical Assumptions and Requests

- **Language/runtime**: Python 3.11+, FastAPI for the webhook/API layer (per RFC §4).
- **Orchestration**: LangGraph for the agent state machine (S5); nodes are the unit of testability and the unit the "evidence-citation" requirement (FR4) attaches to.
- **Vector store**: Chroma for S2 MVP, migrating to pgvector/Oracle DB 23ai at S13 — isolated behind one retrieval interface (NFR8) so the swap doesn't touch call sites.
- **LLM provider path**: starts on whichever model the gateway is configured for at S1–S12, swaps to OCI Gen AI at S13 — this is exactly why NFR1 (single gateway, no direct provider calls) is a hard constraint and not a nice-to-have.
- **Observability**: Langfuse or LangSmith for tracing (S11); cost-per-incident is a computed, reported number, not an estimate.
- **CI/CD**: GitHub Actions for CI (lint, unit+integration tests, eval gate); Terraform for infra-as-code; ArgoCD for GitOps deploy to OKE (S12). No manual `kubectl apply` to the target environment — this is a non-negotiable DevOps-practice constraint for this program, not just this product.
- **Containerization**: Docker for the service; the `kind` cluster is the local dev/test target, OKE is the deployed target.
- **Secrets**: cluster kubeconfig and model API keys via environment/secret store, never committed, never logged, never included in LLM traces (NFR7) — this needs a concrete mechanism (e.g., Terraform-managed secret injection, `.env` excluded via `.gitignore`) decided by the Architect.
- **Interview/teaching surface**: FastMCP (S14) exposing a `triage_alert` tool — note this is a second transport (MCP) in addition to the webhook, which the Architect should design for from S1, not retrofit at S14 (ties to FR9 above).

---

**⚠️ Elicitation required before continuing.**

Rationale / flags:
- I chose "Modular Monolith" over strict "Monolith" or "Microservices" from the template's three choices — it's the closest fit but worth you knowing I didn't pick a template option verbatim.
- The CI/CD and GitOps-only-deploy assumption is a real constraint I'm elevating to "non-negotiable" based on your ask for DevOps/SDLC best practice everywhere, not something stated that strongly in the RFC itself.
- Secrets handling mechanism is flagged as an open decision for the Architect, not resolved here — PM-level scope ends at "must not leak," not "exactly how."

## Epic List

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

## Epic 1 Foundation, Ingestion & Minimal CI

Epic Goal: Stand up a repo with real CI from commit one, and deliver the first vertical slice — an alert comes in, gets logged exactly once, and the system finds the right runbook for it.

### Story 1.1 Repo & CI Scaffolding

As a developer,
I want a repo scaffold with lint/test CI wired from the first commit,
so that every subsequent story inherits a working quality gate instead of retrofitting one later.

#### Acceptance Criteria

1: Repository contains a Python 3.11+ FastAPI project scaffold matching the structure in Technical Assumptions (`apps/incident-copilot/`, `platform/`, `docs/`).
2: A GitHub Actions workflow runs on every push/PR — lint (ruff) + unit tests (pytest) — and fails the build on any failure.
3: README documents how to run the service locally and how to run tests.
4: Repo is pushed to a public GitHub repository.

### Story 1.2 Alert Ingestion Webhook

As an on-call engineer,
I want the service to accept a simulated Prometheus alert and log it,
so that I have a durable, queryable record of every alert the system has seen.

#### Acceptance Criteria

1: `POST /webhook/alert` accepts a JSON payload matching the simulated Prometheus alert schema and returns 202 Accepted.
2: Each received alert is persisted (id, payload, received_at) before any further processing.
3: A duplicate delivery of the same alert ID does not create a second record or trigger a second pipeline run (FR2).
4: Requests without a valid HMAC signature / shared-secret header are rejected with 401 before any processing (NFR9).
5: Unit tests cover: valid signed payload accepted, malformed payload rejected (4xx), unsigned/invalid-signature payload rejected (401), duplicate ID deduplicated.

### Story 1.3 Runbook Corpus & Retrieval

As an on-call engineer,
I want the system to find the right runbook for an incoming alert,
so that diagnosis starts from the correct known failure mode instead of nothing.

#### Acceptance Criteria

1: At least 10 runbooks (Markdown) exist, each describing one distinct failure mode.
2: Runbooks are embedded and stored in Chroma, accessible only through a single retrieval interface (NFR8) — nothing calls Chroma directly.
3: Given a test alert, the retrieval interface returns the correct runbook for at least 8/10 hand-labeled test cases.
4: Retrieval latency and the embedding model used are logged.

## Epic 2 Evidence-Grounded Diagnosis Loop

Epic Goal: Turn "runbook found" into an actual diagnosis — first with a simple LLM call, then rebuilt as an inspectable LangGraph state machine, then grounded in live cluster evidence instead of just runbook text.

### Story 2.1 LLM Triage Summary

As an on-call engineer,
I want the system to produce a cause + next-steps summary from the alert and its matched runbook,
so that I get an initial diagnosis without manually reading the runbook myself.

#### Acceptance Criteria

1: Given an alert + its retrieved runbook, the system calls the LLM gateway (never the model provider directly, per NFR1) and returns a structured diagnosis: probable cause + next-step action.
2: The diagnosis explicitly references which runbook section it drew from.
3: If retrieval returns no runbook above a confidence threshold, the system returns an explicit "no matching runbook" result rather than a hallucinated diagnosis.
4: Unit tests cover: happy path, low-confidence-retrieval fallback, gateway-call-failure handling (retry/error surfaced, not swallowed).

### Story 2.2 LangGraph State Machine Refactor

As a developer,
I want the diagnosis pipeline rebuilt as an explicit LangGraph state machine (classify → retrieve → propose → human-approval),
so that each stage is independently testable and the pipeline's state is inspectable rather than hidden inside one function.

#### Acceptance Criteria

1: Pipeline implemented as a LangGraph graph with distinct nodes: classify alert type, retrieve runbook, investigate (placeholder until Story 2.3), propose diagnosis+action, human-approval (stub returning "pending" until Epic 3).
2: Each node is unit-testable in isolation with mocked inputs/outputs.
3: Running an alert through the graph end-to-end produces the same diagnosis output as the pre-refactor Story 2.1 loop — verified by a regression fixture comparing old vs. new output on the same test alerts.
4: Graph state/transitions are logged so a run can be replayed/debugged from the log alone.

### Story 2.3 Read-Only kubectl Evidence Grounding

As an on-call engineer,
I want the diagnosis to cite live cluster state, not just the runbook text,
so that I can trust the diagnosis reflects what's actually happening right now, not a generic guess.

#### Acceptance Criteria

1: The investigate node calls read-only `kubectl get`/`describe` against the target cluster (local `kind` for dev/test) for resources relevant to the alert.
2: The tool is strictly read-only — no code path from this node to any write/mutating kubectl verb (NFR5).
3: The final proposal cites specific live evidence (e.g., "pod X in CrashLoopBackOff, restart count N") alongside the runbook citation.
4: If the cluster/tool call fails or times out, the system still returns a diagnosis, clearly flagged as "not grounded in live state," rather than failing the whole pipeline.

## Epic 3 Human-in-the-Loop & Quality Proof

Epic Goal: Make the product trustworthy and measurable — the gateway gets caching/rate-limiting discipline, the approval gate becomes real (not a stub), and a repeatable eval produces the numbers the whole product is judged on.

### Story 3.1 LLM Response Caching (LRU)

As a platform operator,
I want LLM/embedding responses cached,
so that repeated identical calls don't re-incur cost/latency and we have a benchmarked hit-rate number to quote.

#### Acceptance Criteria

1: The LLM gateway caches responses for identical (model, prompt) pairs using an LRU eviction policy with a configurable max size.
2: Cache hit-rate is measured and reported via a benchmark against a fixture set of repeated/near-repeated queries.
3: Cache is transparent to callers — no call site needs to know whether a response was cached or live.
4: Unit tests cover cache hit, cache miss, eviction under capacity pressure.

### Story 3.2 Rate Limiting & Alert Dedup

As a platform operator,
I want the gateway to enforce a token-bucket rate limit and alert ingestion to merge near-duplicate alerts by interval,
so that a noisy alert storm doesn't blow the model budget or spam the approval queue.

#### Acceptance Criteria

1: The LLM gateway enforces a token-bucket rate limiter (parameters configurable, not hardcoded — see Key Risks); requests over the limit are queued or rejected with a clear error, never silently dropped.
2: Alerts for the same underlying issue arriving within a configurable time window are merged (interval-merge) into a single pipeline run instead of N separate diagnoses.
3: Unit tests cover: limiter allows under limit, blocks over limit, recovers after window; interval-merge merges overlapping alerts and leaves non-overlapping ones separate.

### Story 3.3 Human Approval Gate (CLI)

As an on-call engineer,
I want to see the proposed diagnosis and action and explicitly approve or reject it,
so that no action is ever taken without my sign-off.

#### Acceptance Criteria

1: After a proposal is generated, a CLI command displays the diagnosis, evidence, and proposed action, and prompts for approve/reject.
2: An approval is logged with actor + timestamp and marks the proposal "approved — would execute" (no real executor exists yet for MVP).
3: A rejection is logged with actor + timestamp and the run ends as a no-op — nothing is executed.
4: The human-approval stub from Story 2.2 is replaced by this real implementation.
5: This fulfills FR6/FR7 — the literal "demo moment" from the RFC.

### Story 3.4 Evaluation Harness

As a product owner,
I want a repeatable eval scoring retrieval hit-rate and diagnosis usefulness on a fixed 20-incident set,
so that I have a quotable, defendable quality number instead of a vibe.

#### Acceptance Criteria

1: A fixed synthetic set of 20 incidents exists, each with a known-correct expected runbook.
2: Running the eval reports retrieval hit-rate (% correct runbook retrieved) across the full set.
3: Running the eval reports an LLM-judge usefulness score per diagnosis, via a judge call distinct from the diagnosis call itself.
4: The eval runs as a single command and produces a persisted report (JSON/markdown) that can be committed or attached to a PR.
5: Target retrieval hit-rate ≥80% (FR8) — if below, this is flagged as a known gap, not hidden.

## Epic 4 Platform Hardening & GitOps Deploy

Epic Goal: Turn a locally-working service into an observable, CI-gated, GitOps-deployed one.

### Story 4.1 Observability: Tracing & Cost-per-Incident

As a platform operator,
I want every LLM call traced and cost-per-incident computed,
so that I can answer "what does one diagnosis cost" with a real number, not an estimate.

#### Acceptance Criteria

1: Every LLM gateway call is traced (Langfuse or LangSmith) with model, token counts, latency, and cost recorded.
2: A cost-per-incident metric is computed by aggregating trace data per pipeline run and reported.
3: Traces never contain secrets/PII (NFR7/FR10) — verified by a test asserting no raw kubeconfig/API key appears in a trace payload.
4: The cost-per-incident number from a test run is captured in README/docs as a quotable figure.

### Story 4.2 Eval as CI Gate

As a developer,
I want the Story 3.4 eval harness to run automatically in CI and fail the build on regression,
so that a diagnosis-quality regression is caught before merge, not after deploy.

#### Acceptance Criteria

1: The eval harness (Story 3.4) runs as a step in the GitHub Actions CI pipeline (building on Story 1.1's CI).
2: CI fails if retrieval hit-rate or judge score drops below a committed baseline threshold.
3: The baseline threshold is stored in the repo (not hardcoded in the workflow file), so updating it is a reviewable diff.
4: A CI badge in the README reflects current pipeline status.

### Story 4.3 Containerization & GitOps Deploy

As a platform operator,
I want the service deployed via Docker + Terraform + ArgoCD to a real cluster,
so that the product is a running, observable service, not something that only works on a laptop.

#### Acceptance Criteria

1: The service is packaged as a Docker image, built in CI.
2: Terraform provisions the target infrastructure (OKE or equivalent) — no manually-created cloud resources.
3: ArgoCD deploys the service from Git repo state (GitOps) — no manual `kubectl apply` to the target environment (NFR2).
4: A deliberate failure (e.g., killing the pod) is demonstrated to auto-heal via the deployment controller, with a screenshot/log captured as proof.
5: Deployed service responds to a real webhook call end-to-end, not just locally.

## Epic 5 Cloud Portability & Agent Interop

Epic Goal: Prove the abstraction boundaries from Epics 1–4 actually hold by swapping providers behind them, and open a second, agent-native way to use the product without creating a second implementation.

### Story 5.1 OCI Gen AI & DB 23ai Swap

As a platform operator,
I want to swap the LLM provider to OCI Gen AI and the vector store to Oracle DB 23ai behind the existing gateway/retrieval interfaces,
so that the NFR1/NFR8 abstraction claims are proven true, not just assumed.

#### Acceptance Criteria

1: The LLM gateway's underlying provider is swapped to OCI Gen AI without any change to call sites outside the gateway module (proves NFR1).
2: The vector store is swapped from Chroma to Oracle DB 23ai vector search without any change to call sites outside the retrieval interface (proves NFR8).
3: The full eval harness (Story 3.4) is re-run against the OCI-native configuration and the hit-rate/judge numbers are reported alongside the original, for comparison.
4: Any behavioral differences (latency, cost, quality) between the two configurations are documented.

### Story 5.2 FastMCP Tool Interface

As an external agent (e.g., Claude Code),
I want to call "triage this alert" as an MCP tool,
so that Incident Copilot's diagnosis capability can be used programmatically outside its own webhook/CLI surface.

#### Acceptance Criteria

1: A FastMCP server exposes a `triage_alert` tool taking an alert payload and returning the diagnosis — reusing the same pipeline as the webhook path, not a separate implementation.
2: The tool is demonstrably callable from Claude Code (or an equivalent MCP client) end-to-end.
3: The MCP transport is subject to the same gateway rate-limiting/caching as the webhook transport — no bypass of NFR1 via a second entry point.
4: Tests cover a successful tool call and an invalid-payload tool call.

## Epic 6 Ship

Epic Goal: Convert the working, deployed, measured product into a public artifact a stranger (interviewer, hiring manager, HN reader) can understand and judge in minutes.

### Story 6.1 Demo & Case-Study Publication

As a product owner (and job-seeking engineer),
I want a demo video, case-study README, and landing page published,
so that this product is a legible, shareable portfolio artifact, not just working code.

#### Acceptance Criteria

1: An 8-minute-or-less demo video exists showing: alert in → runbook retrieved → evidence-grounded diagnosis → human approval → MCP tool call from Claude Code (Epic 5).
2: A case-study README documents the problem, architecture, and trade-offs (reusing RFC content) plus the real eval numbers (retrieval hit-rate, judge score, cost-per-incident) from Stories 3.4/4.1/5.1 — no placeholder numbers.
3: A landing page (using the shared platform's landing template per the roadmap) is published, linking to the demo and case study.
4: A launch post (e.g., LinkedIn) is drafted and published.
5: Design Reps tracking (docs) is updated to reflect the RFC/retro items this epic closes out.

## Checklist Results Report

Ran `pm-checklist` against this PRD in comprehensive mode.

### Executive Summary

- **Overall PRD completeness:** ~85%
- **MVP scope appropriateness:** Just Right — every epic maps to a real roadmap sprint group with a concrete deliverable; nothing speculative was added beyond NFR9 (webhook auth) and the "architectural no-autofix" framing (NFR5), both defensible hardenings.
- **Readiness for architecture phase:** Ready
- **Most critical gap found and fixed during this review:** missing webhook authentication requirement (NFR9) — added, with a corresponding AC in Story 1.2.

### Category Analysis

| Category | Status | Critical Issues |
|---|---|---|
| 1. Problem Definition & Context | PARTIAL | No formal user research or competitive analysis — expected and acceptable for a solo portfolio/learning build, but flagged rather than silently assumed. Problem impact isn't quantified with a baseline number. |
| 2. MVP Scope Definition | PASS | Out-of-Scope section added during this review to avoid Architect needing to cross-reference the RFC. |
| 3. User Experience Requirements | PARTIAL (N/A by design) | No UI exists for MVP (CLI-only per RFC); section correctly skipped per template condition, but noted explicitly rather than left silent. |
| 4. Functional Requirements | PASS | FRs are testable, WHAT-not-HOW, consistently numbered. |
| 5. Non-Functional Requirements | PASS (after fix) | Webhook authentication (NFR9) was missing and is now added with an enforcing AC in Story 1.2. |
| 6. Epic & Story Structure | PASS | Epic 1 includes scaffolding, CI, and local testability from the start, per checklist §6.3. |
| 7. Technical Guidance | PASS | Key Risks section added so Architect inherits RFC's risk register instead of needing to re-read it. |
| 8. Cross-Functional Requirements | PARTIAL | No formal data-retention policy for alert/runbook storage — acceptable gap for MVP, flagged as LOW priority for Architect to make an explicit (even if simple) call rather than leave implicit. |
| 9. Clarity & Communication | PASS | This is a one-person program (you are PM/Architect/Dev/QA); formal "stakeholder alignment" doesn't apply in the traditional sense — noted rather than faked. |

### Top Issues by Priority

- **BLOCKERS:** None remaining — the one blocker found (missing webhook auth) was fixed in this review.
- **HIGH:** None.
- **MEDIUM:** Problem impact has no quantified baseline (e.g., "manual triage takes N minutes") — low cost to add if you want it for the eventual case-study README (Epic 6), not required to proceed.
- **LOW:** Data retention policy for stored alerts/runbooks is implicit (keep forever, by omission) — Architect should make this an explicit one-line decision, not carry the ambiguity forward.

### MVP Scope Assessment

- Nothing flagged for cutting — every FR/epic traces to a specific roadmap sprint.
- No essential feature found missing.
- Timeline: the roadmap allots 5 weeks (S0–S15) to 6 epics; Epic 4 (Terraform/ArgoCD/Docker) and Epic 5 (OCI/DB23ai swap + FastMCP) are the two most likely to overrun their sprint-sheet hour estimates — flagged for Architect/SM awareness, not a scope objection.

### Technical Readiness

- Technical constraints are clear and non-negotiable where it matters (NFR1 gateway-only LLM calls, NFR2 GitOps-only deploy, NFR5 architectural no-autofix, NFR8 swappable vector store).
- Key technical risk for Architect's deep-dive: whether the "single retrieval interface" and "single gateway" abstractions (NFR1/NFR8) can really stay clean through the Epic 5 provider swap — Story 5.1 is the test of that claim, and if it's hard, that's a signal to revisit the abstraction, not just push through.

### Final Decision

**READY FOR ARCHITECT.**

## Next Steps

### UX Expert Prompt

Not applicable for this PRD — M1 Incident Copilot's MVP interaction surface is CLI-only (human approval gate, Story 3.3); Slack/Telegram UX is explicitly deferred past MVP. Revisit this prompt when that work is scheduled.

### Architect Prompt

Use this PRD (`docs/prd.md`) plus the RFC (`docs/design.md`) as input to create the architecture document. Key things this PRD needs from you, specifically:

1. Concrete module boundaries for the "single LLM gateway" (NFR1) and "single retrieval interface" (NFR8) — these are promises this PRD makes that Epic 5 will test by swapping providers behind them; design them to actually hold.
2. A secrets-handling mechanism satisfying NFR7 (cluster kubeconfig + model API keys never logged/traced) — this PRD deliberately left the "how" to you.
3. `coding-standards.md`, `tech-stack.md`, and `source-tree.md` under `docs/architecture/` — these are referenced by `core-config.yaml`'s `devLoadAlwaysFiles` and are required before the SM can draft stories against them.
4. A concrete webhook signature/auth mechanism satisfying NFR9 (added during PM checklist review).
5. Explicit guidance on the Modular Monolith → extracted-gateway-service seam, since M2 (PipelineMedic) is already scheduled to reuse the gateway as a dependency, not duplicate it.
