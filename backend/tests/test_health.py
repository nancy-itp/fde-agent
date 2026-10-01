from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_reports_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "environment": "development"}


def test_health_requires_no_auth() -> None:
    """Liveness checks must stay reachable with no bearer token."""
    response = client.get("/health")
    assert response.status_code != 401
