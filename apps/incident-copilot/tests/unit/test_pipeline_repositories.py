import uuid
from datetime import UTC, datetime

from incident_copilot.persistence.models import DiagnosisProposal, PipelineRun
from incident_copilot.persistence.repositories import (
    DiagnosisProposalRepository,
    PipelineRunRepository,
)


class _FakeSession:
    """Minimal in-memory stand-in -- avoids a real DB for these unit tests,
    same convention as mocking SQLAlchemy in test_retrieval.py (via mocker)
    but here we need `.get()`/attribute-mutation semantics, so a tiny fake
    is clearer than a deep mock chain."""

    def __init__(self) -> None:
        self.added: list = []
        self.committed = False
        self._by_id: dict = {}

    def add(self, obj) -> None:
        self.added.append(obj)
        self._by_id[obj.id] = obj

    def commit(self) -> None:
        self.committed = True

    def get(self, model, pk):
        return self._by_id.get(pk)


def test_pipeline_run_repository_create_sets_running_status_and_empty_transitions() -> None:
    session = _FakeSession()
    alert_id = uuid.uuid4()

    run = PipelineRunRepository(session).create(alert_id, "amazon.nova-micro-v1:0")

    assert isinstance(run, PipelineRun)
    assert run.alert_id == alert_id
    assert run.status == "running"
    assert run.node_transitions == []
    assert run.llm_provider_config == "amazon.nova-micro-v1:0"
    assert session.committed is True


def test_pipeline_run_repository_append_transition_appends_to_existing_log() -> None:
    session = _FakeSession()
    run = PipelineRunRepository(session).create(uuid.uuid4(), "amazon.nova-micro-v1:0")
    entered = datetime(2026, 11, 10, 12, 0, 0, tzinfo=UTC)
    exited = datetime(2026, 11, 10, 12, 0, 1, tzinfo=UTC)

    PipelineRunRepository(session).append_transition(run.id, "classify", entered, exited, "ok")

    assert run.node_transitions == [
        {
            "node_name": "classify",
            "entered_at": entered.isoformat(),
            "exited_at": exited.isoformat(),
            "output_summary": "ok",
        }
    ]


def test_pipeline_run_repository_mark_completed_sets_status() -> None:
    session = _FakeSession()
    run = PipelineRunRepository(session).create(uuid.uuid4(), "amazon.nova-micro-v1:0")

    PipelineRunRepository(session).mark_completed(run.id)

    assert run.status == "completed"


def test_pipeline_run_repository_mark_failed_sets_status() -> None:
    session = _FakeSession()
    run = PipelineRunRepository(session).create(uuid.uuid4(), "amazon.nova-micro-v1:0")

    PipelineRunRepository(session).mark_failed(run.id)

    assert run.status == "failed"


def test_diagnosis_proposal_repository_create_persists_all_fields() -> None:
    session = _FakeSession()
    pipeline_run_id = uuid.uuid4()

    proposal = DiagnosisProposalRepository(session).create(
        pipeline_run_id=pipeline_run_id,
        runbook_id="pod-crashloop-oom",
        cause="Container exceeded its memory limit",
        next_step_action="Raise resources.limits.memory",
        runbook_citation="Resolution",
        live_evidence=None,
        grounded_in_live_state=False,
    )

    assert isinstance(proposal, DiagnosisProposal)
    assert proposal.pipeline_run_id == pipeline_run_id
    assert proposal.runbook_id == "pod-crashloop-oom"
    assert proposal.cause == "Container exceeded its memory limit"
    assert proposal.next_step_action == "Raise resources.limits.memory"
    assert proposal.runbook_citation == "Resolution"
    assert proposal.live_evidence is None
    assert proposal.grounded_in_live_state is False
    assert session.committed is True
