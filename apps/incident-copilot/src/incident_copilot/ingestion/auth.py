import hashlib
import hmac


def verify_signature(raw_body: bytes, signature_header: str | None, secret: str) -> bool:
    """HMAC-SHA256 over the raw request body.

    `signature_header` is the raw `X-Signature` header value; a missing header
    is treated as an invalid signature, not a special case.

    [Source: architecture/security.md#authentication--authorization]
    [Source: architecture/rest-api-spec.md#componentssecurityschemes]
    """
    if not signature_header:
        return False

    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    # constant-time comparison -- avoids a timing side-channel on string equality
    return hmac.compare_digest(expected, signature_header)
