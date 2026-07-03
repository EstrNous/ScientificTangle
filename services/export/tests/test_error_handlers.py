from app.main import app
from fastapi.testclient import TestClient


def test_not_found_returns_api_error() -> None:
    with TestClient(app) as client:
        response = client.get("/missing-endpoint")
    assert response.status_code == 404
    assert response.json()["code"] == "http_error"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
