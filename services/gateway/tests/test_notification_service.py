import asyncio
from uuid import uuid4

import httpx
from app.service.notification_service import NotificationService


def test_proxy_list_notifications() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/notifications"
        assert request.headers["Authorization"] == "Bearer token"
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": str(uuid4()),
                        "title": "Новый документ по интересам",
                        "reason": "Совпадение",
                        "type": "interest_match",
                        "reference_id": "doc.pdf",
                        "reference_type": "document",
                        "read": False,
                        "match_score": 0.8,
                        "match_reason": "никель",
                        "created_at": "2026-07-04T05:10:00+00:00",
                    }
                ],
                "unread_count": 1,
            },
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = NotificationService(client, notification_url="http://notification")
            principal = type("Principal", (), {"user_id": uuid4()})()
            result = await service.list_notifications(
                principal,
                since=None,
                cursor=None,
                authorization="Bearer token",
                request_id="req-1",
            )
            assert len(result.items) == 1
            assert result.unread_count == 1

    asyncio.run(run())


def test_create_conflict_event_posts_internal_api() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["headers"] = dict(request.headers)
        import json as json_module
        captured["body"] = json_module.loads(request.content.decode())
        return httpx.Response(200, json={"id": str(uuid4()), "type": "conflict_detected"})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = NotificationService(
                client,
                notification_url="http://notification",
                internal_service_token="test-internal-token",
            )
            user_id = uuid4()
            await service.create_conflict_event(
                user_id=user_id,
                event_type="conflict_detected",
                message="test",
                reference_id="run-1",
                reference_type="query_run",
                match_score=1.0,
                match_reason="query_conflict_detected",
                match_payload={"conflict_count": 1},
                request_id="req-2",
            )
            assert captured["path"] == "/internal/v1/events"
            assert captured["headers"]["x-internal-service-token"] == "test-internal-token"
            assert captured["body"]["type"] == "conflict_detected"
            assert captured["body"]["user_id"] == str(user_id)

    asyncio.run(run())


def test_create_conflict_event_logs_failed_delivery() -> None:
    captured: list[str] = []

    class Logger:
        def warning(self, event, **kwargs):
            captured.append(event)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"code": "notification_unavailable", "message": "down"})

    async def run() -> None:
        import app.service.notification_service as notification_module

        original_logger = notification_module.logger
        notification_module.logger = Logger()
        try:
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                service = NotificationService(
                    client,
                    notification_url="http://notification",
                    internal_service_token="test-internal-token",
                )
                await service.create_conflict_event(
                    user_id=uuid4(),
                    event_type="conflict_detected",
                    message="test",
                    reference_id="run-1",
                    reference_type="query_run",
                    match_score=1.0,
                    match_reason="query_conflict_detected",
                    match_payload={"conflict_count": 1},
                    request_id="req-3",
                )
        finally:
            notification_module.logger = original_logger

    asyncio.run(run())
    assert captured == ["notification_event_delivery_failed"]
