from fastapi.testclient import TestClient

from app.main import app


def test_health_is_available_with_a_request_id() -> None:
    response = TestClient(app).get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Request-ID"]
