import asyncio

import httpx
import pytest
from app.core.config import settings
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


def test_run_query_injects_scientific_flag_when_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "top1_scientific_query_enabled", True)
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.read().decode()
        return httpx.Response(200, json={"answer": {"summary": "ok"}})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = GatewayService(client, "http://orchestrator", 1024)
            await service.run_query(
                {"question": "никель", "filters": {}, "limit": 10},
                "Bearer token",
                "req-1",
            )

    asyncio.run(run())
    assert "top1_scientific_query" in str(captured["body"])


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


def test_export_query_forwards_to_orchestrator() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["authorization"] = request.headers["Authorization"]
        captured["request_id"] = request.headers["X-Request-ID"]
        captured["body"] = request.read().decode()
        return httpx.Response(
            200,
            json={
                "export_job_id": "ed791c22-76e3-469a-ac76-26fe5aeb8792",
                "query_run_id": "28df9d8f-7be5-474d-bf95-1bbda500c8b2",
                "format": "markdown",
                "status": "completed",
                "content_type": "text/markdown",
                "content": {
                    "answer": "ok",
                    "evidence": [{"source_span_id": "span-1"}],
                    "sources": [{"document_id": "doc-1"}],
                    "graph": {"nodes": [], "links": []},
                    "gaps": [],
                    "conflicts": [],
                    "query_ir": {"raw_query": "x", "filters": {}},
                    "retrieval_trace": {"storage": "hybrid"},
                    "user_role": "researcher",
                    "access_scope": ["public", "internal"],
                    "warnings": [],
                },
                "file_url": "inline://export-jobs/test.md",
                "warnings": [],
                "format_status": [
                    {"format": "markdown", "available": True, "status": "available"},
                    {"format": "json", "available": True, "status": "available"},
                    {"format": "jsonld", "available": False, "status": "backlog"},
                    {"format": "pdf", "available": False, "status": "backlog"},
                ],
                "generated_at": "2026-07-04T12:00:00+00:00",
            },
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = GatewayService(client, "http://orchestrator", 1024)
            result = await service.export_query_run(
                {
                    "query_run_id": "28df9d8f-7be5-474d-bf95-1bbda500c8b2",
                    "format": "markdown",
                },
                "Bearer token",
                "req-2",
            )
            assert result["format"] == "markdown"
            assert result["content"]["answer"] == "ok"
            assert result["content"]["retrieval_trace"]["storage"] == "hybrid"
            assert {item["format"]: item["status"] for item in result["format_status"]}["pdf"] == "backlog"

    import asyncio

    asyncio.run(run())
    assert captured["path"] == "/export"
    assert captured["authorization"] == "Bearer token"
    assert captured["request_id"] == "req-2"
    assert "markdown" in str(captured["body"])
