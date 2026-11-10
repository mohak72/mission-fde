import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from incident_copilot.persistence.models import Alert, DiagnosisProposal, PipelineRun, Runbook


class AlertRepository:
    """The only module allowed to issue queries against `alerts`.

    [Source: architecture/coding-standards.md#critical-rules]
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def insert_if_new(
        self,
        external_alert_id: str,
        payload: dict,
        signature_verified: bool,
        team: str | None = None,
    ) -> tuple[Alert, bool]:
        """Atomic dedup: INSERT ... ON CONFLICT DO NOTHING, then SELECT either way.

        Returns (alert, created) where created=True only if this call inserted
        the row.

        [Source: architecture/database-schema.md, architecture/components.md#ingestion-module]
        """
        stmt = (
            insert(Alert)
            .values(
                id=uuid.uuid4(),
                external_alert_id=external_alert_id,
                payload=payload,
                signature_verified=signature_verified,
                team=team,
            )
            .on_conflict_do_nothing(index_elements=["external_alert_id"])
            .returning(Alert.id)
        )
        result = self._session.execute(stmt)
        self._session.commit()
        created = result.first() is not None

        alert = self._session.scalars(
            select(Alert).where(Alert.external_alert_id == external_alert_id)
        ).one()
        return alert, created


class RunbookRepository:
    """The only module allowed to issue queries against `runbooks`.

    [Source: architecture/coding-standards.md#critical-rules]
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert(
        self,
        runbook_id: str,
        title: str,
        content: str,
        failure_mode_tags: list[str],
        team: str | None = None,
    ) -> Runbook:
        """Insert or replace a runbook's metadata/content, keyed by its stable id.

        Upsert (not insert-only) because the seed script is re-run idempotently
        -- re-seeding the same corpus must not error or duplicate rows.
        """
        stmt = (
            insert(Runbook)
            .values(
                id=runbook_id,
                title=title,
                content=content,
                failure_mode_tags=failure_mode_tags,
                team=team,
            )
            .on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "title": title,
                    "content": content,
                    "failure_mode_tags": failure_mode_tags,
                    "team": team,
                },
            )
        )
        self._session.execute(stmt)
        self._session.commit()
        return self._session.scalars(select(Runbook).where(Runbook.id == runbook_id)).one()

    def get_by_id(self, runbook_id: str) -> Runbook | None:
        return self._session.scalars(select(Runbook).where(Runbook.id == runbook_id)).one_or_none()


class PipelineRunRepository:
    """The only module allowed to issue queries against `pipeline_runs`.

    [Source: architecture/coding-standards.md#critical-rules]
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, alert_id: uuid.UUID, llm_provider_config: str) -> PipelineRun:
        run = PipelineRun(
            id=uuid.uuid4(),
            alert_id=alert_id,
            status="running",
            node_transitions=[],
            llm_provider_config=llm_provider_config,
        )
        self._session.add(run)
        self._session.commit()
        return run

    def append_transition(
        self,
        pipeline_run_id: uuid.UUID,
        node_name: str,
        entered_at: datetime,
        exited_at: datetime,
        output_summary: str,
    ) -> None:
        """Appends one entry to the append-only `node_transitions` log and
        commits independently -- no single long-lived transaction spans the
        whole run. [Source: architecture/error-handling-strategy.md#data-consistency]
        """
        run = self._session.get(PipelineRun, pipeline_run_id)
        run.node_transitions = [
            *run.node_transitions,
            {
                "node_name": node_name,
                "entered_at": entered_at.isoformat(),
                "exited_at": exited_at.isoformat(),
                "output_summary": output_summary,
            },
        ]
        self._session.commit()

    def mark_completed(self, pipeline_run_id: uuid.UUID) -> None:
        run = self._session.get(PipelineRun, pipeline_run_id)
        run.status = "completed"
        self._session.commit()

    def mark_failed(self, pipeline_run_id: uuid.UUID) -> None:
        run = self._session.get(PipelineRun, pipeline_run_id)
        run.status = "failed"
        self._session.commit()


class DiagnosisProposalRepository:
    """The only module allowed to issue queries against `diagnosis_proposals`.

    [Source: architecture/coding-standards.md#critical-rules]
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        pipeline_run_id: uuid.UUID,
        runbook_id: str | None,
        cause: str,
        next_step_action: str,
        runbook_citation: str | None,
        live_evidence: dict | None,
        grounded_in_live_state: bool,
    ) -> DiagnosisProposal:
        proposal = DiagnosisProposal(
            id=uuid.uuid4(),
            pipeline_run_id=pipeline_run_id,
            runbook_id=runbook_id,
            cause=cause,
            next_step_action=next_step_action,
            runbook_citation=runbook_citation,
            live_evidence=live_evidence,
            grounded_in_live_state=grounded_in_live_state,
        )
        self._session.add(proposal)
        self._session.commit()
        return proposal
