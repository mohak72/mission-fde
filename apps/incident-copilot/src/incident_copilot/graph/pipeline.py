"""Wires the diagnosis pipeline as an explicit LangGraph state machine:
classify -> retrieve -> investigate -> propose -> approve.
[Source: architecture/components.md#diagnosis-graph]
"""

from datetime import UTC, datetime

import structlog
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from platform_core.config import settings as platform_settings
from pydantic import BaseModel
from sqlalchemy.orm import Session

from incident_copilot.graph.nodes.approve import approve
from incident_copilot.graph.nodes.classify import classify
from incident_copilot.graph.nodes.investigate import investigate
from incident_copilot.graph.nodes.propose import propose_diagnosis
from incident_copilot.graph.nodes.retrieve import retrieve
from incident_copilot.graph.state import GraphState, PipelineContext
from incident_copilot.persistence.models import Alert, PipelineRun
from incident_copilot.persistence.repositories import (
    DiagnosisProposalRepository,
    PipelineRunRepository,
)

logger = structlog.get_logger(component="graph.pipeline")


def _propose(state: GraphState, runtime: Runtime[PipelineContext]) -> dict:
    """Adapts Story 2.1's `propose_diagnosis(alert, session) -> DiagnosisResult`
    into a graph node -- reuses it unchanged, only plumbs `GraphState`/
    `Runtime` in and out, per this story's Task 2 instruction. Lives here
    rather than in `propose.py` so that file stays byte-for-byte what
    Story 2.1 shipped. [Source: docs/stories/2.2.langgraph-state-machine-refactor.md#tasks-subtasks]
    """
    diagnosis = propose_diagnosis(state.alert, runtime.context.session)
    return {"diagnosis": diagnosis}


def _build_graph():
    graph = StateGraph(GraphState, context_schema=PipelineContext)
    graph.add_node("classify", classify)
    graph.add_node("retrieve", retrieve)
    graph.add_node("investigate", investigate)
    graph.add_node("propose", _propose)
    graph.add_node("approve", approve)
    graph.add_edge(START, "classify")
    graph.add_edge("classify", "retrieve")
    graph.add_edge("retrieve", "investigate")
    graph.add_edge("investigate", "propose")
    graph.add_edge("propose", "approve")
    graph.add_edge("approve", END)
    return graph.compile()


_COMPILED_GRAPH = _build_graph()


def _summarize_output(output: dict) -> str:
    """A short, loggable description of one node's partial state update --
    never the raw alert payload (Coding Standards Critical Rules); none of
    this story's nodes return `alert` in their output, so this never sees it.
    """
    parts: list[str] = []
    for key, value in output.items():
        if isinstance(value, BaseModel):
            parts.append(f"{key}={value.model_dump()!r}")
        elif hasattr(value, "id"):  # ORM model instances, e.g. Runbook
            parts.append(f"{key}.id={value.id!r}")
        else:
            parts.append(f"{key}={value!r}")
    return ", ".join(parts)


def run_pipeline(alert: Alert, session: Session) -> PipelineRun:
    """The single entry point both the webhook path and the future MCP tool
    call into. Deviates from `components.md`'s documented
    `run_pipeline(alert: Alert) -> PipelineRun` signature by keeping
    `session` explicit, consistent with every other seam in this codebase
    (`retrieve_runbook(alert, session)`, `propose_diagnosis(alert, session)`).
    [Source: architecture/components.md#diagnosis-graph]
    """
    run_repo = PipelineRunRepository(session)
    run = run_repo.create(alert.id, platform_settings.bedrock_model_id)

    structlog.contextvars.bind_contextvars(pipeline_run_id=str(run.id))
    try:
        state_values: dict = {"alert": alert}
        entered_at = datetime.now(UTC)
        for chunk in _COMPILED_GRAPH.stream(
            GraphState(alert=alert),
            context=PipelineContext(session=session),
            stream_mode="updates",
        ):
            ((node_name, output),) = chunk.items()
            exited_at = datetime.now(UTC)
            state_values.update(output)
            run_repo.append_transition(
                run.id, node_name, entered_at, exited_at, _summarize_output(output)
            )
            logger.info("node_transition", node_name=node_name)
            entered_at = exited_at

        final_state = GraphState(**state_values)
        diagnosis = final_state.diagnosis
        if diagnosis is not None and diagnosis.matched:
            DiagnosisProposalRepository(session).create(
                pipeline_run_id=run.id,
                runbook_id=final_state.runbook.id if final_state.runbook else None,
                cause=diagnosis.cause,
                next_step_action=diagnosis.next_step_action,
                runbook_citation=diagnosis.runbook_citation,
                live_evidence=None,
                grounded_in_live_state=final_state.grounded_in_live_state,
            )

        run_repo.mark_completed(run.id)
        return run
    except Exception:
        # A failed run is a terminal, inspectable state (PipelineRun.status),
        # never a silent swallow -- but it IS the signal; this never
        # re-raises. [Source: architecture/error-handling-strategy.md#error-propagation]
        run_repo.mark_failed(run.id)
        logger.exception("pipeline_run_failed")
        return run
    finally:
        structlog.contextvars.unbind_contextvars("pipeline_run_id")
