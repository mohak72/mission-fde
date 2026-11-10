from incident_copilot.graph.nodes.retrieve import retrieve
from incident_copilot.graph.state import GraphState, PipelineContext
from incident_copilot.persistence.models import Alert, Runbook

ALERT = Alert(
    id=None,
    external_alert_id="a1",
    payload={"labels": {"alertname": "KubePodCrashLooping"}, "annotations": {}},
    received_at=None,
    signature_verified=True,
)
RUNBOOK = Runbook(
    id="pod-crashloop-oom",
    title="Pod CrashLoopBackOff",
    content="...",
    failure_mode_tags=[],
    team=None,
)


def test_retrieve_wraps_retrieve_runbook_unchanged(mocker) -> None:
    mock_retrieve_runbook = mocker.patch(
        "incident_copilot.graph.nodes.retrieve.retrieve_runbook", return_value=RUNBOOK
    )
    state = GraphState(alert=ALERT)
    session = object()
    runtime = mocker.Mock(context=PipelineContext(session=session))

    result = retrieve(state, runtime)

    assert result == {"runbook": RUNBOOK}
    mock_retrieve_runbook.assert_called_once_with(ALERT, session)


def test_retrieve_returns_none_when_no_match(mocker) -> None:
    mocker.patch("incident_copilot.graph.nodes.retrieve.retrieve_runbook", return_value=None)
    state = GraphState(alert=ALERT)
    runtime = mocker.Mock(context=PipelineContext(session=object()))

    result = retrieve(state, runtime)

    assert result == {"runbook": None}
