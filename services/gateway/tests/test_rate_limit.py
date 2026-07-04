from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


def test_gateway_rate_limit_blocks_api_route_before_auth() -> None:
    app = create_app(
        Settings(
            rate_limit_enabled=True,
            rate_limit_default_per_minute=1,
            rate_limit_use_redis=False,
        )
    )

    @app.get("/limited-test")
    async def limited_test() -> dict[str, bool]:
        return {"ok": True}

    client = TestClient(app)

    first = client.get("/limited-test", headers={"X-Request-ID": "gateway-1"})
    second = client.get("/limited-test", headers={"X-Request-ID": "gateway-2"})

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["code"] == "rate_limited"
    assert second.json()["request_id"] == "gateway-2"


def test_gateway_rate_limit_excludes_health() -> None:
    app = create_app(
        Settings(
            rate_limit_enabled=True,
            rate_limit_default_per_minute=1,
            rate_limit_use_redis=False,
        )
    )
    client = TestClient(app)

    statuses = [client.get("/health").status_code for _ in range(3)]

    assert statuses == [200, 200, 200]
