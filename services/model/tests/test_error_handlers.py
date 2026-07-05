from app.main import app
from fastapi.testclient import TestClient


def test_validation_error_returns_api_error() -> None:
    with TestClient(app) as client:
        response = client.post("/v1/embeddings", json={})
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
