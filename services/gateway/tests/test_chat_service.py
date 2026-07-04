import asyncio
from uuid import uuid4

from app.service.chat_service import ChatService

from infra.postgres.notification_db.repository import NotificationData
from shared.contracts import UserRole
from shared.security import AuthenticatedPrincipal


class FakeNotificationRepository:
    def __init__(self) -> None:
        self.created: NotificationData | None = None

    async def create_notification(self, data: NotificationData):
        self.created = data


def test_conflict_notification_uses_query_run_reference_and_match_payload() -> None:
    repository = FakeNotificationRepository()
    service = ChatService(repository=None, gateway_service=None, notification_repository=repository)
    principal = AuthenticatedPrincipal(user_id=uuid4(), role=UserRole.ANALYST, token_id=uuid4())
    run_id = uuid4()

    asyncio.run(
        service._maybe_notify_conflicts(
            principal,
            {
                "id": str(run_id),
                "evidence_bundle": {"conflicts": ["conflict-1", "conflict-2"]},
            },
        )
    )

    assert repository.created is not None
    assert repository.created.type == "conflict_detected"
    assert repository.created.reference_id == str(run_id)
    assert repository.created.reference_type == "query_run"
    assert repository.created.match_score == 1.0
    assert repository.created.match_reason == "query_conflict_detected"
    assert repository.created.match_payload == {
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
