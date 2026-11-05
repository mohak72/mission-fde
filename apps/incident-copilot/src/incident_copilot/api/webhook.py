from collections.abc import Generator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from incident_copilot.config import settings
from incident_copilot.ingestion import ingest_alert
from incident_copilot.ingestion.auth import verify_signature
from incident_copilot.ingestion.schemas import AlertPayload
from incident_copilot.persistence.models import SessionLocal

router = APIRouter()


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@router.post("/webhook/alert", status_code=status.HTTP_202_ACCEPTED)
async def receive_alert(request: Request, session: Session = Depends(get_session)) -> dict:
    """[Source: architecture/rest-api-spec.md#pathswebhookalert]

    Signature is verified over the raw body, before any JSON parsing (NFR9
    AC4) -- this is why the route takes a `Request`, not a pydantic model,
    as its parameter. [Source: architecture/security.md#input-validation]
    """
    raw_body = await request.body()
    signature = request.headers.get("X-Signature")

    if not verify_signature(raw_body, signature, settings.webhook_hmac_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid signature")

    try:
        payload = AlertPayload.model_validate_json(raw_body)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="malformed payload"
        ) from exc

    _alert, created = ingest_alert(payload, session)
    return {
        "alert_id": payload.alert_id,
        "status": "accepted" if created else "deduplicated",
    }
