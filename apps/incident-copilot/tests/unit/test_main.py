from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    # Arrange: app + client come from conftest's fixture

    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
