import asyncio
from uuid import uuid4

import httpx
from app.service.analytics_service import AdminService

from shared.contracts import AccessPolicy


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


def test_patch_policy_proxies_to_orchestrator() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["authorization"] = request.headers["Authorization"]
        captured["body"] = request.read()
        return httpx.Response(
            200,
            json={
                "document_id": "doc-1",
                "access_policy": {"level": "restricted", "allowed_roles": ["admin"]},
            },
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = AdminService(client)
            result = await service.patch_policy(
                "doc-1",
                AccessPolicy(level="restricted", allowed_roles=["admin"]),
                "Bearer token",
            )
            assert result["access_policy"]["level"] == "restricted"

    asyncio.run(run())
    assert captured["path"] == "/admin/policies/doc-1"
    assert captured["authorization"] == "Bearer token"
