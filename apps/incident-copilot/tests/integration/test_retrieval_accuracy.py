import pytest
from fixtures.retrieval_test_cases import RETRIEVAL_TEST_CASES
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from incident_copilot.config import settings
from incident_copilot.persistence.models import Alert
from incident_copilot.retrieval.interface import retrieve_runbook
from incident_copilot.retrieval.seed_runbooks import seed_runbooks

TEST_DB_NAME = "incident_copilot_test"


def _swap_db_name(url: str, db_name: str) -> str:
    return url.rsplit("/", 1)[0] + f"/{db_name}"


@pytest.fixture(scope="session")
def seeded_corpus() -> Session:
    """Seeds the full runbook corpus once per session, against the same
    dedicated test Postgres database and isolated Chroma collection
    `conftest.py`'s session-scoped fixtures set up (real infra, not mocked --
    this is the one place AC3's accuracy requirement is actually verified).
    """
    engine = create_engine(_swap_db_name(settings.database_url, TEST_DB_NAME))
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = session_factory()
    seed_runbooks(session)
    yield session
    session.close()
    engine.dispose()


def test_retrieval_accuracy_at_least_8_of_10(seeded_corpus: Session) -> None:
    """AC3: at least 8/10 hand-labeled test cases must retrieve the correct
    runbook. [Source: architecture/test-strategy-and-standards.md#integration-tests]
    """
    hits = 0
    misses: list[tuple[str, str | None]] = []

    for case in RETRIEVAL_TEST_CASES:
        alert = Alert(
            id=None,
            external_alert_id="irrelevant-for-this-test",
            payload={"labels": case["labels"], "annotations": case["annotations"]},
            received_at=None,
            signature_verified=True,
        )
        result = retrieve_runbook(alert, seeded_corpus)
        retrieved_id = result.id if result else None
        if retrieved_id == case["expected_runbook_id"]:
            hits += 1
        else:
            misses.append((case["expected_runbook_id"], retrieved_id))

    assert hits >= 8, f"Only {hits}/10 correct; misses (expected, got): {misses}"
