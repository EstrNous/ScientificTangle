import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "infra" / "nginx" / "nginx.cloud.http.conf"

INTERNAL_UPSTREAMS = (
    "proxy_pass http://orchestrator",
    "proxy_pass http://ingestion",
    "proxy_pass http://knowledge",
    "proxy_pass http://retrieval",
    "proxy_pass http://model_svc",
    "proxy_pass http://model",
)

INTERNAL_BLOCK_PATTERN = re.compile(
    r"location\s+~\s+\^/\(orchestrator\|ingestion\|knowledge\|retrieval\|model\)\(/|\$\)\s*\{[^}]*return\s+404;",
    re.DOTALL,
)


def test_cloud_http_config_blocks_internal_services() -> None:
    content = CONFIG_PATH.read_text(encoding="utf-8")
    for needle in INTERNAL_UPSTREAMS:
        assert needle not in content, needle
    assert INTERNAL_BLOCK_PATTERN.search(content), "internal prefix block with return 404"


def test_cloud_http_config_exposes_public_routes() -> None:
    content = CONFIG_PATH.read_text(encoding="utf-8")
    assert "location /api/" in content
    assert "proxy_pass http://gateway/" in content
    assert "location /api/auth/" in content
    assert "location /grafana/" in content
    assert "listen 80;" in content
    assert "ssl_certificate" not in content
