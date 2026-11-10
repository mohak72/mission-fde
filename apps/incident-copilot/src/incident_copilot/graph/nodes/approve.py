"""The "approve" node: a stub per AC1, replaced by Story 3.3's real
Approval CLI wiring. Returns a literal "pending" status held only in
in-memory graph state for this story -- no `ApprovalDecision` table exists
yet. [Source: docs/stories/2.2.langgraph-state-machine-refactor.md#technical-constraints]
"""

from incident_copilot.graph.state import GraphState


def approve(state: GraphState) -> dict:
    return {"approval_status": "pending"}
