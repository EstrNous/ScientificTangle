from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from infra.postgres.auth_audit_db import AuthRepository, Role, SqlAlchemyAuthRepository, User
from app.service.service import AuthenticationError, AuthService, RequestContext

bearer_scheme = HTTPBearer(auto_error=False)


async def get_repository(request: Request) -> AsyncIterator[AuthRepository]:
    fixed_repository = request.app.state.repository
    if fixed_repository is not None:
        yield fixed_repository
        return

    async with request.app.state.session_factory() as session:
        yield SqlAlchemyAuthRepository(session)


def get_request_context(request: Request) -> RequestContext:
    client_host = request.client.host if request.client is not None else None
    return RequestContext(
        request_id=request.state.request_id,
        ip_address=client_host,
        user_agent=request.headers.get("user-agent"),
    )


def get_auth_service(
    request: Request,
    repository: Annotated[AuthRepository, Depends(get_repository)],
) -> AuthService:
    return AuthService(
        repository=repository,
        password_manager=request.app.state.password_manager,
        token_manager=request.app.state.token_manager,
        audit_sink=request.app.state.audit_sink,
        refresh_token_days=request.app.state.settings.refresh_token_days,
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    service: Annotated[AuthService, Depends(get_auth_service)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> User:
    from app.api.web import UnauthorizedError

    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise UnauthorizedError

    try:
        return await service.authenticate_access_token(credentials.credentials, context)
    except AuthenticationError as error:
        raise UnauthorizedError from error


def require_roles(
    *allowed_roles: Role,
) -> Callable[..., Coroutine[Any, Any, User]]:
    async def dependency(
        user: Annotated[User, Depends(get_current_user)],
        service: Annotated[AuthService, Depends(get_auth_service)],
        context: Annotated[RequestContext, Depends(get_request_context)],
    ) -> User:
        from app.api.web import ForbiddenError

        if Role(user.role) not in allowed_roles:
            await service.record_access_denied(user, context)
            raise ForbiddenError

        return user

    return dependency
