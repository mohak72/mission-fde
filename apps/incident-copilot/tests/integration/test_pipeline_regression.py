"""AC3: running an alert through the LangGraph pipeline must produce the
same diagnosis as calling the pre-refactor Story 2.1 `propose_diagnosis`
loop directly -- a regression fixture, not a retrieval-accuracy test (that's
`test_retrieval_accuracy.py`'s job). Real Postgres + real Chroma, Gateway
mocked, same tier/asymmetric-mocking convention as that file.
[Source: architecture/test-strategy-and-standards.md#integration-tests]
"""

from sqlalchemy.orm import Session

from incident_copilot.graph.nodes.propose import propose_diagnosis
from incident_copilot.graph.pipeline import run_pipeline
from incident_copilot.persistence.models import DiagnosisProposal
from incident_copilot.persistence.repositories import AlertRepository
from incident_copilot.retrieval.seed_runbooks import seed_runbooks

ALERT_PAYLOAD = {
    "labels": {"alertname": "KubePodCrashLooping", "pod": "checkout-7f9c-abc12"},
    "annotations": {
        "summary": "Pod checkout-7f9c-abc12 is crash looping",
        "description": "Container checkout was OOMKilled, exit code 137, memory limit exceeded",
    },
}
MOCK_LLM_RESPONSE = (
    "Cause: Container exceeded its memory limit\n"
    "Action: Raise resources.limits.memory\n"
    "Citation: Resolution"
)


def test_run_pipeline_matches_direct_propose_diagnosis_call(mocker, db_session: Session) -> None:
    seed_runbooks(db_session)
    alert, _ = AlertRepository(db_session).insert_if_new(
        "regression-1", ALERT_PAYLOAD, signature_verified=True
    )

    mocker.patch(
        "incident_copilot.graph.nodes.propose.complete",
        return_value=mocker.Mock(content=MOCK_LLM_RESPONSE),
    )

    direct_result = propose_diagnosis(alert, db_session)
    run = run_pipeline(alert, db_session)

    assert run.status == "completed"
    proposal = (
        db_session.query(DiagnosisProposal)
        .filter(DiagnosisProposal.pipeline_run_id == run.id)
        .one()
    )
    assert proposal.cause == direct_result.cause
    assert proposal.next_step_action == direct_result.next_step_action
    assert proposal.runbook_citation == direct_result.runbook_citation


def test_run_pipeline_creates_no_proposal_on_no_match(mocker, db_session: Session) -> None:
    """AC3 edge case: a no-match result (DiagnosisResult(matched=False))
    completes the run without creating a DiagnosisProposal row."""
    seed_runbooks(db_session)
    alert, _ = AlertRepository(db_session).insert_if_new(
        "regression-2",
        {"labels": {"alertname": "TotallyUnrelatedAlert"}, "annotations": {}},
        signature_verified=True,
    )
    mocker.patch("incident_copilot.retrieval.interface.query_nearest", return_value=[])
    mock_complete = mocker.patch("incident_copilot.graph.nodes.propose.complete")

    run = run_pipeline(alert, db_session)

    assert run.status == "completed"
    mock_complete.assert_not_called()
    proposal_count = (
        db_session.query(DiagnosisProposal)
        .filter(DiagnosisProposal.pipeline_run_id == run.id)
        .count()
    )
    assert proposal_count == 0
