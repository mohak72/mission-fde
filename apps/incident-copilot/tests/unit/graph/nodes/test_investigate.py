from incident_copilot.graph.nodes.investigate import investigate
from incident_copilot.graph.state import GraphState
from incident_copilot.persistence.models import Alert

ALERT = Alert(
    id=None,
    external_alert_id="a1",
    payload={"labels": {}, "annotations": {}},
    received_at=None,
    signature_verified=True,
)


def test_investigate_stub_returns_no_evidence_not_grounded() -> None:
    state = GraphState(alert=ALERT)

    result = investigate(state)

    assert result == {"grounded_in_live_state": False}
