"""The "investigate" node: a placeholder per AC1, replaced by Story 2.3's
real `cluster/evidence.py` call. Returns no evidence and marks the result
as not grounded in live cluster state -- this story never imports
`kubernetes`. [Source: docs/stories/2.2.langgraph-state-machine-refactor.md#technical-constraints]
"""

from incident_copilot.graph.state import GraphState


def investigate(state: GraphState) -> dict:
    return {"grounded_in_live_state": False}
