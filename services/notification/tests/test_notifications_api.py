import pytest
from datetime import UTC, datetime
from uuid import uuid4

from infra.postgres.notification_db.repository import NotificationData
from infra.postgres.common.cursor import encode_cursor

from tests.conftest import FakeNotification

@pytest.mark.asyncio
async def test_list_notifications(client, fake_repository) -> None:
    response = await client.get("/notifications")
    assert response.status_code == 200
    payload = response.json()
    assert payload["unread_count"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["type"] == "interest_match"


@pytest.mark.asyncio
async def test_list_notifications_since_filters_items(client, fake_repository) -> None:
    response = await client.get("/notifications", params={"since": "2026-07-04T06:00:00+00:00"})
    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.asyncio
async def test_mark_notification_read(client, fake_repository) -> None:
    note_id = fake_repository.notifications[0].id
    response = await client.post(f"/notifications/{note_id}/read")
    assert response.status_code == 200
    assert response.json()["updated_count"] == 1
    assert fake_repository.notifications[0].is_read is True


@pytest.mark.asyncio
async def test_mark_all_notifications_read(client, fake_repository) -> None:
    response = await client.post("/notifications/read-all")
    assert response.status_code == 200
    assert response.json()["updated_count"] == 1
    assert fake_repository.notifications[0].is_read is True


@pytest.mark.asyncio
async def test_create_event_is_idempotent(fake_repository, notification_service, principal) -> None:
    data = NotificationData(
        user_id=principal.user_id,
        type="ingestion_complete",
        message="Обработано документов: 1",
        reference_id="task-1",
        reference_type="ingestion_task",
    )
    first = await notification_service.create_event(data)
    second = await notification_service.create_event(data)
    assert first.id == second.id
    assert len(fake_repository.created_events) == 1


@pytest.mark.asyncio
async def test_list_notifications_cursor_returns_next_page(client, fake_repository) -> None:
    older = FakeNotification()
    older.created_at = datetime(2026, 7, 4, 4, 0, tzinfo=UTC)
    newer = FakeNotification()
    newer.id = uuid4()
    newer.created_at = datetime(2026, 7, 4, 6, 0, tzinfo=UTC)
    fake_repository.notifications = [older, newer]

    first = await client.get("/notifications")
    assert first.status_code == 200
    first_payload = first.json()
    assert len(first_payload["items"]) == 2

    cursor = encode_cursor(newer.created_at, newer.id)
    second = await client.get("/notifications", params={"cursor": cursor})
    assert second.status_code == 200
    second_payload = second.json()
    assert len(second_payload["items"]) == 1
    assert second_payload["items"][0]["id"] == str(older.id)
    assert second_payload["next_cursor"] is None


@pytest.mark.asyncio
async def test_mark_notification_read_not_found(client, fake_repository) -> None:
    response = await client.post(f"/notifications/{uuid4()}/read")
    assert response.status_code == 404
    assert response.json()["code"] == "notification_not_found"