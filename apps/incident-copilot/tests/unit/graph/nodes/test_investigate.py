from incident_copilot.cluster.evidence import ClusterEvidence, ClusterEvidenceError
from incident_copilot.graph.nodes.investigate import investigate
from incident_copilot.graph.state import GraphState
from incident_copilot.persistence.models import Alert

ALERT = Alert(
    id=None,
    external_alert_id="a1",
    payload={"labels": {"namespace": "prod", "pod": "api-7f8"}, "annotations": {}},
    received_at=None,
    signature_verified=True,
)


def test_investigate_returns_evidence_and_grounded_true_on_success(mocker) -> None:
    evidence = ClusterEvidence(
        resource_kind="Pod",
        resource_name="api-7f8",
        namespace="prod",
        status_summary="pod api-7f8 in CrashLoopBackOff, restart count 7",
        raw={"restart_count": 7},
    )
    mocker.patch("incident_copilot.graph.nodes.investigate.get_evidence", return_value=evidence)
    state = GraphState(alert=ALERT)

    result = investigate(state)

    assert result == {"live_evidence": evidence.model_dump(), "grounded_in_live_state": True}


def test_investigate_degrades_gracefully_on_cluster_evidence_error(mocker) -> None:
    mocker.patch(
        "incident_copilot.graph.nodes.investigate.get_evidence",
        side_effect=ClusterEvidenceError("boom"),
    )
    state = GraphState(alert=ALERT)

    result = investigate(state)

    assert result == {"live_evidence": None, "grounded_in_live_state": False}


def test_investigate_degrades_gracefully_when_no_resource_identifiable(mocker) -> None:
    mocker.patch("incident_copilot.graph.nodes.investigate.get_evidence", return_value=None)
    alert = Alert(
        id=None,
        external_alert_id="a2",
        payload={"labels": {}, "annotations": {}},
        received_at=None,
        signature_verified=True,
    )
    state = GraphState(alert=alert)

    result = investigate(state)

    assert result == {"live_evidence": None, "grounded_in_live_state": False}
