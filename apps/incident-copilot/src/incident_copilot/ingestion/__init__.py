from sqlalchemy.orm import Session

from incident_copilot.ingestion.schemas import AlertPayload
from incident_copilot.persistence.models import Alert
from incident_copilot.persistence.repositories import AlertRepository


def ingest_alert(payload: AlertPayload, session: Session) -> tuple[Alert, bool]:
    """The one entrypoint both the webhook route and the future MCP handler
    (Story 5.2) call -- never duplicate this logic inline in a route.

    Returns (alert, created) -- created=False means this was a duplicate
    delivery (AC3); no second pipeline run is triggered either way, since the
    Diagnosis Graph does not exist yet (Story 2.2).

    [Source: architecture/components.md#ingestion-module]
    """
    repo = AlertRepository(session)
    team = payload.labels.get("team")
    return repo.insert_if_new(
        external_alert_id=payload.alert_id,
        payload=payload.model_dump(mode="json"),
        signature_verified=True,
        team=team,
    )
