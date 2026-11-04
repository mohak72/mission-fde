# Error Handling Strategy

## General Approach

- **Error Model:** Python exceptions, not error-code return values. FastAPI exception handlers translate internal exceptions to HTTP status codes at the API boundary only — internal code never deals in HTTP concepts.
- **Exception Hierarchy:** A single base `IncidentCopilotError`, with subclasses: `IngestionError` (invalid signature, malformed payload), `RetrievalError`, `ClusterEvidenceError` (caught internally to trigger graceful degradation — Story 2.3 AC4 — never surfaced past the investigate node), `GatewayError` (LLM call failure), `ApprovalError`.
- **Error Propagation:** Each graph node either handles its own failure gracefully in-graph (only `ClusterEvidenceError`, by design) or lets the exception propagate, which the graph's outer run loop catches, marks `PipelineRun.status = 'failed'`, logs with full context, and re-raises nothing further — a failed run is a terminal, inspectable state, never a silent swallow (this directly satisfies Story 2.1 AC4's "surfaced, not swallowed").

## Logging Standards

- **Library:** `structlog` 24.x
- **Format:** JSON lines — one structured object per log entry, never bare `print`/f-string logging anywhere in the codebase (this is going in Critical Rules below).
- **Levels:** `DEBUG` (node-internal detail, dev-only); `INFO` (pipeline milestones: alert received, runbook retrieved, diagnosis produced, decision recorded); `WARNING` (graceful degradation events, e.g. kubectl timeout); `ERROR` (unhandled failure, run marked failed); `CRITICAL` unused in M1.
- **Required Context:**
  - **Correlation ID:** `pipeline_run_id` — every log line emitted during one run carries it, making Story 2.2 AC4's "replayable from the log alone" requirement actually true.
  - **Service Context:** component name (`ingestion`, `graph.retrieve`, `gateway`, `cluster_evidence`, `approval_cli`, `eval_harness`).
  - **User Context:** `actor` field on Approval CLI log lines only; no end-user identity exists elsewhere.
  - **Hard rule, not optional:** no raw alert payload, kubeconfig, or model API key ever appears in a log line — this is the same guarantee Story 4.1 AC3 tests for traces, extended to logs generally.

## Error Handling Patterns

### External API Errors (Bedrock/OCI Gen AI via Gateway; Kubernetes API via Cluster Evidence Tool)

- **Retry Policy:** Exponential backoff with jitter, max 3 attempts, only for transient errors (timeouts, 5xx, throttling responses) — never retried for 4xx/bad-request-shaped provider errors, which indicate a bug, not transience.
- **Circuit Breaker:** The Gateway trips per-provider after N consecutive failures within a rolling window and fails fast rather than queuing more calls behind a known-bad provider — this protects the rate-limit budget (NFR1) from being burned on calls that will fail anyway.
- **Timeout Configuration:** LLM calls: 30s. Kubernetes API calls: 5s — deliberately short, because Story 2.3 AC4's graceful degradation depends on failing fast, not hanging the whole pipeline waiting on a slow cluster.
- **Error Translation:** Raw `botocore.exceptions.ClientError` and `kubernetes.client.exceptions.ApiException` are caught and translated to `GatewayError`/`ClusterEvidenceError` at the Gateway/Cluster Evidence Tool boundary respectively — nothing outside those two modules may catch a raw provider SDK exception (this is a Critical Rule below, not just a suggestion).

### Business Logic Errors

- **Custom Exceptions:** The hierarchy above — no separate parallel hierarchy needed.
- **User-Facing Errors:** The only "user" is the on-call engineer at the Approval CLI — errors shown there are plain-text, human-readable, no stack traces; full stack trace goes to structured logs only, correlated by `pipeline_run_id`.
- **Error Codes:** Deliberately **not** introducing a numeric error-code system (e.g. `ERR-4012`) — the template suggests one, but for this scale it would be ceremony without a consumer (no support team triaging codes, no multi-language client needing stable codes). HTTP status codes (400/401/202, per REST API Spec) are sufficient.

### Data Consistency

- **Transaction Strategy:** Each node's own persistence write commits independently as that node completes — the graph does **not** hold one long-lived DB transaction open across the whole run (which includes slow external calls to Bedrock/kubectl). `node_transitions` is the audit trail reconstructing a partial run, not a transactional atomicity guarantee across the full pipeline.
- **Compensation Logic:** Not applicable. No write/mutating external action exists anywhere in this system (NFR5) — there is nothing to compensate for, which is a direct, pleasant consequence of the no-autofix architectural constraint, not an oversight.
- **Idempotency:** Alert ingestion is idempotent by `alert_id` (FR2) — a retried webhook delivery is a no-op past the dedup check. Idempotent retry of an entire failed pipeline run is explicitly out of scope for M1 (a failed run is terminal; re-running means a new alert/new run, not an automatic retry).

---

**⚠️ Elicitation required before continuing.**

Rationale / flags:
- Skipping a numeric error-code system is a deliberate anti-ceremony call, going against the template's own example — flagging because it's a case where I think "best practice" and "right-sized for this project" diverge, and I sided with right-sized.
- 5s timeout on Kubernetes API calls is a specific number I invented to make graceful degradation actually fast in a demo — there's no stated requirement for the exact value, just that it should fail fast.
- `structlog` is a new dependency not mentioned anywhere upstream — worth confirming you're fine with it vs. stdlib `logging` + a JSON formatter (less dependency surface, more boilerplate).

Select 1-9 or just type your question/feedback:

1. Proceed to next section (Coding Standards)
2. Expand on the circuit breaker design — what "N consecutive failures" and "rolling window" should actually be
3. Challenge from a different stakeholder's perspective (e.g., an SRE asking "how do I debug a failed run at 2am from these logs alone")
4. Analyze what could go wrong if `structlog`'s correlation-ID context isn't properly propagated across async boundaries (FastAPI + LangGraph both async)
5. Identify hidden assumptions in "4xx from provider is never transient" — are there real-world cases where it is?
6. Red Team: argue for stdlib logging over structlog to minimize dependencies
7. Tree of Thoughts: 3 alternative retry/circuit-breaker library choices (write-your-own vs. tenacity vs. pybreaker), compared
8. Self-Consistency check: re-derive this section independently from NFR5/NFR7 and the Components section, and diff
9. Meta-review: critique this section as if you were Dev about to implement Story 2.1's gateway-call-failure handling AC
