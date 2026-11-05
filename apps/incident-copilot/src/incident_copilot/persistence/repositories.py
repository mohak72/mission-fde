import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from incident_copilot.persistence.models import Alert


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
