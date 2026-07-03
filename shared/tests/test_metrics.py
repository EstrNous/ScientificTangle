from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.metrics import build_metrics_router, setup_metrics


def test_metrics_router_exposes_prometheus() -> None:
    app = FastAPI()
    setup_metrics(app, "test-service")
    app.include_router(build_metrics_router())
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")
