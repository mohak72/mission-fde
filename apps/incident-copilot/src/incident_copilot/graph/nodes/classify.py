"""The "classify" node: extracts a normalized `alert_type` from the alert
payload. No PRD/architecture doc defines a taxonomy or an ML/rule-based
classifier for this -- per Known Gap #1 in this story, the chosen scope is
the simplest one that satisfies AC1 (a distinct, inspectable node exists):
read the existing `alertname` label straight through. No new ML/LLM call,
consistent with this project's recurring "right-sized, not novel" pattern
(e.g. regex PII scrubbing over an ML service).
[Source: docs/stories/2.2.langgraph-state-machine-refactor.md#known-gaps-in-architecture-docs]
"""

import structlog

from incident_copilot.graph.state import GraphState

logger = structlog.get_logger(component="graph.classify")


def classify(state: GraphState) -> dict:
    labels: dict[str, str] = state.alert.payload.get("labels", {})
    alert_type = labels.get("alertname", "unknown")
    logger.info("alert_classified", alert_type=alert_type)
    return {"alert_type": alert_type}
