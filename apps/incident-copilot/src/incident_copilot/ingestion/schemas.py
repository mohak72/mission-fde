from datetime import datetime

from pydantic import BaseModel


class AlertPayload(BaseModel):
    """Matches the OpenAPI `AlertPayload` schema exactly.

    [Source: architecture/rest-api-spec.md#componentsschemasalertpayload]
    """

    alert_id: str
    labels: dict[str, str]
    annotations: dict[str, str]
    startsAt: datetime  # noqa: N815 -- field name mirrors the Alertmanager-style wire schema
