import os

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_E2E") != "1",
    reason="Set RUN_E2E=1 with docker compose up",
)

BASE_SERVICE_URLS = {
    "gateway": "http://localhost:8000",
    "auth_audit": "http://localhost:8001",
    "orchestrator": "http://localhost:8002",
    "ingestion": "http://localhost:8003",
    "knowledge": "http://localhost:8004",
    "retrieval": "http://localhost:8005",
}

MODEL_SERVICE_URL = ("model", "http://localhost:8006")


def service_urls() -> list[tuple[str, str]]:
    items = list(BASE_SERVICE_URLS.items())
    if os.getenv("RUN_MODEL_TESTS") == "1":
        items.append(MODEL_SERVICE_URL)
    return items


@pytest.mark.parametrize("name,base_url", service_urls())
def test_service_health(name: str, base_url: str) -> None:
    response = httpx.get(f"{base_url}/health", timeout=5.0)
    assert response.status_code == 200, name
    assert response.json().get("status") == "ok"
