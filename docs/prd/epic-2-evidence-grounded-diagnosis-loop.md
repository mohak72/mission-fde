# Epic 2 Evidence-Grounded Diagnosis Loop

Epic Goal: Turn "runbook found" into an actual diagnosis — first with a simple LLM call, then rebuilt as an inspectable LangGraph state machine, then grounded in live cluster evidence instead of just runbook text.

## Story 2.1 LLM Triage Summary

As an on-call engineer,
I want the system to produce a cause + next-steps summary from the alert and its matched runbook,
so that I get an initial diagnosis without manually reading the runbook myself.

### Acceptance Criteria

1: Given an alert + its retrieved runbook, the system calls the LLM gateway (never the model provider directly, per NFR1) and returns a structured diagnosis: probable cause + next-step action.
2: The diagnosis explicitly references which runbook section it drew from.
3: If retrieval returns no runbook above a confidence threshold, the system returns an explicit "no matching runbook" result rather than a hallucinated diagnosis.
4: Unit tests cover: happy path, low-confidence-retrieval fallback, gateway-call-failure handling (retry/error surfaced, not swallowed).

## Story 2.2 LangGraph State Machine Refactor

As a developer,
I want the diagnosis pipeline rebuilt as an explicit LangGraph state machine (classify → retrieve → propose → human-approval),
so that each stage is independently testable and the pipeline's state is inspectable rather than hidden inside one function.

### Acceptance Criteria

1: Pipeline implemented as a LangGraph graph with distinct nodes: classify alert type, retrieve runbook, investigate (placeholder until Story 2.3), propose diagnosis+action, human-approval (stub returning "pending" until Epic 3).
2: Each node is unit-testable in isolation with mocked inputs/outputs.
3: Running an alert through the graph end-to-end produces the same diagnosis output as the pre-refactor Story 2.1 loop — verified by a regression fixture comparing old vs. new output on the same test alerts.
4: Graph state/transitions are logged so a run can be replayed/debugged from the log alone.

## Story 2.3 Read-Only kubectl Evidence Grounding

As an on-call engineer,
I want the diagnosis to cite live cluster state, not just the runbook text,
so that I can trust the diagnosis reflects what's actually happening right now, not a generic guess.

### Acceptance Criteria

1: The investigate node calls read-only `kubectl get`/`describe` against the target cluster (local `kind` for dev/test) for resources relevant to the alert.
2: The tool is strictly read-only — no code path from this node to any write/mutating kubectl verb (NFR5).
3: The final proposal cites specific live evidence (e.g., "pod X in CrashLoopBackOff, restart count N") alongside the runbook citation.
4: If the cluster/tool call fails or times out, the system still returns a diagnosis, clearly flagged as "not grounded in live state," rather than failing the whole pipeline.
