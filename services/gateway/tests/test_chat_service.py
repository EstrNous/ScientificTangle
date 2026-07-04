import asyncio
from uuid import uuid4

from app.service.chat_service import ChatService

from shared.contracts import UserRole
from shared.security import AuthenticatedPrincipal


class FakeNotificationService:
    def __init__(self) -> None:
        self.last_event: dict | None = None

    async def create_conflict_event(self, **kwargs) -> None:
        self.last_event = kwargs


def test_conflict_notification_uses_query_run_reference_and_match_payload() -> None:
    notification_service = FakeNotificationService()
    service = ChatService(repository=None, gateway_service=None, notification_service=notification_service)
    principal = AuthenticatedPrincipal(user_id=uuid4(), role=UserRole.ANALYST, token_id=uuid4())
    run_id = uuid4()

    asyncio.run(
        service._maybe_notify_conflicts(
            principal,
            {
                "id": str(run_id),
                "evidence_bundle": {"conflicts": ["conflict-1", "conflict-2"]},
            },
            "req-1",
        )
    )

    assert notification_service.last_event is not None
    assert notification_service.last_event["event_type"] == "conflict_detected"
    assert notification_service.last_event["reference_id"] == str(run_id)
    assert notification_service.last_event["reference_type"] == "query_run"
    assert notification_service.last_event["match_score"] == 1.0
    assert notification_service.last_event["match_reason"] == "query_conflict_detected"
    assert notification_service.last_event["match_payload"] == {
        "conflict_count": 2,
        "query_run_id": str(run_id),
    }


def test_map_query_response_builds_ui_payload() -> None:
    principal = AuthenticatedPrincipal(user_id=uuid4(), role=UserRole.ANALYST, token_id=uuid4())
    payload = ChatService._map_query_response(
        {
            "answer": {
                "answer_text": "Тестовый ответ",
                "confidence": 0.77,
            },
            "query_ir": {"entities": ["никель", "католит"]},
            "evidence_bundle": {
                "evidence_items": [
                    {
                        "source_span": {
                            "document_id": "nickel_report.pdf",
                            "page": 12,
                            "text": "скорость потока католита составляет 2–4 м/ч",
                        }
                    }
                ]
            },
            "warnings": ["demo_warning"],
        },
        principal,
    )

    assert payload["content"] == "Тестовый ответ"
    assert payload["confidence"] == 0.77
    assert payload["sources"][0]["title"] == "nickel_report.pdf"
    assert payload["evidence_table"]["rows"][0][2] == "nickel_report.pdf"
    assert payload["expanded_synonyms"] == ["никель", "католит"]
