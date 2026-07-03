from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RefreshSession, User


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

    async def get_user_by_id(self, user_id: UUID) -> User | None: ...

    async def create_refresh_session(self, data: RefreshSessionData) -> None: ...

    async def rotate_refresh_session(
        self, old_token_hash: str, replacement: RefreshSessionData
    ) -> RotationResult: ...

    async def revoke_refresh_session(self, token_hash: str) -> bool: ...


class SqlAlchemyAuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_by_username(self, username: str) -> User | None:
        result = await self._session.scalar(select(User).where(User.username == username))
        return result

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        return await self._session.get(User, user_id)

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

    async def _revoke_family(self, family_id: UUID, revoked_at: datetime) -> None:
        await self._session.execute(
            update(RefreshSession)
            .where(RefreshSession.family_id == family_id, RefreshSession.revoked_at.is_(None))
            .values(revoked_at=revoked_at)
        )

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
