"""The single seam (NFR8) between callers and whatever vector store is active.

[Source: architecture/components.md#retrieval-service]
"""

import time

import structlog
from sqlalchemy.orm import Session

from incident_copilot.persistence.models import Alert, Runbook
from incident_copilot.persistence.repositories import RunbookRepository
from incident_copilot.retrieval.chroma_backend import (
    EMBEDDING_MODEL_NAME,
    query_nearest,
    upsert_embedding,
)

logger = structlog.get_logger(component="retrieval")


def index_runbook(runbook: Runbook, session: Session) -> None:
    """Corpus management: persists metadata/content to Postgres, then embeds
    `runbook.content` into Chroma, keyed by `runbook.id`.
    """
    RunbookRepository(session).upsert(
        runbook_id=runbook.id,
        title=runbook.title,
        content=runbook.content,
        failure_mode_tags=runbook.failure_mode_tags,
        team=runbook.team,
    )
    upsert_embedding(runbook.id, runbook.content)


def _query_text_for_alert(alert: Alert) -> str:
    """No specific guidance exists in the architecture docs for exactly which
    Alert fields to embed as the query text. Chosen default: concatenate all
    label and annotation values -- documented here, not silently assumed.
    """
    labels: dict[str, str] = alert.payload.get("labels", {})
    annotations: dict[str, str] = alert.payload.get("annotations", {})
    return " ".join([*labels.values(), *annotations.values()])


def retrieve_runbook(alert: Alert, session: Session) -> Runbook | None:
    """Always returns the top-1 nearest match in this story -- the
    `None`-on-low-confidence threshold is Story 2.1's addition, not this
    story's. [Source: architecture/components.md#retrieval-service]
    """
    query_text = _query_text_for_alert(alert)

    start = time.monotonic()
    nearest_ids = query_nearest(query_text, n_results=1)
    latency_ms = (time.monotonic() - start) * 1000

    logger.info(
        "runbook_retrieved",
        latency_ms=round(latency_ms, 2),
        embedding_model=EMBEDDING_MODEL_NAME,
    )

    if not nearest_ids:
        return None

    return RunbookRepository(session).get_by_id(nearest_ids[0])
