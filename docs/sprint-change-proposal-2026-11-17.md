# Sprint Change Proposal — 2026-11-17

**Status: PROPOSED — nothing in this document is approved or applied.**
Prepared by Sarah (PO) using `correct-course` in batch mode, with John (PM) reasoning on scope for Gaps 1–2 and Winston (Architect) on technical direction for Gaps 3–4. No PRD, architecture, story or code file has been changed.

## 1. Trigger

Batch-drafting Epics 3 and 4 (commit `2f72f60`) surfaced four gaps between the PRD, the architecture docs and the code on `main` (`0652292`). Verifying them turned up a fifth and some smaller drift, listed in section 7.

The most important finding is how Gaps 1 and 2 interact:

- FR10 says PII is scrubbed "before [payloads] are indexed or sent to any model". Today nothing scrubs anything. The raw payload is persisted, used as the retrieval query, and every label and annotation is written into the LLM prompt.
- The only reason no unscrubbed alert reaches Bedrock from production today is that nothing calls `run_pipeline` (Gap 1).
- So closing Gap 1 without first closing Gap 2 turns a dormant FR10 violation into a live one. **The scrubber has to land before, or together with, the hand-off.**

## 2. Summary of recommendations

| # | Gap | Recommendation | Owner |
|---|---|---|---|
| 1 | Nothing calls `run_pipeline` | New Story 2.5 "Webhook-to-Pipeline Hand-off"; take the wiring out of the 3.2 draft | John (PM) |
| 2 | No PII scrubber (FR10) | New Story 2.4 "PII Scrubbing at Ingestion", built before 2.5 | John (PM) |
| 3 | Circuit breaker has no story | Descope from M1 in the architecture doc; record as deferred | Winston (Architect) |
| 4 | Kubernetes timeout 5s (doc) vs 10s (code) | Change the code to 5s and make it a setting; the doc stays | Winston (Architect) |
| 5 | FR11 per-team retrieval filter has no story (new finding) | Decide: small Story 2.6 before the eval baseline, or mark FR11 deferred | John (PM) |

Numbering the new stories 2.4–2.6 keeps the seven existing drafts' numbers unchanged and puts the new work first in `create-next-story`'s sequential order. It does reopen Epic 2, which is accurate: Epic 2's diagnosis loop cannot be reached from the webhook yet.

---

## 3. Gap 1 — Nothing in production code calls `run_pipeline`

### Evidence
- `apps/incident-copilot/src/incident_copilot/api/webhook.py:45-49` — the route calls `ingest_alert` and returns; no hand-off.
- `apps/incident-copilot/src/incident_copilot/ingestion/__init__.py:12-14` — docstring: "no second pipeline run is triggered either way, since the Diagnosis Graph does not exist yet (Story 2.2)". The graph now exists; the comment is stale.
- `grep run_pipeline` over `src/`: the only hit is the definition in `graph/pipeline.py`.
- `docs/architecture/core-workflows.md:24` draws `ING->>GRAPH: run_pipeline(alert)`; `docs/architecture/components.md:5` says ingestion "hands off to the Diagnosis Graph".
- No acceptance criterion in Epics 1–3 asks for the hand-off. Story 1.2 AC3 ("does not ... trigger a second pipeline run") was accepted while its second half was untestable.
- `docs/stories/3.2.rate-limiting-alert-dedup.md:55` and `:115` — the draft wires it via FastAPI `BackgroundTasks` and flags it as needing confirmation.

### Impact
- FR1→FR5 is the product's primary flow and it is not connected. Story 3.2 AC2, Story 3.3's demo, Story 4.3 AC5 and Story 5.2 AC1 ("reusing the same pipeline as the webhook path") all assume it.
- No architecture change: the docs already describe the intended behaviour.

### Options considered (John, PM)
1. **Keep it inside Story 3.2 as drafted.** Least ceremony. But 3.2 already carries two unrelated concerns (gateway limiter, interval-merge), and the product's main data flow would ship as a sub-task with no acceptance criterion of its own.
2. **A dedicated small story before Epic 3 (recommended).** Own ACs, own QA gate, and it can be sequenced explicitly after the scrubber.
3. **Defer to Story 5.2.** Rejected: 3.2, 3.3 and 4.3 need it first.

### Recommendation (John, PM)
Add **Story 2.5** and remove the wiring from the 3.2 draft. 3.2 then only extends an existing hand-off so that a merged alert does not start a run.

### Proposed edit — `docs/prd/epic-2-evidence-grounded-diagnosis-loop.md`, append

```markdown
## Story 2.5 Webhook-to-Pipeline Hand-off

As an on-call engineer,
I want an accepted alert to start a diagnosis run automatically,
so that a diagnosis exists without anyone invoking the pipeline by hand.

### Acceptance Criteria

1: A newly ingested (non-duplicate) alert starts exactly one pipeline run. The webhook still returns 202 without waiting for the run to finish.
2: A duplicate delivery of the same alert ID starts no pipeline run (completes FR2 and the second half of Story 1.2 AC3).
3: The decision "should this alert start a run" is made in the Ingestion Module, not in the route, so the MCP entry point (Story 5.2) reuses it.
4: A pipeline failure does not change the webhook response and does not crash the service; the run is left in an inspectable `failed` state.
5: An integration test posts a signed alert and asserts a `PipelineRun` (and, for a matching runbook, a `DiagnosisProposal`) is persisted for it, with the LLM gateway mocked.
```

Mechanism is a story-level decision, not an AC. Bob's draft recommended FastAPI `BackgroundTasks` with a fresh DB session inside the task. That runs in-process, so a run in flight is lost if the service restarts. Accepting that for M1 is decision 2 below.

### Proposed edits — story drafts (Bob applies after approval)
- `docs/stories/3.2.rate-limiting-alert-dedup.md`
  - Line 24 ("Nothing in production code calls `run_pipeline` today…"): replace with a note that Story 2.5 built the hand-off and this story only makes it respect the merge decision.
  - Line 55 ("Wire the hand-off per Known Gap #1's recommended default…"): replace with "Extend Story 2.5's hand-off so it is skipped when `should_run_pipeline` is false."
  - Line 115 (Known Gap #1): delete; resolved by Story 2.5.
  - Batch-Draft Assumptions: add "Story 2.5's hand-off exists and its scheduling mechanism is unchanged."
- `docs/stories/3.3.human-approval-gate-cli.md`, `4.3.containerization-gitops-deploy.md`: in Batch-Draft Assumptions, change the "webhook is wired by then" assumption to reference Story 2.5.
- `apps/incident-copilot/src/incident_copilot/ingestion/__init__.py:12-14`: the stale docstring is corrected as part of Story 2.5 (code, not part of this proposal's edits).

---

## 4. Gap 2 — No story builds the PII scrubber (FR10)

### Evidence
- `docs/prd/requirements.md:14` — FR10. No epic file references FR10 except Story 4.1 AC3 (`epic-4…md:15`), which is about traces.
- `ingestion/` contains only `__init__.py`, `auth.py`, `schemas.py`; `pii.py` (`docs/architecture/source-tree.md:23`) does not exist.
- The docs state the scrubber as fact: `data-models.md:9` ("stored after PII scrubbing"), `database-schema.md:9` ("PII-scrubbed before insert"), `security.md:31`, `components.md:5`, `core-workflows.md:22`.
- What happens to a raw payload today:
  - **Persisted raw:** `ingestion/__init__.py:22` → `alerts.payload`.
  - **Sent to the model raw:** `graph/nodes/propose.py:46-48` joins every label and annotation into the prompt.
  - **Used as the retrieval query raw:** `retrieval/interface.py:49-51`. The embedding is computed locally by Chroma, so this does not leave the process today; it would after Story 5.1 if OCI computes embeddings.
  - **Logged:** no. All six `logger.*` call sites log metadata only.
- Not reachable from production until Gap 1 is closed. Tests and any manual `run_pipeline` call already exercise the raw path.

### Impact
- Story 2.5 must not ship before this. Story 4.1 AC3 and the "scrub first" coding standard (`coding-standards.md:23`) depend on it.
- Existing `alerts` rows hold only simulated test data, so no backfill is proposed.
- A deterministic scrubber keeps Story 3.1's cache keys and Story 3.2's dedup fingerprint stable.

### Options considered (John, PM)
1. **New story before the hand-off (recommended).**
2. **Fold into Story 2.5.** One story, but it mixes a security control with flow wiring and makes the QA gate harder to read.
3. **Fold into Story 4.1.** Rejected: too late; 2.5 would already be sending raw payloads to the model.
4. **Descope FR10 for M1.** Possible, since payloads are simulated, but five architecture docs would then be wrong and 4.1 AC3 would be untestable as written.

### Recommendation (John, PM)
Add **Story 2.4**, built first.

### Proposed edit — `docs/prd/epic-2-evidence-grounded-diagnosis-loop.md`, append (before Story 2.5)

```markdown
## Story 2.4 PII Scrubbing at Ingestion

As a platform operator,
I want PII and credential-shaped strings removed from an alert before it is stored or used,
so that nothing downstream — retrieval, the model provider, logs or traces — ever sees them (FR10).

### Acceptance Criteria

1: A rule-based scrubber replaces email addresses, phone numbers and credential-shaped strings (bearer tokens, cloud access keys) in alert label and annotation values with a typed placeholder (e.g. `[REDACTED:email]`). Keys are never altered.
2: Scrubbing happens inside the Ingestion Module before the alert is persisted, so the stored payload is the scrubbed one and both entry points (webhook now, MCP in Story 5.2) get it without duplicating logic.
3: Scrubbing is deterministic and leaves the alert ID and the labels used to identify resources (`alertname`, `namespace`, `pod`, `deployment`, `team`) intact unless a value itself matches a pattern.
4: A test ingests an alert containing each PII type and asserts none of the raw values appear in the stored payload, the retrieval query text, the LLM prompt, or any log line emitted during the run.
5: Unit tests cover each pattern and assert ordinary Kubernetes names, image tags and runbook-style text are not falsely redacted.
```

Whether IP addresses count as PII is decision 3. They are personal data under some regimes but are also useful diagnostic evidence in an alert; the draft AC leaves them unscrubbed.

### Proposed edits — other files
- `docs/prd/epic-list.md:4` — after "…instead of guessing." add: " Also scrubs PII at ingestion (FR10) and connects the webhook to the pipeline."
- `docs/stories/3.2.rate-limiting-alert-dedup.md:122` (Known Gap #8): delete; resolved by Story 2.4.
- `docs/stories/4.1.observability-tracing-cost-per-incident.md`: in Batch-Draft Assumptions add "Story 2.4's scrubber runs at ingestion, so prompt text reaching the gateway is already scrubbed; this story's AC3 test covers secrets (kubeconfig, API keys), which the scrubber does not see."
- `docs/stories/3.4.evaluation-harness.md`: add an assumption that eval alerts are created through `ingest_alert` (so they are scrubbed like real ones), or state explicitly that they bypass it.
- Architecture docs: no change; they become true.

---

## 5. Gap 3 — Circuit breaker specified, never scheduled

### Evidence
- `docs/architecture/error-handling-strategy.md:25` specifies a per-provider breaker ("N consecutive failures within a rolling window", N undefined).
- No PRD requirement or AC mentions it. NFR1 asks only for rate limiting and caching.
- `platform/src/platform_core/gateway/gateway.py:4-6` — "deliberately deferred … until Story 3.2's token-bucket limiter is built".
- `docs/stories/3.2.rate-limiting-alert-dedup.md:117` leaves it out and proposes correcting the docstring.
- `docs/architecture/checklist-results-report.md:18, 21, 34, 37` cite the breaker as an existing mitigation.

### Options considered (Winston, Architect)
1. **Build it in Story 3.2.** Third concern in one story, and nothing in the PRD asks for it.
2. **New story.** Proper, but the benefit at M1 scale is small: one provider, no fallback provider to fail over to, retries already capped at 3 attempts with a 30s timeout, and after Story 3.2 the limiter itself bounds how much budget a failing provider can burn.
3. **Descope from M1 in the architecture doc (recommended).** Record it as deferred with the condition that would bring it back.

### Recommendation (Winston, Architect)
Option 3. Revisit when a second provider exists (Story 5.1) or when alert volume makes fail-fast worth having.

### Proposed edit — `docs/architecture/error-handling-strategy.md:25`

Before:
> - **Circuit Breaker:** The Gateway trips per-provider after N consecutive failures within a rolling window and fails fast rather than queuing more calls behind a known-bad provider — this protects the rate-limit budget (NFR1) from being burned on calls that will fail anyway.

After:
> - **Circuit Breaker:** Deferred — not built in M1. No PRD requirement asks for one, and with a single provider, retries capped at 3 attempts and the Story 3.2 rate limiter bounding spend, the retry policy and limiter are the only protections. Revisit when a second provider exists (Story 5.1) or if sustained provider outages are observed.

### Proposed edits — other files
- `docs/architecture/checklist-results-report.md:21, 34, 37`: replace "(circuit breaker)" / "circuit-breaker design" with "retry cap and timeout"; line 18: drop "circuit breakers" from the list of concrete items.
- `docs/stories/3.2.rate-limiting-alert-dedup.md:40` and `:117`: change the instructed docstring wording to "the circuit breaker is deferred beyond M1 — see error-handling-strategy.md".
- `docs/stories/4.1.observability-tracing-cost-per-incident.md:25`: delete "and possibly the circuit breaker Story 2.1 deferred".

---

## 6. Gap 4 — Kubernetes timeout: 5s in the doc, 10s in the code

### Evidence
- `docs/architecture/error-handling-strategy.md:26` — "Kubernetes API calls: 5s — deliberately short, because Story 2.3 AC4's graceful degradation depends on failing fast".
- `apps/incident-copilot/src/incident_copilot/cluster/evidence.py:26` — `_REQUEST_TIMEOUT_SECONDS = 10`, used at lines 89, 94, 125.
- `docs/stories/2.3.read-only-kubectl-evidence-grounding.md:129` (Known Gap #4) says "No timeout value is specified for kubectl calls". That was a drafting error: the value was specified, in a doc the draft did not check for it. The 10s was chosen on a false premise, not as a considered override.

### Options considered (Winston, Architect)
1. **Change the code to 5s (recommended).** The doc gives a reason; the code's value has none. The pod path makes two sequential calls, so worst-case delay before degradation drops from about 20s to about 10s. Whether the Kubernetes client's own retries add to this was not verified and should be checked in the fix.
2. **Change the doc to 10s.** No code change, but it keeps a number nobody chose deliberately.
3. **Leave both.** Rejected.

### Recommendation (Winston, Architect)
Option 1, and move the value into `config.py` as a setting (default 5) so it is not a module constant. This is a small chore: one branch, one PR, normal QA. It is not blocking Epic 3.

### Proposed edits
- `docs/architecture/error-handling-strategy.md:26`: no change.
- Code (via a small chore PR, not this proposal): `cluster/evidence.py:26` reads the timeout from settings; `config.py` gains `kubernetes_request_timeout_seconds: int = 5`; tests updated if any assert the literal 10.
- `docs/stories/2.3…md` is a completed story and is not edited; this proposal is the record of the correction.

---

## 7. Other uncovered requirements and drift found during verification

1. **FR11 per-team retrieval filter — no story covers it (Gap 5).**
   - `requirements.md:15`. `alerts.team` and `runbooks.team` exist, but `retrieval/chroma_backend.py:65` queries with no metadata filter and `retrieve_runbook` (`retrieval/interface.py:54-79`) never reads `alert.team`.
   - Flagged before and never scheduled: `architecture/checklist-results-report.md:15` (SHOULD-FIX), Story 1.3 Known Gap #3.
   - Tension with NFR6, which scopes M1 to single-tenant.
   - John's (PM) view: either build it as a small **Story 2.6** (metadata filter behind the retrieval interface, plus tests that team A's alert cannot retrieve team B's runbook), or mark FR11 "deferred beyond M1" in `requirements.md`. If it is going to be built at all, build it before Story 3.4, because adding a filter later changes retrieval results and invalidates the eval baseline Story 4.2 commits. It also has to exist before Story 5.1 for the NFR8 swap to prove anything about filtering. This is decision 5.
2. **NFR7 covers logs as well as traces, but only traces have a test (Story 4.1 AC3).** Story 2.4 AC4 above adds a log assertion for PII. A matching assertion for secrets in logs could be added to Story 4.1; not drafted here.
3. **Exception hierarchy.** `error-handling-strategy.md:6` describes a shared `IncidentCopilotError` base with five subclasses. The code has per-module exceptions (`GatewayError`, `ClusterEvidenceError`) and no base. Winston's (Architect) view: update the doc to describe what was built; not urgent.
4. **NFR4 says the eval runs "on every change".** Story 4.2's draft recommends a two-tier gate instead. If that is chosen, `requirements.md` NFR4 needs rewording. Already flagged in 4.2; listed here so it is not lost.
5. **Minor doc drift:** `error-handling-strategy.md:11` says `structlog` 24.x; `pyproject.toml:14` pins `>=26.0,<27`.

Everything else in `requirements.md` maps to a merged or drafted story: FR1–FR9 and NFR1–NFR3, NFR5, NFR8, NFR9.

## 8. Change-checklist record

- **1 Trigger and context:** addressed (sections 1, 3–7). Triggering stories: 3.2, 4.1, 2.3 drafts.
- **2 Epic impact:** Epic 2 reopened with two or three small stories. Epics 3 and 4 keep their stories and numbering; four drafts need the edits listed above. Epics 5 and 6 unaffected, except that 5.1 and 5.2 benefit from 2.4–2.6 existing.
- **3 Artifact impact:** PRD (`epic-2`, `epic-list`, possibly `requirements.md` for FR11/NFR4); architecture (`error-handling-strategy`, `checklist-results-report`); story drafts 3.2, 3.3, 3.4, 4.1, 4.3. No frontend spec.
- **4 Path forward:** Option 1, direct adjustment. No rollback of merged work. No change to MVP goals; the only possible scope reduction is FR11 (decision 5) and the circuit breaker (decision 4).
- **5–6 Proposal and handoff:** this document. User approval not yet obtained.

## 9. Action plan if approved

1. Sarah (PO) applies the PRD and architecture edits in sections 3–6.
2. Bob (SM) drafts Story 2.4, then 2.5 (and 2.6 if chosen) from the new epic text, and applies the edits to the 3.2, 3.3, 3.4, 4.1 and 4.3 drafts.
3. James (Dev) and Quinn (QA) run 2.4 → 2.5 (→ 2.6) through the usual branch, PR, review cycle. The timeout chore can go any time.
4. Epic 3 starts at Story 3.1 after 2.5 merges. 3.1 itself does not depend on 2.4/2.5 and could run in parallel if wanted.

## 10. Decisions needed from you

1. **Hand-off as its own Story 2.5**, or keep it inside Story 3.2 as currently drafted?
2. **Hand-off mechanism:** accept in-process `BackgroundTasks` for M1, knowing an in-flight run is lost on restart?
3. **PII scope for Story 2.4:** emails, phone numbers and credential-shaped strings as drafted — and should IP addresses be scrubbed too?
4. **Circuit breaker:** descope from M1 as recommended, or schedule a story?
5. **FR11 per-team filter:** build as Story 2.6 before the eval, or mark deferred beyond M1?
6. **Kubernetes timeout:** change the code to 5s (recommended) or change the doc to 10s?
7. **Numbering:** new stories as 2.4–2.6 (recommended, reopens Epic 2), or a different placement?
