from app.main import app as retrieval_app
from fastapi.testclient import TestClient


def test_retrieval_health_offline() -> None:
    with TestClient(retrieval_app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
