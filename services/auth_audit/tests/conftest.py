# ruff: noqa: E402
import asyncio
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

SERVICE_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = SERVICE_DIR.parents[1]
for import_root in (SERVICE_DIR, REPOSITORY_ROOT):
    import_root_text = str(import_root)
    if import_root_text not in sys.path:
        sys.path.insert(0, import_root_text)

from infra.postgres.auth_audit_db import (
    AuthRepository,
    IdentityConflictError,
    NewUserData,
    RefreshSessionData,
    Role,
    RotationResult,
    RotationStatus,
    User,
)

from app.api.factory import create_app
from app.core.config import Settings
from app.service.security import PasswordManager


@dataclass(slots=True)
class StoredRefreshSession:
    data: RefreshSessionData
    revoked_at: datetime | None = None
    replaced: bool = False


class FakeAuthRepository(AuthRepository):
    def __init__(self, users: list[User]) -> None:
        self.users = {user.id: user for user in users}
        self.sessions: dict[str, StoredRefreshSession] = {}
        self._lock = asyncio.Lock()

    async def get_user_by_username(self, username: str) -> User | None:
        return next((user for user in self.users.values() if user.username == username), None)

    async def get_user_by_identifier(self, identifier: str) -> User | None:
        username_result = await self.get_user_by_username(identifier)
        if username_result is not None:
            return username_result
        return next((user for user in self.users.values() if user.email == identifier), None)

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        return self.users.get(user_id)

    async def create_user(self, data: NewUserData) -> User:
        if any(
            user.username == data.username or user.email == data.email
            for user in self.users.values()
        ):
            raise IdentityConflictError
        user = User(
            id=uuid4(),
            username=data.username,
            email=data.email,
            password_hash=data.password_hash,
            role=data.role.value,
            is_active=True,
        )
        self.users[user.id] = user
        return user

    async def update_profile(
        self, user_id: UUID, username: str | None, email: str | None
    ) -> User | None:
        user = self.users.get(user_id)
        if user is None:
            return None
        if any(
            other.id != user_id
            and (
                username is not None
                and other.username == username
                or email is not None
                and other.email == email
            )
            for other in self.users.values()
        ):
            raise IdentityConflictError
        if username is not None:
            user.username = username
        if email is not None:
            user.email = email
        return user

    async def change_password(self, user_id: UUID, password_hash: str) -> User | None:
        user = self.users.get(user_id)
        if user is None:
            return None
        user.password_hash = password_hash
        await self.revoke_user_sessions(user_id)
        return user

    async def deactivate_user(self, user_id: UUID) -> User | None:
        user = self.users.get(user_id)
        if user is None:
            return None
        user.is_active = False
        user.deactivated_at = datetime.now(UTC)
        await self.revoke_user_sessions(user_id)
        return user

    async def list_users(self, offset: int, limit: int) -> tuple[list[User], int]:
        users = list(self.users.values())
        return users[offset : offset + limit], len(users)

    async def update_user(
        self, user_id: UUID, role: Role | None, is_active: bool | None
    ) -> User | None:
        user = self.users.get(user_id)
        if user is None:
            return None
        should_revoke = role is not None and role.value != user.role
        if role is not None:
            user.role = role.value
        if is_active is not None:
            user.is_active = is_active
            user.deactivated_at = None if is_active else datetime.now(UTC)
            should_revoke = should_revoke or not is_active
        if should_revoke:
            await self.revoke_user_sessions(user_id)
        return user

    async def create_refresh_session(self, data: RefreshSessionData) -> None:
        self.sessions[data.token_hash] = StoredRefreshSession(data)

    async def rotate_refresh_session(
        self, old_token_hash: str, replacement: RefreshSessionData
    ) -> RotationResult:
        async with self._lock:
            existing = self.sessions.get(old_token_hash)
            if existing is None or existing.data.expires_at <= datetime.now(UTC):
                return RotationResult(RotationStatus.INVALID)
            if existing.revoked_at is not None or existing.replaced:
                for session in self.sessions.values():
                    if session.data.family_id == existing.data.family_id:
                        session.revoked_at = datetime.now(UTC)
                return RotationResult(RotationStatus.REUSED, session_id=existing.data.id)
            user = self.users.get(existing.data.user_id)
            if user is None or not user.is_active:
                existing.revoked_at = datetime.now(UTC)
                return RotationResult(RotationStatus.INACTIVE_USER, session_id=existing.data.id)
            stored_replacement = RefreshSessionData(
                id=replacement.id,
                user_id=existing.data.user_id,
                family_id=existing.data.family_id,
                token_hash=replacement.token_hash,
                expires_at=replacement.expires_at,
                ip_address=replacement.ip_address,
                user_agent=replacement.user_agent,
            )
            self.sessions[replacement.token_hash] = StoredRefreshSession(stored_replacement)
            existing.revoked_at = datetime.now(UTC)
            existing.replaced = True
            return RotationResult(RotationStatus.SUCCESS, user=user, session_id=replacement.id)

    async def revoke_refresh_session(self, token_hash: str) -> bool:
        existing = self.sessions.get(token_hash)
        if existing is None:
            return False
        existing.revoked_at = datetime.now(UTC)
        return True

    async def revoke_user_sessions(self, user_id: UUID) -> int:
        count = 0
        for session in self.sessions.values():
            if session.data.user_id == user_id and session.revoked_at is None:
                session.revoked_at = datetime.now(UTC)
                count += 1
        return count


@pytest.fixture(scope="session")
def rsa_pems() -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private_key.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


@pytest.fixture
def settings(rsa_pems: tuple[str, str]) -> Settings:
    private_pem, public_pem = rsa_pems
    return Settings(
        jwt_private_key=SecretStr(private_pem),
        jwt_public_key=public_pem,
        refresh_cookie_secure=True,
        allowed_origins="https://ui.example.test",
    )


@pytest.fixture
def researcher() -> User:
    password_manager = PasswordManager()
    return User(
        id=uuid4(),
        username="researcher",
        email="researcher@example.com",
        password_hash=password_manager.hash("correct-password"),
        role=Role.RESEARCHER.value,
        is_active=True,
    )


@pytest.fixture
def inactive_user() -> User:
    password_manager = PasswordManager()
    return User(
        id=uuid4(),
        username="inactive",
        email=None,
        password_hash=password_manager.hash("correct-password"),
        role=Role.ANALYST.value,
        is_active=False,
    )


@pytest.fixture
def admin() -> User:
    password_manager = PasswordManager()
    return User(
        id=uuid4(),
        username="admin",
        email="admin@example.com",
        password_hash=password_manager.hash("AdminPassword1"),
        role=Role.ADMIN.value,
        is_active=True,
    )


@pytest.fixture
def repository(researcher: User, inactive_user: User, admin: User) -> FakeAuthRepository:
    return FakeAuthRepository([researcher, inactive_user, admin])


@pytest.fixture
async def client(settings: Settings, repository: FakeAuthRepository) -> AsyncClient:
    app = create_app(settings=settings, repository=repository)
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="https://testserver") as http_client:
        yield http_client
