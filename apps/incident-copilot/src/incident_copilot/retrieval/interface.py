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

# Chroma's default distance space is squared-L2 (lower = more similar). Picked
# empirically against the 10 hand-labeled cases from tests/fixtures/
# retrieval_test_cases.py: every correct match there scores 0.21-0.37, while
# three clearly-unrelated probe queries ("what is the capital of France", etc.)
# scored 0.88-0.96 -- 0.5 sits comfortably in the gap between those two
# clusters. [Source: Story 2.1 Completion Notes]
CONFIDENCE_DISTANCE_THRESHOLD = 0.5


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
    """Returns the top-1 nearest match, or `None` if it's below the
    confidence threshold (AC3 -- added this story; Story 1.3 always returned
    the top-1 match regardless of distance).
    [Source: architecture/components.md#retrieval-service]
    """
    query_text = _query_text_for_alert(alert)

    start = time.monotonic()
    nearest = query_nearest(query_text, n_results=1)
    latency_ms = (time.monotonic() - start) * 1000

    logger.info(
        "runbook_retrieved",
        latency_ms=round(latency_ms, 2),
        embedding_model=EMBEDDING_MODEL_NAME,
    )

    if not nearest:
        return None

    nearest_id, distance = nearest[0]
    if distance > CONFIDENCE_DISTANCE_THRESHOLD:
        return None

    return RunbookRepository(session).get_by_id(nearest_id)
