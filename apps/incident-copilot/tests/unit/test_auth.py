import hashlib
import hmac

from incident_copilot.ingestion.auth import verify_signature


def test_verify_signature_accepts_correct_signature() -> None:
    body = b'{"alert_id": "a1"}'
    secret = "shh"
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    assert verify_signature(body, signature, secret) is True


def test_verify_signature_rejects_wrong_secret() -> None:
    body = b'{"alert_id": "a1"}'
    signature = hmac.new(b"shh", body, hashlib.sha256).hexdigest()

    assert verify_signature(body, signature, "wrong-secret") is False


def test_verify_signature_rejects_tampered_body() -> None:
    secret = "shh"
    signature = hmac.new(secret.encode(), b'{"alert_id": "a1"}', hashlib.sha256).hexdigest()

    assert verify_signature(b'{"alert_id": "a2"}', signature, secret) is False


def test_verify_signature_rejects_missing_header() -> None:
    assert verify_signature(b'{"alert_id": "a1"}', None, "shh") is False
