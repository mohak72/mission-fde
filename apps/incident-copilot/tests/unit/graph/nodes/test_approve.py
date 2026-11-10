from incident_copilot.graph.nodes.approve import approve
from incident_copilot.graph.state import GraphState
from incident_copilot.persistence.models import Alert

ALERT = Alert(
    id=None,
    external_alert_id="a1",
    payload={"labels": {}, "annotations": {}},
    received_at=None,
    signature_verified=True,
)


def test_approve_stub_returns_pending() -> None:
    state = GraphState(alert=ALERT)

    result = approve(state)

    assert result == {"approval_status": "pending"}
