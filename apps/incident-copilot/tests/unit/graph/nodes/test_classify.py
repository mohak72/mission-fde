from incident_copilot.graph.nodes.classify import classify
from incident_copilot.graph.state import GraphState
from incident_copilot.persistence.models import Alert

ALERT = Alert(
    id=None,
    external_alert_id="a1",
    payload={"labels": {"alertname": "KubePodCrashLooping"}, "annotations": {}},
    received_at=None,
    signature_verified=True,
)


def test_classify_extracts_alertname_label() -> None:
    state = GraphState(alert=ALERT)

    result = classify(state)

    assert result == {"alert_type": "KubePodCrashLooping"}


def test_classify_defaults_to_unknown_when_alertname_missing() -> None:
    alert = Alert(
        id=None,
        external_alert_id="a2",
        payload={"labels": {}, "annotations": {}},
        received_at=None,
        signature_verified=True,
    )
    state = GraphState(alert=alert)

    result = classify(state)

    assert result == {"alert_type": "unknown"}
