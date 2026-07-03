from fastapi import Header, Request

from shared.security import (
    AuthenticatedPrincipal,
    AuthenticationError,
    get_bearer_token,
)
from shared.web.errors import ServiceError


async def require_principal(
    request: Request,
    authorization: str | None = Header(default=None),
) -> AuthenticatedPrincipal:
    try:
        token = get_bearer_token(authorization)
        return await request.app.state.jwt_validator.validate(token)
    except AuthenticationError as error:
        raise ServiceError(401, "authentication_required", "Valid access token required") from error
