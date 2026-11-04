# Epic 1 Foundation, Ingestion & Minimal CI

Epic Goal: Stand up a repo with real CI from commit one, and deliver the first vertical slice — an alert comes in, gets logged exactly once, and the system finds the right runbook for it.

## Story 1.1 Repo & CI Scaffolding

As a developer,
I want a repo scaffold with lint/test CI wired from the first commit,
so that every subsequent story inherits a working quality gate instead of retrofitting one later.

### Acceptance Criteria

1: Repository contains a Python 3.11+ FastAPI project scaffold matching the structure in Technical Assumptions (`apps/incident-copilot/`, `platform/`, `docs/`).
2: A GitHub Actions workflow runs on every push/PR — lint (ruff) + unit tests (pytest) — and fails the build on any failure.
3: README documents how to run the service locally and how to run tests.
4: Repo is pushed to a public GitHub repository.

## Story 1.2 Alert Ingestion Webhook

As an on-call engineer,
I want the service to accept a simulated Prometheus alert and log it,
so that I have a durable, queryable record of every alert the system has seen.

### Acceptance Criteria

1: `POST /webhook/alert` accepts a JSON payload matching the simulated Prometheus alert schema and returns 202 Accepted.
2: Each received alert is persisted (id, payload, received_at) before any further processing.
3: A duplicate delivery of the same alert ID does not create a second record or trigger a second pipeline run (FR2).
4: Requests without a valid HMAC signature / shared-secret header are rejected with 401 before any processing (NFR9).
5: Unit tests cover: valid signed payload accepted, malformed payload rejected (4xx), unsigned/invalid-signature payload rejected (401), duplicate ID deduplicated.

## Story 1.3 Runbook Corpus & Retrieval

As an on-call engineer,
I want the system to find the right runbook for an incoming alert,
so that diagnosis starts from the correct known failure mode instead of nothing.

### Acceptance Criteria

1: At least 10 runbooks (Markdown) exist, each describing one distinct failure mode.
2: Runbooks are embedded and stored in Chroma, accessible only through a single retrieval interface (NFR8) — nothing calls Chroma directly.
3: Given a test alert, the retrieval interface returns the correct runbook for at least 8/10 hand-labeled test cases.
4: Retrieval latency and the embedding model used are logged.
