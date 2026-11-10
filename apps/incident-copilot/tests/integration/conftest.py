import shutil
import tempfile
import uuid

import psycopg
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from incident_copilot.config import settings
from incident_copilot.persistence.models import Base
from incident_copilot.retrieval import chroma_backend

TEST_DB_NAME = "incident_copilot_test"


def _swap_db_name(url: str, db_name: str) -> str:
    return url.rsplit("/", 1)[0] + f"/{db_name}"


def _psycopg_url(sqlalchemy_url: str) -> str:
    # psycopg.connect() doesn't understand the "+psycopg" SQLAlchemy dialect suffix.
    return sqlalchemy_url.replace("postgresql+psycopg://", "postgresql://")


@pytest.fixture(scope="session", autouse=True)
def _test_database():
    """Dedicated test database -- never the dev one.

    [Source: architecture/test-strategy-and-standards.md#test-data-management]
    """
    admin_url = _psycopg_url(_swap_db_name(settings.database_url, "postgres"))
    test_url = _swap_db_name(settings.database_url, TEST_DB_NAME)

    with psycopg.connect(admin_url, autocommit=True) as admin_conn:
        admin_conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}")
        admin_conn.execute(f"CREATE DATABASE {TEST_DB_NAME}")

    engine = create_engine(test_url)
    Base.metadata.create_all(engine)
    engine.dispose()

    yield

    with psycopg.connect(admin_url, autocommit=True) as admin_conn:
        admin_conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}")


@pytest.fixture(scope="session", autouse=True)
def _chroma_test_isolation():
    """Dedicated, uniquely-named Chroma persist directory + collection per
    test session -- never the dev one, dropped on teardown.

    [Source: architecture/test-strategy-and-standards.md#test-data-management]
    """
    tmp_dir = tempfile.mkdtemp(prefix="chroma_test_")
    settings.chroma_persist_directory = tmp_dir
    settings.chroma_collection_name = f"runbooks_test_{uuid.uuid4().hex[:8]}"
    chroma_backend.reset_client()

    yield

    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def db_session():
    test_url = _swap_db_name(settings.database_url, TEST_DB_NAME)
    engine = create_engine(test_url)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    session: Session = session_factory()
    try:
        yield session
    finally:
        session.execute(text("TRUNCATE alerts, pipeline_runs, diagnosis_proposals CASCADE"))
        session.commit()
        session.close()
        engine.dispose()
