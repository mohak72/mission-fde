# Technical Assumptions

## Repository Structure: Monorepo

A single monorepo (not polyrepo) because the explicit point of M1 is that it "births the platform" — LLM gateway, eval harness, deploy pipeline, landing-page template — and M2–M6 (`PipelineMedic`, `DocuMind`, `ChurnCast`, `ReconAI`) all reuse those pieces wholesale per the roadmap's "Reuses → New" column. A polyrepo would force premature versioning/publishing of internal packages for code that has exactly one consumer today. Structure: `apps/incident-copilot/` for the product-specific agent/webhook code, `platform/` for the gateway, tracing, and deploy templates meant for reuse, `docs/` for BMad artifacts.

## Service Architecture: Modular Monolith (single deployable), LangGraph-orchestrated

One FastAPI service containing the LangGraph state machine (classify → retrieve → investigate → propose → human-approval), not microservices. Rationale: the RFC's whole shape is one alert → one pipeline run; splitting into services now would add network hops and deploy complexity with no corresponding scaling need (NFR6: single-cluster, single-tenant MVP). The LLM gateway (NFR1) is a logical module inside the same deployable for M1, structured so it *can* be extracted into its own service for M2+ without a rewrite (it's already called through one internal interface, never bypassed).

## Testing Requirements: Unit + Integration + Eval-as-Test

Three tiers, deliberately not a full e2e/UI pyramid (there is no UI to test):
- **Unit**: pure functions — dedup logic, rate limiter, LRU cache, PII scrubber, runbook retrieval scoring.
- **Integration**: webhook → pipeline → (mocked LLM + real local vector store) → proposal, and the human-approval state transitions, run against a local `kind` cluster for the `kubectl` tool.
- **Eval-as-test (NFR4)**: the 20-incident synthetic eval (FR8) runs in CI like a test suite — a drop in retrieval hit-rate or judge score fails the build, not just a dashboard metric reviewed later. This is the FDE-grade practice the RFC's "Success Metric" section implies but doesn't operationalize into CI; I'm making it explicit here.

## Additional Technical Assumptions and Requests

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
