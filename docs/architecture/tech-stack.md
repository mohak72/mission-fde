# Tech Stack

## Cloud Infrastructure

- **Provider:** Oracle Cloud Infrastructure (OKE) for compute/deploy; **Amazon Web Services (Bedrock)** for the LLM provider during S1–S12 only.
- **Key Services:** OCI Kubernetes Engine (OKE), AWS Bedrock Converse API (Nova Micro / Claude Haiku), swapping to OCI Gen AI + Oracle DB 23ai at Story 5.1 (S13).
- **Deployment Regions:** Single region for MVP (no multi-region requirement per PRD NFR6).

**This is a deliberate two-cloud split, not an oversight:** deploy infrastructure targets OCI (matching the RFC's stated OCI-native direction and the S13 migration target), while the LLM provider for S1–S12 is AWS Bedrock specifically because the AWS AIP-C01 cert labs (G1–G5 on `☁ AWS Labs`) require hands-on Bedrock Converse API usage mapped directly to this product. The LLM Gateway module (NFR1) is exactly what makes this tolerable — swapping Bedrock → OCI Gen AI at S13 is a provider-adapter change inside the gateway, not a re-architecture.

## Technology Stack Table

| Category | Technology | Version | Purpose | Rationale |
|---|---|---|---|---|
| **Language** | Python | 3.12 | Primary language | Modern, widely supported; satisfies PRD's "3.11+" with headroom |
| **Package manager** | uv | 0.9.x | Dependency management, lockfile | Fast, reproducible installs; generates a committed lockfile for the "no manual kubectl apply"-grade reproducibility bar this program sets everywhere |
| **Web framework** | FastAPI | 0.136.3 | Webhook HTTP API | Verified current as of 2026-11-04; per PRD Technical Assumptions |
| **ASGI server** | Uvicorn | 0.34.x | Serves FastAPI app | Standard FastAPI pairing |
| **Agent orchestration** | LangGraph | 1.2.14 | Diagnosis state machine | Verified current as of 2026-11-04; per PRD/RFC |
| **Vector store (MVP)** | Chromadb | 1.5.8 | Runbook retrieval (Story 1.3) | Verified current; per PRD — swapped to Oracle DB 23ai at Story 5.1 behind the Retrieval interface |
| **LLM provider SDK** | boto3 | 1.43.100 | AWS Bedrock Converse calls | Verified current; only module allowed to import this (NFR1) |
| **Kubernetes client** | kubernetes (official Python client) | 31.x | Read-only `get`/`describe` calls (Story 2.3) | Chosen over shelling out to the `kubectl` binary — typed responses, testable with a mock API client, and no risk of a shell-injection surface on alert-derived input |
| **MCP server** | fastmcp | 2.9.1 | Exposes `triage_alert` tool (Story 5.2) | Confirmed present on PyPI; **flagging low confidence on "latest"** — FastMCP's versioning was inconsistent across sources I checked. Re-verify at Story 5.2 implementation time before locking the lockfile. |
| **Config/secrets** | pydantic-settings | 2.7.x | Typed env-based config | Keeps NFR7 (no hardcoded secrets) enforceable via one settings module, not scattered `os.environ` calls |
| **Tracing** | Langfuse | 2.x (self-hosted or cloud) | LLM call tracing, cost-per-incident (Story 4.1) | Open-source option avoids a second paid SaaS dependency beyond Bedrock itself |
| **Linting** | ruff | 0.8.x | Lint + format | Single fast tool replacing flake8+black+isort; CI-gated from Story 1.1 |
| **Testing** | pytest + pytest-asyncio | 8.x / 0.25.x | Unit + integration tests | Matches PRD Test Strategy; async support needed for FastAPI/LangGraph |
| **Containerization** | Docker | 27.x | Packaging (Story 4.3) | Per PRD NFR2 |
| **IaC** | Terraform | 1.9.x | OKE provisioning (Story 4.3) | Per PRD NFR2/RFC |
| **GitOps deploy** | ArgoCD | 2.13.x | Deploy from Git state (Story 4.3) | Per PRD NFR2 — no manual `kubectl apply` |
| **Local K8s** | kind | 0.24.x | Local dev/test cluster for Story 2.3's kubectl tool | Matches RFC's stated dev target |
| **CI** | GitHub Actions | n/a (hosted) | Lint, test, eval-gate (Stories 1.1, 4.2) | Per PRD NFR4 |
| **SAST** | bandit | 1.8.x | Security lint in CI | Added during Security section review — catches Python security antipatterns ruff doesn't target |
| **Dependency audit** | pip-audit | 2.7.x | Vulnerable dependency detection in CI | Added during Security section review |

---

**⚠️ Elicitation required before continuing.**

Rationale / flags:
- **Two-cloud split (OCI deploy + AWS Bedrock LLM) is the single highest-impact decision in this table** — it's unusual to deploy on one cloud and call a model on another, and it only works because of the Gateway seam. If you'd rather simplify to one cloud for MVP (e.g., Bedrock-hosted compute too, or defer OKE until S13), say so now — this ripples into the Infrastructure/Deployment section later.
- FastMCP's version is genuinely uncertain from my research — I'm not going to pretend confidence I don't have; Story 5.2 is in Epic 5 (late), so there's time to re-check.
- Kubernetes Python client over shelling out to `kubectl` is my call, not stated in the PRD/RFC — flagging it because it's a real implementation-shaping decision for Story 2.3.

Select 1-9 or just type your question/feedback:

1. Proceed to next section (Data Models)
2. Expand on the two-cloud split — what specifically breaks if Bedrock access from OCI compute has latency/networking issues
3. Challenge from a different stakeholder's perspective (e.g., a cost-conscious reviewer asking "why two clouds")
4. Analyze what could go wrong if the Kubernetes Python client version drifts from the target cluster's K8s API version
5. Identify hidden assumptions in using uv instead of poetry/pip-tools
6. Red Team: argue for deploying on AWS entirely (since Bedrock's already there) instead of splitting clouds
7. Tree of Thoughts: 3 alternative LLM-provider choices for S1-S12 if not Bedrock, compared
8. Self-Consistency check: re-derive the stack independently from PRD Technical Assumptions + RFC and diff
9. Meta-review: critique this stack as if you were the infra-devops-platform agent about to write Terraform against it
