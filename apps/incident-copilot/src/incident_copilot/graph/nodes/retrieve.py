"""The "retrieve" node: a thin wrapper around the existing retrieval seam.
Does not reimplement retrieval logic -- calls
`retrieval.interface.retrieve_runbook` unchanged (Story 1.3/2.1).
[Source: docs/stories/2.2.langgraph-state-machine-refactor.md#tasks-subtasks]
"""

from langgraph.runtime import Runtime

from incident_copilot.graph.state import GraphState, PipelineContext
from incident_copilot.retrieval.interface import retrieve_runbook


def retrieve(state: GraphState, runtime: Runtime[PipelineContext]) -> dict:
    runbook = retrieve_runbook(state.alert, runtime.context.session)
    return {"runbook": runbook}
