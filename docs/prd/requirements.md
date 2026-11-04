# Requirements

## Functional

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

## Non Functional

1. NFR1: All LLM calls route through a single internal gateway that enforces rate limiting (token-bucket) and response caching (LRU) — no component calls a model provider directly.
2. NFR2: The system is fully containerized and deployed via GitOps (Terraform + ArgoCD) to a real cluster (OKE/kind), not run only from a developer machine.
3. NFR3: Every LLM call is traced (Langfuse/LangSmith) with cost-per-incident computed and reported.
4. NFR4: Evaluation (FR8) runs in CI (GitHub Actions) on every change, and a regression in retrieval hit-rate or judge score fails the build.
5. NFR5: No auto-remediation code path exists in the codebase for MVP — this is an architectural constraint, not just a UI gate, so a prompt-injected or misbehaving LLM cannot cause a write action even if the approval step is bypassed in code.
6. NFR6: The system targets a single `kind`/OKE cluster and single-tenant scope for MVP; multi-cluster/multi-tenant is explicitly out of scope.
7. NFR7: Secrets and credentials (cluster kubeconfig, model API keys) are never logged or sent to the model provider, including inside traces.
8. NFR8: The vector store choice (Chroma for MVP, migrating to pgvector/OCI DB 23ai) must be swappable behind one interface so the S13 migration does not require touching retrieval call sites.
9. NFR9: The webhook endpoint verifies the authenticity of incoming requests (e.g., HMAC signature or shared-secret header) and rejects unsigned/invalid requests — added during PM checklist review; a production-shaped webhook that trusts any POST body is a real vulnerability, not an acceptable MVP shortcut, and mirrors how Alertmanager webhooks are actually secured.

## Out of Scope for MVP

Carried forward from the RFC (`docs/design.md` §3) so the Architect doesn't need to cross-reference a second document:

- No auto-remediation — the agent never executes a write action without explicit human approval (see NFR5).
- No multi-cluster or multi-tenant support — one `kind`/OKE cluster, single scope.
- No Slack/Telegram integration for MVP — CLI approval is the interim UX (FR7); chat-based approval is a post-MVP enhancement.
- No production Alertmanager/Prometheus wiring — simulated JSON payloads only.
- No fine-tuning — retrieval + prompting only.

## Key Risks (carried from RFC §6, for Architect visibility)

- Retrieval quality on only 10 runbooks is untested — may need query rewriting if hit-rate is low; this is exactly what Story 3.4's eval harness will surface, not something to pre-solve.
- `kubectl` read-only tool-calling reliability (does the LLM call it correctly, every time?) is unproven until Story 2.3 — Story 2.3 AC4's graceful-degradation behavior exists because of this risk.
- LLM gateway rate-limiting design was deferred until real usage patterns existed — now being built in Story 3.2; Architect should keep the token-bucket parameters configurable rather than hardcoded, since they're still a guess.
