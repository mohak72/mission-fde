"""The "investigate" node: calls the Cluster Evidence Tool (Story 2.3) and
degrades gracefully on any failure -- `ClusterEvidenceError` is caught here,
not inside `cluster/evidence.py`, per this story's Known Gap #3.
"""

import structlog

from incident_copilot.cluster.evidence import ClusterEvidenceError, get_evidence
from incident_copilot.graph.state import GraphState

logger = structlog.get_logger(component="graph.investigate")


def investigate(state: GraphState) -> dict:
    try:
        evidence = get_evidence(state.alert)
    except ClusterEvidenceError as exc:
        logger.warning("cluster_evidence_unavailable", reason=str(exc))
        return {"live_evidence": None, "grounded_in_live_state": False}

    if evidence is None:
        logger.warning("cluster_evidence_no_resource_identifiable")
        return {"live_evidence": None, "grounded_in_live_state": False}

    return {"live_evidence": evidence.model_dump(), "grounded_in_live_state": True}
