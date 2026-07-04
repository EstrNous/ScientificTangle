# ruff: noqa: E402
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

SERVICE_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = SERVICE_DIR.parents[1]
for import_root in (SERVICE_DIR, REPOSITORY_ROOT):
    import_root_text = str(import_root)
    if import_root_text not in sys.path:
        sys.path.insert(0, import_root_text)

from app.core import dependencies
from app.core.config import Settings
from app.main import create_app
from app.service.chat_service import ChatService

from shared.contracts import UserRole
from shared.security import AuthenticatedPrincipal


@dataclass
class FakeChatSession:
    id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class FakeChatRepository:
    def __init__(self) -> None:
        self.sessions: list[FakeChatSession] = []

    async def list_sessions(self, user_id: UUID) -> list[FakeChatSession]:
        return sorted(
            [session for session in self.sessions if session.user_id == user_id],
            key=lambda session: session.updated_at,
            reverse=True,
        )

    async def get_session(self, session_id: UUID, user_id: UUID) -> FakeChatSession | None:
        for session in self.sessions:
            if session.id == session_id and session.user_id == user_id:
                return session
        return None

    async def create_session(self, user_id: UUID, title: str) -> FakeChatSession:
        now = datetime.now(UTC)
        session = FakeChatSession(
            id=uuid4(),
            user_id=user_id,
            title=title,
            created_at=now,
            updated_at=now,
        )
        self.sessions.append(session)
        return session

    async def delete_session(self, session_id: UUID, user_id: UUID) -> bool:
        session = await self.get_session(session_id, user_id)
        if session is None:
            return False
        self.sessions.remove(session)
        return True

    async def get_messages(self, session_id: UUID) -> list:
        return []

    async def save_message(self, session_id: UUID, role: str, content: str, query_run_id: UUID | None = None):
        raise NotImplementedError


@pytest.fixture
def principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(user_id=uuid4(), role=UserRole.RESEARCHER, token_id=uuid4())


@pytest.fixture
def fake_chat_repository() -> FakeChatRepository:
    return FakeChatRepository()


@pytest.fixture
def chat_test_app(fake_chat_repository: FakeChatRepository, principal: AuthenticatedPrincipal):
    from unittest.mock import AsyncMock

    @asynccontextmanager
    async def test_lifespan(app):
        http_client = httpx.AsyncClient()
        app.state.session_factory = None
        app.state.http_client = http_client
        app.state.gateway_service = AsyncMock()
        app.state.notification_service = AsyncMock()
        app.state.jwt_validator = AsyncMock()
        app.state.jwt_validator.validate = AsyncMock(return_value=principal)
        yield
        await http_client.aclose()

    app = create_app(
        Settings(
            service_name="gateway-test",
            rate_limit_enabled=False,
            rate_limit_use_redis=False,
        )
    )
    app.router.lifespan_context = test_lifespan

    async def override_get_chat_service(request):
        return ChatService(
            repository=fake_chat_repository,
            gateway_service=request.app.state.gateway_service,
            notification_service=request.app.state.notification_service,
        )

    app.dependency_overrides[dependencies.get_chat_service] = override_get_chat_service
    return app


@pytest.fixture
async def chat_client(chat_test_app):
    transport = ASGITransport(app=chat_test_app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as async_client:
        yield async_client
