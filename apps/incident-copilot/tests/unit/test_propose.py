import pytest
from platform_core.gateway.gateway import GatewayError

from incident_copilot.graph.nodes.propose import propose_diagnosis
from incident_copilot.persistence.models import Alert, Runbook

ALERT = Alert(
    id=None,
    external_alert_id="a1",
    payload={
        "labels": {"alertname": "KubePodCrashLooping"},
        "annotations": {"summary": "Pod checkout-7f9c is OOMKilled"},
    },
    received_at=None,
    signature_verified=True,
)
RUNBOOK = Runbook(
    id="pod-crashloop-oom",
    title="Pod CrashLoopBackOff: Out of Memory (OOMKilled)",
    content="## Symptoms\nOOMKilled.\n## Resolution\nRaise the memory limit.",
    failure_mode_tags=["oom"],
    team=None,
)


def test_propose_diagnosis_happy_path(mocker) -> None:
    mocker.patch(
        "incident_copilot.graph.nodes.propose.retrieve_runbook", return_value=RUNBOOK
    )
    mock_complete = mocker.patch("incident_copilot.graph.nodes.propose.complete")
    mock_complete.return_value.content = (
        "Cause: Container exceeded its memory limit\n"
        "Action: Raise resources.limits.memory\n"
        "Citation: Resolution"
    )

    result = propose_diagnosis(ALERT, object())

    assert result.matched is True
    assert result.cause == "Container exceeded its memory limit"
    assert result.next_step_action == "Raise resources.limits.memory"
    assert result.runbook_citation == "Resolution"
    mock_complete.assert_called_once()


def test_propose_diagnosis_returns_no_match_without_calling_gateway(mocker) -> None:
    mocker.patch("incident_copilot.graph.nodes.propose.retrieve_runbook", return_value=None)
    mock_complete = mocker.patch("incident_copilot.graph.nodes.propose.complete")

    result = propose_diagnosis(ALERT, object())

    assert result.matched is False
    assert result.cause is None
    assert result.next_step_action is None
    assert result.runbook_citation is None
    mock_complete.assert_not_called()


def test_propose_diagnosis_surfaces_gateway_error(mocker) -> None:
    mocker.patch(
        "incident_copilot.graph.nodes.propose.retrieve_runbook", return_value=RUNBOOK
    )
    mocker.patch(
        "incident_copilot.graph.nodes.propose.complete", side_effect=GatewayError("boom")
    )

    with pytest.raises(GatewayError):
        propose_diagnosis(ALERT, object())


def test_propose_diagnosis_raises_on_malformed_llm_response(mocker) -> None:
    """REL-002: a non-conforming LLM response (missing one of the required
    Cause/Action/Citation lines) must raise, never silently return
    matched=True with empty fields -- that would violate AC2 undetectably."""
    mocker.patch(
        "incident_copilot.graph.nodes.propose.retrieve_runbook", return_value=RUNBOOK
    )
    mock_complete = mocker.patch("incident_copilot.graph.nodes.propose.complete")
    mock_complete.return_value.content = (
        "Cause: Container exceeded its memory limit\nAction: Raise resources.limits.memory"
    )

    with pytest.raises(GatewayError):
        propose_diagnosis(ALERT, object())
