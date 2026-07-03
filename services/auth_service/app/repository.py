from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RefreshSession, Role, User


class IdentityConflictError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class NewUserData:
    username: str
    email: str
    password_hash: str
    role: Role


@dataclass(frozen=True, slots=True)
class RefreshSessionData:
    id: UUID
    user_id: UUID
    family_id: UUID
    token_hash: str
    expires_at: datetime
    ip_address: str | None
    user_agent: str | None


class RotationStatus(StrEnum):
    SUCCESS = "success"
    INVALID = "invalid"
    REUSED = "reused"
    INACTIVE_USER = "inactive_user"


@dataclass(frozen=True, slots=True)
class RotationResult:
    status: RotationStatus
    user: User | None = None
    session_id: UUID | None = None


class AuthRepository(Protocol):
    async def get_user_by_username(self, username: str) -> User | None: ...

    async def get_user_by_identifier(self, identifier: str) -> User | None: ...

    async def get_user_by_id(self, user_id: UUID) -> User | None: ...

    async def create_user(self, data: NewUserData) -> User: ...

    async def update_profile(
        self, user_id: UUID, username: str | None, email: str | None
    ) -> User | None: ...

    async def change_password(self, user_id: UUID, password_hash: str) -> User | None: ...

    async def deactivate_user(self, user_id: UUID) -> User | None: ...

    async def list_users(self, offset: int, limit: int) -> tuple[list[User], int]: ...

    async def update_user(
        self, user_id: UUID, role: Role | None, is_active: bool | None
    ) -> User | None: ...

    async def create_refresh_session(self, data: RefreshSessionData) -> None: ...

    async def rotate_refresh_session(
        self, old_token_hash: str, replacement: RefreshSessionData
    ) -> RotationResult: ...

    async def revoke_refresh_session(self, token_hash: str) -> bool: ...

    async def revoke_user_sessions(self, user_id: UUID) -> int: ...


class SqlAlchemyAuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_by_username(self, username: str) -> User | None:
        result = await self._session.scalar(select(User).where(User.username == username))
        return result

    async def get_user_by_identifier(self, identifier: str) -> User | None:
        username_result: User | None = await self._session.scalar(
            select(User).where(User.username == identifier)
        )
        if username_result is not None:
            return username_result
        email_result: User | None = await self._session.scalar(
            select(User).where(User.email == identifier)
        )
        return email_result

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def create_user(self, data: NewUserData) -> User:
        user = User(
            username=data.username,
            email=data.email,
            password_hash=data.password_hash,
            role=data.role.value,
            is_active=True,
        )
        self._session.add(user)
        try:
            await self._session.commit()
        except IntegrityError as error:
            await self._session.rollback()
            raise IdentityConflictError from error
        await self._session.refresh(user)
        return user

    async def update_profile(
        self, user_id: UUID, username: str | None, email: str | None
    ) -> User | None:
        user = await self._session.get(User, user_id)
        if user is None:
            return None
        if username is not None:
            user.username = username
        if email is not None:
            user.email = email
        try:
            await self._session.commit()
        except IntegrityError as error:
            await self._session.rollback()
            raise IdentityConflictError from error
        await self._session.refresh(user)
        return user

    async def change_password(self, user_id: UUID, password_hash: str) -> User | None:
        user = await self._session.get(User, user_id)
        if user is None:
            return None
        user.password_hash = password_hash
        await self._revoke_user_sessions(user_id, datetime.now(UTC))
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def deactivate_user(self, user_id: UUID) -> User | None:
        user = await self._session.get(User, user_id)
        if user is None:
            return None
        now = datetime.now(UTC)
        user.is_active = False
        user.deactivated_at = now
        await self._revoke_user_sessions(user_id, now)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def list_users(self, offset: int, limit: int) -> tuple[list[User], int]:
        users = list(
            await self._session.scalars(
                select(User).order_by(User.created_at, User.id).offset(offset).limit(limit)
            )
        )
        total = await self._session.scalar(select(func.count()).select_from(User))
        return users, total or 0

    async def update_user(
        self, user_id: UUID, role: Role | None, is_active: bool | None
    ) -> User | None:
        user = await self._session.get(User, user_id)
        if user is None:
            return None
        now = datetime.now(UTC)
        should_revoke = role is not None and role.value != user.role
        if role is not None:
            user.role = role.value
        if is_active is not None:
            should_revoke = should_revoke or not is_active
            user.is_active = is_active
            user.deactivated_at = None if is_active else now
        if should_revoke:
            await self._revoke_user_sessions(user_id, now)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def create_refresh_session(self, data: RefreshSessionData) -> None:
        self._session.add(self._to_model(data))
        await self._session.commit()

    async def rotate_refresh_session(
        self, old_token_hash: str, replacement: RefreshSessionData
    ) -> RotationResult:
        now = datetime.now(UTC)
        existing = await self._session.scalar(
            select(RefreshSession)
            .where(RefreshSession.token_hash == old_token_hash)
            .with_for_update()
        )
        if existing is None:
            await self._session.rollback()
            return RotationResult(RotationStatus.INVALID)
        if existing.revoked_at is not None or existing.replaced_by_id is not None:
            await self._revoke_family(existing.family_id, now)
            await self._session.commit()
            return RotationResult(RotationStatus.REUSED, session_id=existing.id)
        if existing.expires_at <= now:
            existing.revoked_at = now
            await self._session.commit()
            return RotationResult(RotationStatus.INVALID, session_id=existing.id)
        user = await self._session.get(User, existing.user_id)
        if user is None or not user.is_active:
            existing.revoked_at = now
            await self._session.commit()
            return RotationResult(RotationStatus.INACTIVE_USER, session_id=existing.id)
        next_session = self._to_model(
            RefreshSessionData(
                id=replacement.id,
                user_id=existing.user_id,
                family_id=existing.family_id,
                token_hash=replacement.token_hash,
                expires_at=replacement.expires_at,
                ip_address=replacement.ip_address,
                user_agent=replacement.user_agent,
            )
        )
        self._session.add(next_session)
        await self._session.flush()
        existing.revoked_at = now
        existing.last_used_at = now
        existing.replaced_by_id = replacement.id
        await self._session.commit()
        return RotationResult(RotationStatus.SUCCESS, user=user, session_id=replacement.id)

    async def revoke_refresh_session(self, token_hash: str) -> bool:
        existing = await self._session.scalar(
            select(RefreshSession).where(RefreshSession.token_hash == token_hash).with_for_update()
        )
        if existing is None:
            await self._session.rollback()
            return False
        if existing.revoked_at is None:
            existing.revoked_at = datetime.now(UTC)
        await self._session.commit()
        return True

    async def revoke_user_sessions(self, user_id: UUID) -> int:
        result = await self._revoke_user_sessions(user_id, datetime.now(UTC))
        await self._session.commit()
        return result

    async def _revoke_family(self, family_id: UUID, revoked_at: datetime) -> None:
        await self._session.execute(
            update(RefreshSession)
            .where(RefreshSession.family_id == family_id, RefreshSession.revoked_at.is_(None))
            .values(revoked_at=revoked_at)
        )

    async def _revoke_user_sessions(self, user_id: UUID, revoked_at: datetime) -> int:
        result = await self._session.execute(
            update(RefreshSession)
            .where(RefreshSession.user_id == user_id, RefreshSession.revoked_at.is_(None))
            .values(revoked_at=revoked_at)
        )
        rowcount = getattr(result, "rowcount", 0)
        return int(rowcount or 0)

    @staticmethod
    def _to_model(data: RefreshSessionData) -> RefreshSession:
        return RefreshSession(
            id=data.id,
            user_id=data.user_id,
            family_id=data.family_id,
            token_hash=data.token_hash,
            expires_at=data.expires_at,
            ip_address=data.ip_address,
            user_agent=data.user_agent,
        )
