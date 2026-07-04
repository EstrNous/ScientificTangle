import asyncio

import httpx
import pytest
from app.core.config import settings
from app.service.service import GatewayService, GatewayServiceError


def test_run_query_keeps_legacy_filters_when_flag_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "top1_scientific_query_enabled", False)
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.read().decode()
        return httpx.Response(200, json={"id": "run-1"})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = GatewayService(client, "http://orchestrator", 1024)
            await service.run_query(
                {"question": "никель", "filters": {}, "limit": 10},
                "Bearer token",
                "req-legacy",
            )

    asyncio.run(run())
    assert "top1_scientific_query" not in str(captured["body"])


def test_run_query_respects_explicit_scientific_filter_false(monkeypatch) -> None:
    monkeypatch.setattr(settings, "top1_scientific_query_enabled", True)
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.read().decode()
        return httpx.Response(200, json={"id": "run-1"})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = GatewayService(client, "http://orchestrator", 1024)
            await service.run_query(
                {
                    "question": "никель",
                    "filters": {"top1_scientific_query": False},
                    "limit": 10,
                },
                "Bearer token",
                "req-override",
            )

    asyncio.run(run())
    body = str(captured["body"])
    assert '"top1_scientific_query": false' in body or '"top1_scientific_query":false' in body
    assert body.count("top1_scientific_query") == 1


def test_stream_query_injects_scientific_flag_when_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "top1_scientific_query_enabled", True)
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["body"] = request.read().decode()
        return httpx.Response(200, content=b'data: {"type":"done","payload":{}}\n\n')

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = GatewayService(client, "http://orchestrator", 1024)
            async for _ in service.stream_query(
                {"question": "никель", "filters": {}, "limit": 10},
                "Bearer token",
                "req-stream-flag",
            ):
                pass

    asyncio.run(run())
    assert captured["path"] == "/query/stream"
    assert "top1_scientific_query" in str(captured["body"])


def test_run_query_maps_orchestrator_timeout() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("orchestrator timeout")

    async def run() -> GatewayServiceError:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = GatewayService(client, "http://orchestrator", 1024)
            with pytest.raises(GatewayServiceError) as error:
                await service.run_query(
                    {"question": "никель", "filters": {}, "limit": 10},
                    "Bearer token",
                    "req-timeout",
                )
            return error.value

    error = asyncio.run(run())
    assert error.status_code == 504
    assert error.code == "orchestrator_timeout"


def test_stream_query_maps_orchestrator_timeout() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("orchestrator timeout")

    async def run() -> GatewayServiceError:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = GatewayService(client, "http://orchestrator", 1024)
            with pytest.raises(GatewayServiceError) as error:
                async for _ in service.stream_query(
                    {"question": "никель", "filters": {}, "limit": 10},
                    "Bearer token",
                    "req-stream-timeout",
                ):
                    pass
            return error.value

    error = asyncio.run(run())
    assert error.status_code == 504
    assert error.code == "orchestrator_timeout"
