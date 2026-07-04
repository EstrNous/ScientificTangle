import secrets

from fastapi import Header, Request

from shared.security import (
    AuthenticatedPrincipal,
    AuthenticationError,
    get_bearer_token,
)
from shared.web.errors import ServiceError

INTERNAL_SERVICE_TOKEN_HEADER = "X-Internal-Service-Token"


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


async def require_principal(
    request: Request,
    authorization: str | None = Header(default=None),
) -> AuthenticatedPrincipal:
    try:
        token = get_bearer_token(authorization)
        return await request.app.state.jwt_validator.validate(token)
    except AuthenticationError as error:
        raise ServiceError(401, "authentication_required", "Valid access token required") from error
