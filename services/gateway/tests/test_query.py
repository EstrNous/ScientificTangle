import httpx
import pytest
from app.service.service import GatewayService, GatewayServiceError


def test_run_query_forwards_to_orchestrator() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["authorization"] = request.headers["Authorization"]
        captured["request_id"] = request.headers["X-Request-ID"]
        captured["body"] = request.read().decode()
        return httpx.Response(200, json={"answer": {"summary": "ok"}})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = GatewayService(client, "http://orchestrator", 1024)
            result = await service.run_query(
                {"question": "никель", "filters": {}, "limit": 10},
                "Bearer token",
                "req-1",
            )
            assert result["answer"]["summary"] == "ok"

    import asyncio

    asyncio.run(run())
    assert captured["path"] == "/query/run"
    assert captured["authorization"] == "Bearer token"
    assert captured["request_id"] == "req-1"
    assert "никель" in str(captured["body"])


def test_run_query_maps_downstream_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(502, json={"code": "downstream", "message": "fail", "request_id": "r"})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = GatewayService(client, "http://orchestrator", 1024)
            with pytest.raises(GatewayServiceError) as exc:
                await service.run_query({"question": "x", "filters": {}, "limit": 20}, "Bearer t", "req")
            assert exc.value.status_code == 502

    import asyncio

    asyncio.run(run())
