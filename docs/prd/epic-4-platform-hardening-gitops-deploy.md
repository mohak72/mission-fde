# Epic 4 Platform Hardening & GitOps Deploy

Epic Goal: Turn a locally-working service into an observable, CI-gated, GitOps-deployed one.

## Story 4.1 Observability: Tracing & Cost-per-Incident

As a platform operator,
I want every LLM call traced and cost-per-incident computed,
so that I can answer "what does one diagnosis cost" with a real number, not an estimate.

### Acceptance Criteria

1: Every LLM gateway call is traced (Langfuse or LangSmith) with model, token counts, latency, and cost recorded.
2: A cost-per-incident metric is computed by aggregating trace data per pipeline run and reported.
3: Traces never contain secrets/PII (NFR7/FR10) — verified by a test asserting no raw kubeconfig/API key appears in a trace payload.
4: The cost-per-incident number from a test run is captured in README/docs as a quotable figure.

## Story 4.2 Eval as CI Gate

As a developer,
I want the Story 3.4 eval harness to run automatically in CI and fail the build on regression,
so that a diagnosis-quality regression is caught before merge, not after deploy.

### Acceptance Criteria

1: The eval harness (Story 3.4) runs as a step in the GitHub Actions CI pipeline (building on Story 1.1's CI).
2: CI fails if retrieval hit-rate or judge score drops below a committed baseline threshold.
3: The baseline threshold is stored in the repo (not hardcoded in the workflow file), so updating it is a reviewable diff.
4: A CI badge in the README reflects current pipeline status.

## Story 4.3 Containerization & GitOps Deploy

As a platform operator,
I want the service deployed via Docker + Terraform + ArgoCD to a real cluster,
so that the product is a running, observable service, not something that only works on a laptop.

### Acceptance Criteria

1: The service is packaged as a Docker image, built in CI.
2: Terraform provisions the target infrastructure (OKE or equivalent) — no manually-created cloud resources.
3: ArgoCD deploys the service from Git repo state (GitOps) — no manual `kubectl apply` to the target environment (NFR2).
4: A deliberate failure (e.g., killing the pod) is demonstrated to auto-heal via the deployment controller, with a screenshot/log captured as proof.
5: Deployed service responds to a real webhook call end-to-end, not just locally.
