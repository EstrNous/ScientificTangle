import asyncio
from uuid import uuid4

import httpx
from app.service.analytics_service import AdminService


def test_list_audit_events_forwards_filters_to_orchestrator() -> None:
    captured: dict[str, object] = {}
    user_id = uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["query"] = str(request.url.query)
        captured["authorization"] = request.headers["Authorization"]
        return httpx.Response(200, json=[])

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = AdminService(client)
            result = await service.list_audit_events(
                "Bearer token",
                action="source_viewed",
                user_id=user_id,
                limit=25,
                offset=10,
            )
            assert result == []

    asyncio.run(run())

    assert captured["path"] == "/audit/events"
    assert captured["authorization"] == "Bearer token"
    assert "action=source_viewed" in str(captured["query"])
    assert f"user_id={user_id}" in str(captured["query"])
    assert "limit=25" in str(captured["query"])
    assert "offset=10" in str(captured["query"])
