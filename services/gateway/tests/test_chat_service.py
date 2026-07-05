import asyncio
from uuid import uuid4

import pytest
from app.service.chat_service import ChatService, ChatServiceError
from app.service.service import GatewayServiceError

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


class FakeChatMessage:
    def __init__(self, message_id, session_id: str, role: str, content: str) -> None:
        self.id = message_id
        self.session_id = session_id
        self.role = role
        self.content = content


class FakeChatRepositoryForSend:
    def __init__(self) -> None:
        self.messages: list[FakeChatMessage] = []
        self.deleted_ids: list = []

    async def get_session(self, session_id, user_id):
        return object()

    async def save_message(self, session_id, role: str, content: str, query_run_id=None):
        message = FakeChatMessage(uuid4(), session_id, role, content)
        self.messages.append(message)
        return message

    async def delete_message(self, message_id) -> None:
        self.deleted_ids.append(message_id)
        self.messages = [message for message in self.messages if message.id != message_id]


class FailingGatewayService:
    async def run_query(self, payload, authorization, request_id):
        raise GatewayServiceError(503, "orchestrator_unavailable", "Orchestrator is unavailable")


class ExistingRunGatewayService:
    def __init__(self) -> None:
        self.run_query_calls = 0
        self.get_query_run_calls = 0

    async def run_query(self, payload, authorization, request_id):
        self.run_query_calls += 1
        return {"id": str(uuid4()), "answer": {"answer_text": "unexpected", "confidence": 0.5}}

    async def get_query_run(self, run_id, authorization, request_id):
        self.get_query_run_calls += 1
        return {
            "id": str(run_id),
            "answer": {"answer_text": "Сохранённый ответ", "confidence": 0.91},
            "evidence_bundle": {"evidence_items": []},
            "warnings": [],
        }


def test_send_message_rolls_back_user_message_when_query_fails() -> None:
    repository = FakeChatRepositoryForSend()
    service = ChatService(
        repository=repository,
        gateway_service=FailingGatewayService(),
        notification_service=None,
    )
    principal = AuthenticatedPrincipal(user_id=uuid4(), role=UserRole.ANALYST, token_id=uuid4())
    session_id = uuid4()

    with pytest.raises(ChatServiceError) as error:
        asyncio.run(
            service.send_message(
                principal,
                session_id,
                "nickel",
                "Bearer token",
                "req-1",
            )
        )

    assert error.value.status_code == 503
    assert error.value.code == "orchestrator_unavailable"
    assert repository.messages == []
    assert len(repository.deleted_ids) == 1


def test_send_message_uses_existing_query_run_without_run_query() -> None:
    repository = FakeChatRepositoryForSend()
    gateway = ExistingRunGatewayService()
    service = ChatService(
        repository=repository,
        gateway_service=gateway,
        notification_service=None,
    )
    principal = AuthenticatedPrincipal(user_id=uuid4(), role=UserRole.ANALYST, token_id=uuid4())
    session_id = uuid4()
    run_id = uuid4()

    payload = asyncio.run(
        service.send_message(
            principal,
            session_id,
            "nickel",
            "Bearer token",
            "req-1",
            query_run_id=run_id,
        )
    )

    assert gateway.run_query_calls == 0
    assert gateway.get_query_run_calls == 1
    assert payload["content"] == "Сохранённый ответ"
    assert len(repository.messages) == 2
