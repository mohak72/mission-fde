import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from incident_copilot.persistence.models import Alert, Runbook


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
