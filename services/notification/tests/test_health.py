from app.api.factory import create_app
from app.core.config import Settings
from fastapi.testclient import TestClient


def test_health_smoke() -> None:
    app = create_app(Settings(notification_redis_pubsub_enabled=False))
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/metrics").status_code == 200
