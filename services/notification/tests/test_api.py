import asyncio
from uuid import uuid4

import httpx
import pytest

from infra.postgres.notification_db.repository import NotificationData
from shared.contracts import UserInterestsUpdatePayload

from app.service.notification_service import TYPE_TITLES, NotificationService


def test_notification_payload_maps_ui_fields(notification_service: NotificationService, fake_repository) -> None:
    note = fake_repository.notifications[0]
    payload = NotificationService._payload(note)

    assert payload.title == TYPE_TITLES["interest_match"]
    assert payload.reason == note.message
    assert payload.reference_id == "nickel_report.pdf"
    assert payload.match_score == 0.86
    assert payload.match_reason == "offline_interest_match"


@pytest.mark.asyncio
async def test_list_notifications(notification_service: NotificationService, principal) -> None:
    result = await notification_service.list_notifications(principal)
    assert len(result.items) == 1
    assert result.unread_count == 1


@pytest.mark.asyncio
async def test_create_event(notification_service: NotificationService, fake_repository, principal) -> None:
    payload = await notification_service.create_event(
        NotificationData(
            user_id=principal.user_id,
            type="conflict_detected",
            message="test conflict",
            reference_id="run-1",
            reference_type="query_run",
            match_score=1.0,
            match_reason="query_conflict_detected",
            match_payload={"conflict_count": 1},
        )
    )
    assert payload.type == "conflict_detected"
    assert len(fake_repository.created_events) == 1


def test_update_interests_uses_model_extraction(fake_repository) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/interests/extract"
        return httpx.Response(
            200,
            json={
                "interests": [
                    {"label": "materials", "weight": 0.7, "source_terms": ["никель"]}
                ],
                "warnings": ["deterministic_degraded"],
            },
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = NotificationService(fake_repository, client=client, model_url="http://model")
            principal = type("Principal", (), {"user_id": uuid4()})()
            payload = UserInterestsUpdatePayload(raw_text="Интересует никель", interests=[])
            result = await service.update_interests(principal, payload)
            assert result.interests[0].label == "materials"
            assert result.warnings == ["deterministic_degraded"]

    asyncio.run(run())
    assert fake_repository.interest is not None
    assert fake_repository.interest.raw_text == "Интересует никель"
