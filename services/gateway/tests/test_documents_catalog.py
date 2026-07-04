def test_list_documents_proxies_to_orchestrator() -> None:
    import asyncio
    from datetime import UTC, datetime
    from uuid import uuid4

    import httpx
    from app.service.service import GatewayService

    captured: dict[str, str] = {}
    now = datetime.now(UTC).isoformat()

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        captured["filter"] = request.url.params.get("filter", "")
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "document_id": "doc-1",
                        "title": "report.pdf",
                        "source_path": "report.pdf",
                        "source_type": "application/pdf",
                        "ingestion_task_id": str(uuid4()),
                        "status": "completed",
                        "access_level": "internal",
                        "source_spans_count": 3,
                        "indexed_points_count": 3,
                        "created_at": now,
                        "warnings": [],
                        "error_message": None,
                    }
                ],
                "total": 1,
                "filters_applied": {},
            },
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = GatewayService(client, "http://orchestrator", 1024)
            result = await service.list_documents(
                "Bearer token",
                "request-1",
                catalog_filter="no_index",
            )
            assert result.total == 1
            assert result.items[0].document_id == "doc-1"

    asyncio.run(run())
    assert captured == {
        "method": "GET",
        "path": "/documents",
        "filter": "no_index",
    }
