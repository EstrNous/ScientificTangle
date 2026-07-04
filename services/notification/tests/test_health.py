from app.api.factory import create_app
from fastapi.testclient import TestClient


def test_health_smoke() -> None:
    app = create_app()
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/metrics").status_code == 200
