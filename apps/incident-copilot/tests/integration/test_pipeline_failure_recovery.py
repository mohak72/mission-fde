"""QA Story 2.2 REL-003: run_pipeline's except block must recover cleanly
even when the failure that triggered it was itself raised by a SQL
statement on the active session (leaving it in SQLAlchemy's "pending
rollback" state) -- a mocked session can't reproduce that state, so this
needs a real Postgres session. [Source: docs/qa/gates/2.2-langgraph-state-machine-refactor.yml]
"""

import pytest
from sqlalchemy.exc import PendingRollbackError
from sqlalchemy.orm import Session

from incident_copilot.graph.nodes.propose import DiagnosisResult
from incident_copilot.graph.pipeline import run_pipeline
from incident_copilot.persistence.models import PipelineRun
from incident_copilot.persistence.repositories import AlertRepository
from incident_copilot.retrieval.seed_runbooks import seed_runbooks

ALERT_PAYLOAD = {
    "labels": {"alertname": "KubePodCrashLooping", "pod": "checkout-7f9c-abc12"},
    "annotations": {"summary": "Pod checkout-7f9c-abc12 is crash looping"},
}


def test_run_pipeline_recovers_from_db_originated_failure(mocker, db_session: Session) -> None:
    """Force a NOT NULL violation inside the proposal-persistence step (a
    DiagnosisResult with cause=None, matched=True) so the exception that
    lands in run_pipeline's except block is DB-originated. Before the
    REL-003 fix, run_repo.mark_failed() on the now-dirty session raised
    PendingRollbackError and escaped uncaught; the fix rolls back first.
    """
    seed_runbooks(db_session)
    alert, _ = AlertRepository(db_session).insert_if_new(
        "rel-003-regression", ALERT_PAYLOAD, signature_verified=True
    )
    mocker.patch(
        "incident_copilot.graph.pipeline.propose_diagnosis",
        return_value=DiagnosisResult(matched=True, cause=None, next_step_action="x"),
    )

    try:
        run = run_pipeline(alert, db_session)
    except PendingRollbackError:
        pytest.fail(
            "run_pipeline re-raised PendingRollbackError instead of recovering -- "
            "REL-003 regression: session.rollback() missing before mark_failed()"
        )

    assert run.status == "failed"
    persisted = db_session.query(PipelineRun).filter(PipelineRun.id == run.id).one()
    assert persisted.status == "failed"
