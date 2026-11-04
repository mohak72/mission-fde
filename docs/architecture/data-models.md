# Data Models

## Alert

**Purpose:** The durable record of every alert the system has seen (Story 1.2), and the root entity everything else hangs off of.

**Key Attributes:**
- `id`: str (UUID, or a fingerprint derived from the source payload) - unique alert identity, used for dedup (FR2)
- `payload`: JSON - the raw simulated Prometheus alert body, stored after PII scrubbing (FR10)
- `received_at`: datetime - when the webhook accepted it
- `signature_verified`: bool - result of the NFR9 HMAC check; a `False` record should never exist (rejected before persistence), but the field exists for audit
- `team`: str | null - metadata used for per-team retrieval filtering (FR11)
- `dedup_group_id`: str | null - set by Story 3.2's interval-merge when this alert was merged with a prior one

**Relationships:**
- One `Alert` → one `PipelineRun` (MVP assumes no retries create a second run for the same alert)

## Runbook

**Purpose:** One entry in the 10+ document corpus (Story 1.3) describing a known failure mode; the thing retrieval is trying to match.

**Key Attributes:**
- `id`: str - stable slug (e.g. `pod-crashloop-oom`)
- `title`: str
- `content`: markdown text - the full runbook body
- `failure_mode_tags`: list[str] - used for eval labeling and retrieval scoring sanity-checks
- `team`: str | null - metadata filter counterpart to `Alert.team` (FR11)

**Relationships:**
- Embeddings for `Runbook.content` live in the vector store (Chroma/DB23ai), addressed by `Runbook.id` — the relational-looking model here is metadata; the vector itself is not a field on this model, it's an index entry keyed by this model's id.
- One `Runbook` → many `DiagnosisProposal` (cited by)

## PipelineRun

**Purpose:** The replayable log of one LangGraph execution (Story 2.2 AC4) — exists independently of whether the run succeeded, so a failed/partial run is still inspectable.

**Key Attributes:**
- `id`: str (UUID)
- `alert_id`: str - FK to `Alert`
- `status`: enum (`running`, `completed`, `failed`)
- `node_transitions`: list of `{node_name, entered_at, exited_at, output_summary}` - append-only log of every node the graph passed through
- `llm_provider_config`: str - which backend was active (`bedrock` pre-S13, `oci-genai` post-S13) — needed for Story 5.1's before/after comparison

**Relationships:**
- One `Alert` → one `PipelineRun`
- One `PipelineRun` → zero-or-one `DiagnosisProposal` (zero if the run failed before reaching the propose node)

## DiagnosisProposal

**Purpose:** The actual business output — cause, action, and the evidence backing it (Stories 2.1/2.3) — separated from `PipelineRun` because this is what Dev/QA/the demo actually look at, with its own lifecycle (proposed → approved/rejected).

**Key Attributes:**
- `id`: str (UUID)
- `pipeline_run_id`: str - FK to `PipelineRun`
- `runbook_id`: str - FK to `Runbook` (which one was cited)
- `cause`: text - probable cause
- `next_step_action`: text - proposed action (never auto-executed — no executor exists, per NFR5)
- `runbook_citation`: str - specific section/line referenced (FR4/FR5)
- `live_evidence`: JSON | null - structured kubectl evidence (e.g., pod name, restart count); `null` if Story 2.3's investigate node degraded gracefully
- `grounded_in_live_state`: bool - `False` when `live_evidence` is `null`, surfaced to the approver so they know what they're approving

**Relationships:**
- One `PipelineRun` → one `DiagnosisProposal`
- One `DiagnosisProposal` → zero-or-one `ApprovalDecision`

## ApprovalDecision

**Purpose:** The literal trust mechanic (Story 3.3) — immutable record of who approved/rejected what, and when.

**Key Attributes:**
- `id`: str (UUID)
- `proposal_id`: str - FK to `DiagnosisProposal`
- `actor`: str - who approved/rejected (CLI user identity for MVP)
- `decision`: enum (`approved`, `rejected`)
- `decided_at`: datetime

**Relationships:**
- One `DiagnosisProposal` → one `ApprovalDecision` (once decided; absent while pending)

## EvalRun

**Purpose:** One execution of the Story 3.4 evaluation harness — the quotable numbers this whole product is judged on, and the thing Story 4.2's CI gate reads.

**Key Attributes:**
- `id`: str (UUID)
- `run_at`: datetime
- `provider_config`: str - same tag as `PipelineRun.llm_provider_config`, enabling Story 5.1's before/after comparison
- `retrieval_hit_rate`: float - % of the 20 incidents where the correct runbook was retrieved
- `judge_score`: float - aggregate LLM-judge usefulness score
- `per_incident_results`: list of `{incident_id, expected_runbook_id, retrieved_runbook_id, hit, judge_score}` - the granular evidence behind the two headline numbers

**Relationships:**
- Independent of the live `Alert`/`PipelineRun` tables — runs against a separate, fixed synthetic incident set, not production data (Story 3.4 AC1)

---

**⚠️ Elicitation required before continuing.**

Rationale / flags:
- I split `PipelineRun` (replay log) from `DiagnosisProposal` (business output) rather than merging them — they have genuinely different lifecycles (a run can fail with no proposal; a proposal outlives the run that produced it once approved/rejected). Worth confirming you don't want this simplified to one table for MVP.
- These are conceptual models, not yet a database schema (that's its own template section coming up) — I haven't decided SQL vs. something simpler yet; that decision happens next in Database Schema, informed by these models.
- `EvalRun` is deliberately NOT related to `Alert`/`PipelineRun` — it runs against a separate fixed synthetic set (PRD Story 3.4 AC1), so conflating it with live data would be a modeling mistake, not a simplification.

Select 1-9 or just type your question/feedback:

1. Proceed to next section (Components)
2. Expand on why PipelineRun and DiagnosisProposal are separate - walk through the "run fails before proposing" case concretely
3. Challenge from a different stakeholder's perspective (e.g., Dev who has to write 6 models' worth of boilerplate for an MVP)
4. Analyze what could go wrong if `live_evidence` JSON has no schema validation and downstream code assumes fields exist
5. Identify hidden assumptions in treating Runbook metadata (team tag) separately from its vector embedding
6. Red Team: argue for merging PipelineRun + DiagnosisProposal + ApprovalDecision into one wide table for MVP simplicity
7. Tree of Thoughts: 3 alternative data model groupings, compared
8. Self-Consistency check: re-derive the models independently from the PRD's FRs and diff
9. Meta-review: critique these models as if you were Dev about to write the Story 1.2/1.3 persistence code
