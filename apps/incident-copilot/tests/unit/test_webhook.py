import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from incident_copilot.api.webhook import get_session
from incident_copilot.config import settings
from incident_copilot.main import app

SECRET = settings.webhook_hmac_secret

VALID_PAYLOAD = {
    "alert_id": "alert-1",
    "labels": {"team": "sre"},
    "annotations": {"summary": "pod crashlooping"},
    "startsAt": "2026-11-05T12:00:00Z",
}


def _sign(body: bytes, secret: str = SECRET) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides[get_session] = lambda: iter([object()])
    yield TestClient(app)
    app.dependency_overrides.pop(get_session, None)


def test_valid_signed_payload_is_accepted(client: TestClient, mocker) -> None:
    mocker.patch("incident_copilot.api.webhook.ingest_alert", return_value=(object(), True))
    body = json.dumps(VALID_PAYLOAD).encode()

    response = client.post(
        "/webhook/alert",
        content=body,
        headers={"X-Signature": _sign(body)},
    )

    assert response.status_code == 202
    assert response.json() == {"alert_id": "alert-1", "status": "accepted"}


def test_duplicate_alert_is_deduplicated_not_a_second_run(client: TestClient, mocker) -> None:
    mocker.patch("incident_copilot.api.webhook.ingest_alert", return_value=(object(), False))
    body = json.dumps(VALID_PAYLOAD).encode()

    response = client.post(
        "/webhook/alert",
        content=body,
        headers={"X-Signature": _sign(body)},
    )

    assert response.status_code == 202
    assert response.json() == {"alert_id": "alert-1", "status": "deduplicated"}


def test_malformed_payload_is_rejected(client: TestClient, mocker) -> None:
    ingest = mocker.patch("incident_copilot.api.webhook.ingest_alert")
    body = b'{"not_a_valid_alert": true}'

    response = client.post(
        "/webhook/alert",
        content=body,
        headers={"X-Signature": _sign(body)},
    )

    assert response.status_code == 400
    ingest.assert_not_called()


def test_unsigned_request_is_rejected(client: TestClient, mocker) -> None:
    ingest = mocker.patch("incident_copilot.api.webhook.ingest_alert")
    body = json.dumps(VALID_PAYLOAD).encode()

    response = client.post("/webhook/alert", content=body)

    assert response.status_code == 401
    ingest.assert_not_called()


def test_invalid_signature_request_is_rejected(client: TestClient, mocker) -> None:
    ingest = mocker.patch("incident_copilot.api.webhook.ingest_alert")
    body = json.dumps(VALID_PAYLOAD).encode()

    response = client.post(
        "/webhook/alert",
        content=body,
        headers={"X-Signature": _sign(body, secret="wrong-secret")},
    )

    assert response.status_code == 401
    ingest.assert_not_called()
