import json
from uuid import uuid4

import pytest

from infra.postgres.notification_db.repository import NotificationData
from tests.conftest import FakeRepository


@pytest.mark.asyncio
async def test_delivery_handler_creates_event(notification_service, fake_repository, principal) -> None:
    from app.service.delivery_handler import NotificationDeliveryHandler
    from app.core.config import Settings

    class SessionFactory:
        def __call__(self):
            return self

        async def __aenter__(self):
            return None

        async def __aexit__(self, exc_type, exc, tb):
            return False

    handler = NotificationDeliveryHandler(
        SessionFactory(),
        None,
        Settings(notification_redis_pubsub_enabled=False),
    )

    async def override_create_event(body):
        return await notification_service.create_event(
            NotificationData(
                user_id=principal.user_id,
                type=str(body["type"]),
                message=str(body["message"]),
                reference_id=body.get("reference_id"),
                reference_type=body.get("reference_type"),
            )
        )

    handler._create_event = override_create_event
    message = json.dumps(
        {
            "kind": "event",
            "request_id": "req-1",
            "payload": {
                "user_id": str(principal.user_id),
                "type": "ingestion_complete",
                "message": "Обработано документов: 1",
                "reference_id": "task-1",
                "reference_type": "ingestion_task",
            },
        }
    )
    created = await handler.handle_message(message)
    assert len(created) == 1
    assert created[0].type == "ingestion_complete"
