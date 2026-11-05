import pytest
from fastapi.testclient import TestClient

from incident_copilot.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
