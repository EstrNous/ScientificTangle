import os
import socket

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_PROD_COMPOSE") != "1",
    reason="Set RUN_PROD_COMPOSE=1 with make up-prod",
)

CLOSED_PORTS = (5432, 6379, 7474, 7687, 6333, 8000, 8001, 8002, 8003, 8004, 8005, 8006, 9090, 3000, 3001)
BYPASS_PATHS = ("/model/health", "/knowledge/health", "/orchestrator/health")


def _edge_verify() -> bool:
    return os.getenv("EDGE_TLS_VERIFY", "false").lower() in {"1", "true", "yes"}


@pytest.mark.parametrize("port", CLOSED_PORTS)
def test_internal_ports_not_published_on_host(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1.0)
        assert sock.connect_ex(("127.0.0.1", port)) != 0, port


def test_https_edge_api_health() -> None:
    edge_url = os.getenv("EDGE_URL", "https://localhost/api/health")
    response = httpx.get(edge_url, timeout=5.0, verify=_edge_verify())
    assert response.status_code == 200
    assert response.json().get("status") == "ok"


@pytest.mark.parametrize("path", BYPASS_PATHS)
def test_internal_bypass_routes_are_blocked(path: str) -> None:
    edge_base = os.getenv("EDGE_BASE_URL", "https://localhost")
    response = httpx.get(f"{edge_base}{path}", timeout=5.0, verify=_edge_verify())
    assert response.status_code == 404
