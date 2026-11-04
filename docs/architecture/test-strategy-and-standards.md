# Test Strategy and Standards

## Testing Philosophy

- **Approach:** AC-driven, test-first where practical — each story's Acceptance Criteria (from the PRD) map directly to test cases written before or alongside the implementation, not strict textbook TDD, but never test-after-as-an-afterthought either.
- **Coverage Goals:** 80% line coverage target on business-logic modules specifically (`graph/`, `retrieval/`, `ingestion/`, `platform/gateway/`) — deliberately excluding thin wrapper/glue code (e.g. `api/`, `config.py`) from the percentage, so the number stays meaningful rather than being gamed by testing trivial pass-throughs.
- **Test Pyramid:** Unit + Integration + Eval-as-Test (per PRD Technical Assumptions) — no E2E/UI layer, since none exists.

## Test Types and Organization

### Unit Tests

- **Framework:** pytest 8.x
- **File Convention:** `test_<module>.py`, co-located under `tests/unit/`, mirroring `src/` 1:1
- **Location:** `apps/incident-copilot/tests/unit/`, `platform/tests/unit/`
- **Mocking Library:** `pytest-mock` (wraps `unittest.mock`)
- **Coverage Requirement:** 80% on business-logic modules (see Coverage Goals)

**AI Agent Requirements:**
- Generate tests for all public methods.
- Cover edge cases and error conditions explicitly named in each story's ACs (e.g., Story 1.2 AC5's four listed cases are four separate test functions, not one parametrized blob that could pass/fail opaquely).
- Follow AAA (Arrange, Act, Assert).
- Mock all external dependencies — `boto3`, the Kubernetes client, `chromadb` — a unit test never touches a network.

### Integration Tests

- **Scope:** Webhook/MCP entry → Ingestion → Diagnosis Graph → real local Postgres + real local Chroma + real local `kind` cluster, with the LLM Gateway mocked at its boundary for determinism, speed, and zero cost.
- **Location:** `apps/incident-copilot/tests/integration/`
- **Test Infrastructure:**
  - **Database:** Real Postgres via `docker-compose` (not mocked) — this is where the unique constraints from the Database Schema (one proposal per run, etc.) actually get exercised.
  - **Vector store:** Real local Chroma instance (not mocked) — this is where Story 1.3 AC3's "8/10 hand-labeled test cases" requirement is actually verified.
  - **Kubernetes:** Real local `kind` cluster — Story 2.3's AC is specifically about real `kubectl` behavior (including real timeouts for the degradation path), so mocking it here would test nothing meaningful.
  - **LLM Gateway:** Mocked/stubbed — real LLM calls are reserved for the Eval Harness tier, not integration tests, to keep this tier fast, deterministic, and free to run on every CI build.

### End-to-End Tests

- **Framework:** N/A — no UI exists. The **Eval Harness** (Story 3.4) running the real pipeline with real LLM calls against the fixed 20-incident set is this project's functional equivalent of an E2E suite, and it already has its own full specification in the PRD — not duplicated here.

## Test Data Management

- **Strategy:** Fixture-based. Synthetic alert payloads and synthetic runbooks live as fixtures, not hardcoded inline in test files.
- **Fixtures:** `tests/fixtures/` (alerts, runbooks, expected-diagnosis pairs)
- **Factories:** Lightweight factory functions (plain Python, not a `factory_boy` dependency — not justified at this project size) producing valid `Alert`/`Runbook` test objects with sensible defaults, override-able per test.
- **Cleanup:** Integration tests run against a dedicated test Postgres schema and a dedicated, uniquely-named Chroma collection per test session, both truncated/dropped on teardown — never the dev database.

## Continuous Testing

- **CI Integration:** Separate CI jobs for lint → unit → integration → eval-gate (Story 4.2), so a failure is immediately attributable to a tier, not a single opaque "CI failed" signal.
- **Performance Tests:** Out of scope for M1 — no NFR specifies a throughput/latency SLA beyond the fail-fast timeouts already defined in Error Handling Strategy. Naming this explicitly as a deliberate non-requirement, not a silent gap.
- **Security Tests:** Two concrete, automated checks constitute this project's security testing (not a SAST/DAST suite, which would be disproportionate at this scale): (1) a CI step statically checking `cluster/evidence.py` references no write/mutating Kubernetes verb (the NFR5 guard from Coding Standards), and (2) Story 4.1 AC3's test asserting no secret/PII pattern appears in any trace or log output.

---

**⚠️ Elicitation required before continuing.**

Rationale / flags:
- Mocking the LLM Gateway in integration tests but using real Postgres/Chroma/kind is an asymmetric choice — real infra where the point is testing real behavior (constraints, retrieval quality, kubectl timeouts), mocked where the point would just be cost/flakiness (LLM calls). Flagging because "mock everything in integration tests" or "mock nothing" are both more common defaults, and I picked a third option.
- 80% coverage target is a number I chose, not derived from the PRD — the PRD only required "tests exist and are testable," not a percentage. If you want a stricter or looser bar, this is the place to change it.

Select 1-9 or just type your question/feedback:

1. Proceed to next section (Security)
2. Expand on why 80%, not a higher/lower/no number at all
3. Challenge from a different stakeholder's perspective (e.g., QA designing Story 3.4's eval harness as the de facto E2E suite)
4. Analyze what could go wrong if integration tests become flaky because they depend on a real local kind cluster being up
5. Identify hidden assumptions in "mock the Gateway, use real everything else" for integration tests
6. Red Team: argue integration tests should mock Postgres/Chroma too, for CI speed and reliability
7. Tree of Thoughts: 3 alternative test-tier boundaries, compared
8. Self-Consistency check: re-derive this test strategy independently from the PRD's Technical Assumptions and diff
9. Meta-review: critique this section as if you were QA about to write Story 1.3's test-design
