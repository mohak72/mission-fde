"""AC2/AC4: the graph itself, with every node mocked -- asserts node order
and that `node_transitions` gets populated, one entry per node.
"""

import uuid

from incident_copilot.graph import pipeline as pipeline_module
from incident_copilot.graph.nodes.propose import DiagnosisResult
from incident_copilot.persistence.models import Alert

ALERT = Alert(
    id=uuid.uuid4(),
    external_alert_id="a1",
    payload={"labels": {}, "annotations": {}},
    received_at=None,
    signature_verified=True,
)


def test_run_pipeline_executes_nodes_in_order_and_records_transitions(mocker) -> None:
    call_order: list[str] = []

    def classify_mock(state):
        call_order.append("classify")
        return {"alert_type": "X"}

    def retrieve_mock(state, runtime):
        call_order.append("retrieve")
        return {"runbook": None}

    def investigate_mock(state):
        call_order.append("investigate")
        return {"grounded_in_live_state": False}

    def propose_diagnosis_mock(alert, session):
        call_order.append("propose")
        return DiagnosisResult(matched=False)

    def approve_mock(state):
        call_order.append("approve")
        return {"approval_status": "pending"}

    mocker.patch.object(pipeline_module, "classify", classify_mock)
    mocker.patch.object(pipeline_module, "retrieve", retrieve_mock)
    mocker.patch.object(pipeline_module, "investigate", investigate_mock)
    mocker.patch.object(pipeline_module, "propose_diagnosis", propose_diagnosis_mock)
    mocker.patch.object(pipeline_module, "approve", approve_mock)
    # add_node() captured direct references at graph-build time, so the
    # above patches only take effect against a graph rebuilt after them.
    mocker.patch.object(pipeline_module, "_COMPILED_GRAPH", pipeline_module._build_graph())

    run = mocker.Mock(id=uuid.uuid4())
    transitions: list[str] = []
    mock_run_repo = mocker.Mock()
    mock_run_repo.create.return_value = run
    mock_run_repo.append_transition.side_effect = (
        lambda run_id, node_name, entered_at, exited_at, summary: transitions.append(node_name)
    )
    mocker.patch.object(pipeline_module, "PipelineRunRepository", return_value=mock_run_repo)
    mocker.patch.object(pipeline_module, "DiagnosisProposalRepository")

    result = pipeline_module.run_pipeline(ALERT, session=object())

    assert call_order == ["classify", "retrieve", "investigate", "propose", "approve"]
    assert transitions == ["classify", "retrieve", "investigate", "propose", "approve"]
    mock_run_repo.mark_completed.assert_called_once_with(run.id)
    mock_run_repo.mark_failed.assert_not_called()
    assert result is run


def test_run_pipeline_marks_failed_and_returns_run_on_node_exception(mocker) -> None:
    def classify_boom(state):
        raise RuntimeError("boom")

    mocker.patch.object(pipeline_module, "classify", classify_boom)
    mocker.patch.object(pipeline_module, "_COMPILED_GRAPH", pipeline_module._build_graph())

    run = mocker.Mock(id=uuid.uuid4())
    mock_run_repo = mocker.Mock()
    mock_run_repo.create.return_value = run
    mocker.patch.object(pipeline_module, "PipelineRunRepository", return_value=mock_run_repo)

    mock_session = mocker.Mock()
    result = pipeline_module.run_pipeline(ALERT, session=mock_session)

    mock_session.rollback.assert_called_once()
    mock_run_repo.mark_failed.assert_called_once_with(run.id)
    mock_run_repo.mark_completed.assert_not_called()
    assert result is run
