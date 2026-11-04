# Coding Standards

## Core Standards

- **Languages & Runtimes:** Python 3.12, dependency management via `uv`.
- **Style & Linting:** `ruff` (lint + format), config in `pyproject.toml`, enforced in CI (Story 1.1) — not a local-only convention.
- **Test Organization:** `pytest`; `tests/unit/` mirrors `src/` package structure 1:1; `tests/integration/` is flat, named by capability (e.g., `test_webhook_to_diagnosis.py`), not by source file.

## Naming Conventions

No deviations from standard Python (PEP 8) conventions — omitting the table since there's nothing project-specific to override.

## Critical Rules

These are the rules an AI dev agent is most likely to violate by taking the locally-convenient shortcut instead of respecting an architectural seam. Everything else, assume standard good practice.

- **Never call a raw provider SDK exception outside its owning module:** `botocore.exceptions.*` may only be caught inside `platform/gateway/`; `kubernetes.client.exceptions.*` may only be caught inside `apps/incident-copilot/.../cluster/evidence.py`. Everywhere else catches `GatewayError`/`ClusterEvidenceError`.
- **Never import `chromadb` (or an Oracle DB 23ai client) outside `retrieval/`.** This is the NFR8 seam — a direct import anywhere else breaks the Story 5.1 swap guarantee.
- **Never import `boto3` or an OCI Gen AI client outside `platform/gateway/`.** This is the NFR1 seam — same reasoning.
- **`cluster/evidence.py` may only call read verbs** (`get`, `list`, `describe`-equivalent) on the Kubernetes API. No `patch`/`delete`/`create`/`replace` call may ever be added here or anywhere else against the target cluster — this is NFR5 enforced in code, not just in review.
- **No action-executor exists.** Don't add one "just to make the demo feel real." If a future story genuinely needs to execute an action, that's a new architecture decision, not an incremental addition to the approval path.
- **Never use `print()` or unstructured logging.** Use `structlog`, and every log call within a pipeline run must include `pipeline_run_id`.
- **Never log or trace a raw alert payload, kubeconfig, or API key.** Scrub first (ties to NFR7/NFR10).
- **All database access goes through `persistence/repositories.py`.** No raw SQL or ORM queries written inline in `graph/`, `api/`, or `approval/`.
- **All config/secrets are read through `config.py`'s `pydantic-settings` object.** No scattered `os.environ.get(...)` calls elsewhere.

## Language-Specific Guidelines

- **Python:** Type hints are required on all public function signatures (not enforced by a strict mypy gate for MVP — `ruff` catches obvious issues — but this is a hard review expectation). Use `pydantic` models (not raw `dict`) for anything crossing a module boundary defined in the Data Models section.

---

**⚠️ Elicitation required before continuing.**

Rationale / flags:
- I kept this to 8 critical rules, all directly enforcing an NFR or a seam from earlier sections — resisted the urge to add generic rules ("write clean code," "use SOLID") per the template's own warning that bloat here slows every future Dev session.
- Type hints "required but not strictly mypy-gated" is a middle ground I chose — a full mypy CI gate is more rigor but also more setup; flagging in case you want the stricter version for the "YC-grade" bar.

Select 1-9 or just type your question/feedback:

1. Proceed to next section (Test Strategy and Standards)
2. Expand on what a full mypy gate would add/cost if you want strict typing enforced in CI
3. Challenge from a different stakeholder's perspective (e.g., Dev seeing these 8 rules for the first time at Story 1.1)
4. Analyze what could go wrong if ruff's config doesn't actually catch a violation of one of these architectural rules (e.g., the boto3-only-in-gateway rule needs a custom lint rule, not just ruff defaults)
5. Identify hidden assumptions in assuming structlog's context propagates correctly without a rule enforcing *how* to set it
6. Red Team: argue these 8 rules are still too many / could be cut further
7. Tree of Thoughts: 3 alternative ways to enforce the import-boundary rules (code review only vs. custom lint rule vs. architecture test)
8. Self-Consistency check: re-derive these rules independently from the NFRs and diff
9. Meta-review: critique this section as if you were Dev reading it for the first time with zero other context
