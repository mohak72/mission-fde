# Database Schema

**Database choice: PostgreSQL** (not SQLite) for relational data, from Story 1.2 onward — chosen over SQLite specifically so Story 5.1's migration is a single swap (Chroma → Oracle DB 23ai, vector store only) rather than two migrations stacked (SQLite→Postgres-equivalent, then vector store). The RFC's own S13 description ("memory → Oracle DB 23ai **vector search**") only scopes the vector store for migration, so relational tables stay on Postgres through and beyond Story 5.1.

```sql
CREATE TABLE alerts (
    id                 UUID PRIMARY KEY,
    external_alert_id  TEXT NOT NULL UNIQUE,      -- the alert_id from AlertPayload; UNIQUE makes dedup atomic (see below)
    payload            JSONB NOT NULL,            -- PII-scrubbed before insert (FR10)
    received_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    signature_verified BOOLEAN NOT NULL,          -- always true for persisted rows; kept for audit
    team               TEXT,                      -- FR11 per-team filter
    dedup_group_id     UUID                       -- set by interval-merge (Story 3.2); null if standalone
);
CREATE INDEX idx_alerts_dedup_group ON alerts (dedup_group_id);
CREATE INDEX idx_alerts_received_at ON alerts (received_at);  -- supports interval-merge window queries

CREATE TABLE runbooks (
    id                TEXT PRIMARY KEY,           -- stable slug, e.g. 'pod-crashloop-oom'
    title             TEXT NOT NULL,
    content           TEXT NOT NULL,              -- markdown body; embedding lives in the vector store, keyed by this id
    failure_mode_tags TEXT[] NOT NULL DEFAULT '{}',
    team              TEXT                        -- FR11 counterpart to alerts.team
);

CREATE TABLE pipeline_runs (
    id                   UUID PRIMARY KEY,
    alert_id             UUID NOT NULL REFERENCES alerts(id),
    status               TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    node_transitions     JSONB NOT NULL DEFAULT '[]',  -- append-only log: [{node_name, entered_at, exited_at, output_summary}]
    llm_provider_config  TEXT NOT NULL                 -- 'bedrock' pre-S13, 'oci-genai' post-S13
);
CREATE INDEX idx_pipeline_runs_alert ON pipeline_runs (alert_id);

CREATE TABLE diagnosis_proposals (
    id                     UUID PRIMARY KEY,
    pipeline_run_id        UUID NOT NULL REFERENCES pipeline_runs(id),
    runbook_id             TEXT REFERENCES runbooks(id),
    cause                  TEXT NOT NULL,
    next_step_action       TEXT NOT NULL,
    runbook_citation       TEXT,
    live_evidence          JSONB,                 -- null if investigate node degraded gracefully (Story 2.3 AC4)
    grounded_in_live_state BOOLEAN NOT NULL
);
CREATE UNIQUE INDEX idx_proposals_run ON diagnosis_proposals (pipeline_run_id);  -- one proposal per run (MVP)

CREATE TABLE approval_decisions (
    id           UUID PRIMARY KEY,
    proposal_id  UUID NOT NULL REFERENCES diagnosis_proposals(id),
    actor        TEXT NOT NULL,
    decision     TEXT NOT NULL CHECK (decision IN ('approved', 'rejected')),
    decided_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX idx_decisions_proposal ON approval_decisions (proposal_id);  -- one decision per proposal

CREATE TABLE eval_runs (
    id                  UUID PRIMARY KEY,
    run_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    provider_config     TEXT NOT NULL,            -- same tag as pipeline_runs, for Story 5.1 comparison
    retrieval_hit_rate  NUMERIC(5,4) NOT NULL,     -- e.g. 0.8500
    judge_score         NUMERIC(5,4) NOT NULL
);

CREATE TABLE eval_incident_results (
    id                   UUID PRIMARY KEY,
    eval_run_id          UUID NOT NULL REFERENCES eval_runs(id),
    incident_id          TEXT NOT NULL,
    expected_runbook_id  TEXT NOT NULL REFERENCES runbooks(id),
    retrieved_runbook_id TEXT REFERENCES runbooks(id),
    hit                  BOOLEAN NOT NULL,
    judge_score          NUMERIC(5,4) NOT NULL
);
CREATE INDEX idx_incident_results_run ON eval_incident_results (eval_run_id);
```

---

**⚠️ Elicitation required before continuing.**

Rationale / flags:
- `node_transitions` and `live_evidence` as JSONB rather than normalized tables — deliberate: these are write-once, read-rarely audit/debug payloads, not something queried relationally. Normalizing them would add migration overhead for no query benefit at this scale.
- Unique constraint on `diagnosis_proposals.pipeline_run_id` and `approval_decisions.proposal_id` encodes the "one proposal per run, one decision per proposal" MVP assumption directly in the schema — if that assumption changes later (e.g., re-diagnosis retries), these constraints need to be revisited, not silently ignored.
- `eval_incident_results` as a child table (not JSONB array on `eval_runs`) — chosen because Story 5.1 explicitly needs to compare per-incident results across two `provider_config` values, which is much easier as queryable rows than as JSON blobs to diff.

Select 1-9 or just type your question/feedback:

1. Proceed to next section (Source Tree)
2. Expand on the PostgreSQL-vs-SQLite choice — what changes if you'd rather start with SQLite for pure dev-speed and migrate later
3. Challenge from a different stakeholder's perspective (e.g., Dev writing the first migration in Story 1.2 who just wants minimal schema)
4. Analyze what could go wrong with the "one proposal per run" unique constraint once a future retry/re-diagnosis feature is added
5. Identify hidden assumptions in storing `payload` as JSONB after PII scrubbing — what if scrubbing is imperfect and sensitive data still lands in the column?
6. Red Team: argue for using Chroma's own metadata store for everything, avoiding Postgres entirely for MVP
7. Tree of Thoughts: 3 alternative schema designs for the eval results, compared
8. Self-Consistency check: re-derive this schema independently from the Data Models section and diff
9. Meta-review: critique this schema as if you were Dev about to write the first Alembic/migration file
