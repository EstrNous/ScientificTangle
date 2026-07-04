import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import httpx
from app.service.notification_service import TYPE_TITLES, NotificationService


class FakeNotification:
    def __init__(self) -> None:
        self.id = uuid4()
        self.type = "interest_match"
        self.message = "Совпадение с подпиской: никель, католит"
        self.reference_id = "nickel_report.pdf"
        self.reference_type = "document"
        self.is_read = False
        self.match_score = 0.86
        self.match_payload = {"reason": "offline_interest_match"}
        self.created_at = FakeNotification._now()

    @staticmethod
    def _now():
        from datetime import UTC, datetime

        return datetime(2026, 7, 4, 5, 10, tzinfo=UTC)


def test_notification_payload_maps_ui_fields() -> None:
    note = FakeNotification()
    payload = NotificationService._payload(note)

    assert payload.title == TYPE_TITLES["interest_match"]
    assert payload.reason == note.message
    assert payload.reference_id == "nickel_report.pdf"
    assert payload.reference_type == "document"
    assert payload.match_score == 0.86
    assert payload.match_reason == "offline_interest_match"
    assert payload.read is False
    assert payload.created_at.isoformat().startswith("2026-07-04")


class FakeInterest:
    def __init__(self, raw_text: str, entities: dict) -> None:
        self.raw_text = raw_text
        self.extracted_entities = entities
        self.updated_at = datetime(2026, 7, 4, 5, 15, tzinfo=UTC)


class FakeRepository:
    def __init__(self) -> None:
        self.saved_raw_text = ""
        self.saved_entities: dict | None = None

    async def update_user_interests(self, user_id, raw_text: str, entities: dict) -> FakeInterest:
        self.saved_raw_text = raw_text
        self.saved_entities = entities
        return FakeInterest(raw_text, entities)


def test_update_interests_uses_offline_model_extraction_when_items_empty() -> None:
    repository = FakeRepository()

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
            service = NotificationService(repository, client=client, model_url="http://model")
            principal = type("Principal", (), {"user_id": uuid4()})()
            payload = type("Payload", (), {"raw_text": "Интересует никель", "interests": []})()
            result = await service.update_interests(principal, payload)
            assert result.interests[0].label == "materials"
            assert result.warnings == ["deterministic_degraded"]

    asyncio.run(run())
    assert repository.saved_raw_text == "Интересует никель"
    assert repository.saved_entities == {
        "interests": [
            {"label": "materials", "weight": 0.7, "source_terms": ["никель"]}
        ],
        "warnings": ["deterministic_degraded"],
    }
