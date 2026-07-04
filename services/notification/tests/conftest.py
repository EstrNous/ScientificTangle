# ruff: noqa: E402
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi import Request
from httpx import ASGITransport, AsyncClient

SERVICE_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = SERVICE_DIR.parents[1]
for import_root in (SERVICE_DIR, REPOSITORY_ROOT):
    import_root_text = str(import_root)
    if import_root_text not in sys.path:
        sys.path.insert(0, import_root_text)

from shared.contracts import UserRole
from shared.security import AuthenticatedPrincipal

from app.api.factory import create_app
from app.core import dependencies
from app.core.config import Settings
from app.service.matching_service import MatchingService
from app.service.notification_service import NotificationService


@pytest.fixture
def principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(user_id=uuid4(), role=UserRole.ANALYST, token_id=uuid4())


class FakeNotification:
    def __init__(self) -> None:
        self.id = uuid4()
        self.type = "interest_match"
        self.message = "Совпадение с подпиской: никель"
        self.reference_id = "nickel_report.pdf"
        self.reference_type = "document"
        self.is_read = False
        self.match_score = 0.86
        self.match_payload = {"reason": "offline_interest_match"}
        self.created_at = datetime(2026, 7, 4, 5, 10, tzinfo=UTC)


class FakeInterest:
    def __init__(self, raw_text: str, entities: dict) -> None:
        self.raw_text = raw_text
        self.extracted_entities = entities
        self.updated_at = datetime(2026, 7, 4, 5, 15, tzinfo=UTC)


class FakeRepository:
    def __init__(self) -> None:
        self.notifications: list[FakeNotification] = [FakeNotification()]
        self.interest: FakeInterest | None = None
        self.created_events: list = []

    async def get_user_notifications(self, user_id: UUID, limit: int = 20, since=None):
        if since is None:
            return self.notifications[:limit]
        return [note for note in self.notifications if note.created_at > since]

    async def list_user_notifications(
        self,
        user_id: UUID,
        *,
        since=None,
        cursor=None,
        limit: int = 20,
    ):
        notes = list(self.notifications)
        if cursor is not None:
            from infra.postgres.common.cursor import decode_cursor

            cursor_created_at, cursor_id = decode_cursor(cursor)
            notes = [
                note
                for note in notes
                if (note.created_at, note.id) < (cursor_created_at, cursor_id)
            ]
        elif since is not None:
            notes = [note for note in notes if note.created_at > since]
        notes.sort(key=lambda note: (note.created_at, note.id), reverse=True)
        page = notes[:limit]
        next_cursor = None
        if len(notes) > limit:
            from infra.postgres.common.cursor import encode_cursor

            last = page[-1]
            next_cursor = encode_cursor(last.created_at, last.id)
        return page, next_cursor

    async def count_unread(self, user_id: UUID) -> int:
        return sum(1 for note in self.notifications if not note.is_read)

    async def find_notification_by_reference(self, user_id: UUID, type: str, reference_id: str):
        for note in self.notifications:
            if note.type == type and note.reference_id == reference_id:
                return note
        return None

    async def mark_as_read(self, notification_id: UUID, user_id: UUID) -> bool:
        for note in self.notifications:
            if note.id == notification_id:
                note.is_read = True
                return True
        return False

    async def mark_all_as_read(self, user_id: UUID) -> int:
        count = sum(1 for note in self.notifications if not note.is_read)
        for note in self.notifications:
            note.is_read = True
        return count

    async def get_user_interests(self, user_id: UUID):
        return self.interest

    async def update_user_interests(self, user_id: UUID, raw_text: str, entities: dict):
        self.interest = FakeInterest(raw_text, entities)
        return self.interest

    async def create_notification(self, data):
        if data.reference_id:
            existing = await self.find_notification_by_reference(
                data.user_id,
                data.type,
                data.reference_id,
            )
            if existing is not None:
                return existing
        self.created_events.append(data)
        note = FakeNotification()
        note.type = data.type
        note.message = data.message
        note.reference_id = data.reference_id
        note.reference_type = data.reference_type
        note.match_score = data.match_score
        note.match_payload = {**(data.match_payload or {}), "reason": data.match_reason}
        self.notifications.append(note)
        return note


@pytest.fixture
def fake_repository() -> FakeRepository:
    return FakeRepository()


@pytest.fixture
def notification_service(fake_repository: FakeRepository) -> NotificationService:
    return NotificationService(fake_repository)


@pytest.fixture
def test_app(fake_repository: FakeRepository, principal: AuthenticatedPrincipal):
    from unittest.mock import AsyncMock

    app = create_app(
        Settings(
            service_name="notification-test",
            internal_service_token="test-internal-token",
            notification_redis_pubsub_enabled=False,
        )
    )
    app.state.internal_service_token = "test-internal-token"
    app.state.jwt_validator = AsyncMock()
    app.state.jwt_validator.validate = AsyncMock(return_value=principal)
    app.state.http_client = None

    async def override_get_notification_service(request: Request):
        return NotificationService(fake_repository)

    app.dependency_overrides[dependencies.get_notification_service] = override_get_notification_service

    class FakeWorkflowRepository:
        def __init__(self) -> None:
            self.created: list = []

        async def create_notification_with_match(self, user_id, *, type, message, reference_id, reference_type, match):
            note = FakeNotification()
            note.type = type
            note.message = message
            note.reference_id = reference_id
            note.reference_type = reference_type
            note.match_score = match.match_score
            note.match_payload = match.match_payload
            self.created.append(note)
            return note, None

    workflow_repository = FakeWorkflowRepository()

    async def override_get_matching_service(request: Request):
        return MatchingService(
            fake_repository,
            workflow_repository,
            client=request.app.state.http_client,
            model_url="http://model",
        )

    app.dependency_overrides[dependencies.get_matching_service] = override_get_matching_service
    app.state.test_workflow_repository = workflow_repository
    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={
            "Authorization": "Bearer test-token",
            "X-Internal-Service-Token": "test-internal-token",
        },
    ) as async_client:
        yield async_client
