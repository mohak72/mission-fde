from sqlalchemy import text
from sqlalchemy.orm import Session

from incident_copilot.persistence.repositories import AlertRepository


def test_duplicate_external_alert_id_does_not_create_second_row(db_session: Session) -> None:
    """Exercises the real UNIQUE constraint + ON CONFLICT DO NOTHING against a
    real Postgres -- the one place this atomicity guarantee is actually proven,
    not just asserted. [Source: architecture/database-schema.md]
    """
    repo = AlertRepository(db_session)

    first, created_first = repo.insert_if_new("dup-1", {"alert_id": "dup-1"}, True)
    second, created_second = repo.insert_if_new("dup-1", {"alert_id": "dup-1"}, True)

    assert created_first is True
    assert created_second is False
    assert first.id == second.id

    row_count = db_session.execute(
        text("SELECT count(*) FROM alerts WHERE external_alert_id = 'dup-1'")
    ).scalar_one()
    assert row_count == 1
