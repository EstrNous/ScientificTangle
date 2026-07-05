import secrets
from contextvars import ContextVar
from dataclasses import dataclass
from uuid import UUID

from fastapi import Header, Request

from shared.security import (
    AuthenticatedPrincipal,
    AuthenticationError,
    get_bearer_token,
)
from shared.web.errors import ServiceError

INTERNAL_SERVICE_TOKEN_HEADER = "X-Internal-Service-Token"
ACTING_USER_ID_HEADER = "X-Acting-User-Id"

_forwarded_auth: ContextVar[tuple[str, str] | None] = ContextVar("_forwarded_auth", default=None)


@dataclass(frozen=True, slots=True)
class ServiceCaller:
    user_id: UUID
    internal: bool


@dataclass(frozen=True, slots=True)
class AuthorizedContext:
    principal: AuthenticatedPrincipal
    authorization: str
    request_id: str


async def require_internal_service(
    request: Request,
    internal_service_token: str | None = Header(default=None, alias=INTERNAL_SERVICE_TOKEN_HEADER),
) -> None:
    configured_token = getattr(request.app.state, "internal_service_token", "")
    if not configured_token:
        raise ServiceError(503, "service_misconfigured", "Internal service authentication is not configured")
    if internal_service_token is None or not secrets.compare_digest(
        internal_service_token, configured_token
    ):
        raise ServiceError(401, "authentication_required", "Valid internal service token required")


async def require_service_or_principal(
    request: Request,
    internal_service_token: str | None = Header(default=None, alias=INTERNAL_SERVICE_TOKEN_HEADER),
    acting_user_id: str | None = Header(default=None, alias=ACTING_USER_ID_HEADER),
) -> ServiceCaller:
    configured_token = getattr(request.app.state, "internal_service_token", "")
    if (
        configured_token
        and internal_service_token is not None
        and secrets.compare_digest(internal_service_token, configured_token)
    ):
        if not acting_user_id:
            raise ServiceError(401, "authentication_required", "X-Acting-User-Id is required for internal calls")
        try:
            return ServiceCaller(user_id=UUID(acting_user_id), internal=True)
        except ValueError as error:
            raise ServiceError(422, "validation_error", "Invalid X-Acting-User-Id") from error
    principal = await require_principal(request)
    return ServiceCaller(user_id=principal.user_id, internal=False)


async def require_principal(request: Request) -> AuthenticatedPrincipal:
    try:
        authorization = request.headers.get("Authorization")
        token = get_bearer_token(authorization)
        resolved_authorization = authorization or ""
        request.state.authorization_header = resolved_authorization
        _forwarded_auth.set((resolved_authorization, request.state.request_id))
        return await request.app.state.jwt_validator.validate(token)
    except AuthenticationError as error:
        raise ServiceError(401, "authentication_required", "Valid access token required") from error


def authorization_header_from_request(request: Request) -> str:
    authorization = request.headers.get("Authorization")
    if not authorization:
        raise ServiceError(401, "authentication_required", "Valid access token required")
    return authorization


async def require_authorization_header(request: Request) -> str:
    return authorization_header_from_request(request)


async def get_http_request(request: Request) -> Request:
    return request


def forwarded_auth() -> tuple[str, str]:
    value = _forwarded_auth.get()
    if value is None or not value[0]:
        raise ServiceError(401, "authentication_required", "Valid access token required")
    return value


async def require_forwarded_auth(request: Request) -> AuthorizedContext:
    try:
        authorization = request.headers.get("Authorization")
        token = get_bearer_token(authorization)
        principal = await request.app.state.jwt_validator.validate(token)
        resolved_authorization = authorization or ""
        request.state.authorization_header = resolved_authorization
        _forwarded_auth.set((resolved_authorization, request.state.request_id))
        return AuthorizedContext(
            principal=principal,
            authorization=resolved_authorization,
            request_id=request.state.request_id,
        )
    except AuthenticationError as error:
        raise ServiceError(401, "authentication_required", "Valid access token required") from error


def get_request_id(request: Request) -> str:
    return request.state.request_id
