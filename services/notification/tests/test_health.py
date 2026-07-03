from fastapi.testclient import TestClient

from app.main import app


def test_health_smoke() -> None:
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200
    assert client.get("/metrics").status_code == 200
