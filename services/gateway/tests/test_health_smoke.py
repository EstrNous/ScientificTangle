from fastapi.testclient import TestClient

from app.main import app


def test_health_smoke() -> None:
    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    ready = client.get("/ready")
    assert ready.status_code == 200
    metrics = client.get("/metrics")
    assert metrics.status_code == 200
