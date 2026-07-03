from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.audit import AuthAuditEvent, AuthAuditSink
from app.models import Role, User
from app.repository import (
    AuthRepository,
    RefreshSessionData,
    RotationStatus,
)
from app.security import (
    InvalidAccessTokenError,
    PasswordManager,
    TokenManager,
    create_refresh_token,
    hash_refresh_token,
)


class AuthenticationError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class RequestContext:
    request_id: str
    ip_address: str | None
    user_agent: str | None


@dataclass(frozen=True, slots=True)
class TokenPairResult:
    access_token: str
    expires_in: int
    refresh_token: str
    refresh_expires_in: int
    user: User


class AuthService:
    def __init__(
        self,
        repository: AuthRepository,
        password_manager: PasswordManager,
        token_manager: TokenManager,
        audit_sink: AuthAuditSink,
        refresh_token_days: int,
    ) -> None:
        self._repository = repository
        self._password_manager = password_manager
        self._token_manager = token_manager
        self._audit_sink = audit_sink
        self._refresh_token_days = refresh_token_days
        self._dummy_password_hash = self._password_manager.dummy_hash

    async def login(self, username: str, password: str, context: RequestContext) -> TokenPairResult:
        normalized_username = username.strip().casefold()
        user = await self._repository.get_user_by_username(normalized_username)
        password_hash = user.password_hash if user is not None else self._dummy_password_hash
        password_valid = self._password_manager.verify(password, password_hash)
        if user is None or not password_valid or not user.is_active:
            await self._record(
                "authentication", "denied", context, user=user, username=normalized_username
            )
            raise AuthenticationError
        result = await self._new_session(user, uuid4(), context)
        await self._record("authentication", "success", context, user=user)
        return result

    async def refresh(self, refresh_token: str, context: RequestContext) -> TokenPairResult:
        raw_replacement = create_refresh_token()
        replacement = self._session_data(
            user_id=UUID(int=0),
            family_id=UUID(int=0),
            raw_token=raw_replacement,
            context=context,
        )
        result = await self._repository.rotate_refresh_session(
            hash_refresh_token(refresh_token), replacement
        )
        if result.status == RotationStatus.REUSED:
            await self._record(
                "refresh_token_reuse", "denied", context, session_id=result.session_id
            )
            raise AuthenticationError
        if result.status != RotationStatus.SUCCESS or result.user is None:
            await self._record("token_refresh", "denied", context, session_id=result.session_id)
            raise AuthenticationError
        access_token, expires_in = self._token_manager.create_access_token(
            result.user.id, Role(result.user.role)
        )
        await self._record(
            "token_refresh", "success", context, user=result.user, session_id=result.session_id
        )
        return TokenPairResult(
            access_token=access_token,
            expires_in=expires_in,
            refresh_token=raw_replacement,
            refresh_expires_in=self._refresh_token_days * 86400,
            user=result.user,
        )

    async def logout(self, refresh_token: str, context: RequestContext) -> None:
        revoked = await self._repository.revoke_refresh_session(hash_refresh_token(refresh_token))
        await self._record("logout", "success" if revoked else "ignored", context)

    async def authenticate_access_token(self, token: str, context: RequestContext) -> User:
        try:
            claims = self._token_manager.decode_access_token(token)
        except InvalidAccessTokenError as error:
            await self._record("access_token", "denied", context)
            raise AuthenticationError from error
        user = await self._repository.get_user_by_id(claims.sub)
        if user is None or not user.is_active or user.role != claims.role.value:
            await self._record("access_token", "denied", context, user=user)
            raise AuthenticationError
        return user

    async def record_access_denied(self, user: User, context: RequestContext) -> None:
        await self._record("authorization", "denied", context, user=user)

    async def _new_session(
        self, user: User, family_id: UUID, context: RequestContext
    ) -> TokenPairResult:
        refresh_token = create_refresh_token()
        data = self._session_data(user.id, family_id, refresh_token, context)
        await self._repository.create_refresh_session(data)
        access_token, expires_in = self._token_manager.create_access_token(user.id, Role(user.role))
        return TokenPairResult(
            access_token=access_token,
            expires_in=expires_in,
            refresh_token=refresh_token,
            refresh_expires_in=self._refresh_token_days * 86400,
            user=user,
        )

    def _session_data(
        self,
        user_id: UUID,
        family_id: UUID,
        raw_token: str,
        context: RequestContext,
    ) -> RefreshSessionData:
        return RefreshSessionData(
            id=uuid4(),
            user_id=user_id,
            family_id=family_id,
            token_hash=hash_refresh_token(raw_token),
            expires_at=datetime.now(UTC) + timedelta(days=self._refresh_token_days),
            ip_address=context.ip_address,
            user_agent=context.user_agent,
        )

    async def _record(
        self,
        action: str,
        status: str,
        context: RequestContext,
        user: User | None = None,
        username: str | None = None,
        session_id: UUID | None = None,
    ) -> None:
        await self._audit_sink.record(
            AuthAuditEvent(
                action=action,
                status=status,
                occurred_at=datetime.now(UTC),
                user_id=user.id if user is not None else None,
                username=user.username if user is not None else username,
                session_id=session_id,
                request_id=context.request_id,
                ip_address=context.ip_address,
            )
        )
