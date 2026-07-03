from fastapi import APIRouter, Depends, Request, Response, status
from typing import Annotated

from infra.postgres.auth_audit_db import (
    IdentityConflictError,
    LoginRequest,
    PasswordChangeRequest,
    PasswordConfirmationRequest,
    ProfileUpdateRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from ..core.config import Settings
from ..core.dependencies import (
    get_auth_service,
    get_current_user,
    get_request_context,
)
from infra.postgres.auth_audit_db import User
from ..service.service import AuthenticationError, AuthService, RequestContext
from .cookies import clear_refresh_cookie, set_refresh_cookie, token_response
from shared.web import ServiceError

router = APIRouter()

AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
RequestContextDependency = Annotated[RequestContext, Depends(get_request_context)]
CurrentUserDependency = Annotated[User, Depends(get_current_user)]


def validate_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    settings: Settings = request.app.state.settings
    if origin is not None and origin not in settings.origin_allowlist:
        raise ServiceError(403, "forbidden", "Access is denied")


@router.post("/api/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    service: AuthServiceDependency,
    context: RequestContextDependency,
) -> TokenResponse:
    validate_origin(request)
    try:
        result = await service.register(
            payload.username, str(payload.email), payload.password, context
        )
    except IdentityConflictError as error:
        raise ServiceError(409, "identity_already_exists", "Identity already exists") from error
    set_refresh_cookie(response, request.app.state.settings, result)
    return token_response(result)


@router.post("/api/auth/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    service: AuthServiceDependency,
    context: RequestContextDependency,
) -> TokenResponse:
    validate_origin(request)
    try:
        result = await service.login(payload.identifier, payload.password, context)
    except AuthenticationError as error:
        raise ServiceError(401, "unauthorized", "Authentication is required") from error
    set_refresh_cookie(response, request.app.state.settings, result)
    return token_response(result)


@router.post("/api/auth/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    service: AuthServiceDependency,
    context: RequestContextDependency,
) -> TokenResponse:
    validate_origin(request)
    settings: Settings = request.app.state.settings
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if refresh_token is None:
        raise ServiceError(401, "unauthorized", "Authentication is required")
    try:
        result = await service.refresh(refresh_token, context)
    except AuthenticationError as error:
        clear_refresh_cookie(response, settings)
        raise ServiceError(401, "unauthorized", "Authentication is required") from error
    set_refresh_cookie(response, settings, result)
    return token_response(result)


@router.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    service: AuthServiceDependency,
    context: RequestContextDependency,
) -> None:
    validate_origin(request)
    settings: Settings = request.app.state.settings
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if refresh_token is not None:
        await service.logout(refresh_token, context)
    clear_refresh_cookie(response, settings)


@router.get("/api/auth/me", response_model=UserResponse)
async def me(user: CurrentUserDependency) -> UserResponse:
    return UserResponse.model_validate(user)


@router.patch("/api/auth/me", response_model=UserResponse)
async def update_me(
    payload: ProfileUpdateRequest,
    request: Request,
    user: CurrentUserDependency,
    service: AuthServiceDependency,
    context: RequestContextDependency,
) -> UserResponse:
    validate_origin(request)
    try:
        updated = await service.update_profile(
            user,
            payload.current_password,
            payload.username,
            str(payload.email) if payload.email is not None else None,
            context,
        )
    except AuthenticationError as error:
        raise ServiceError(401, "unauthorized", "Authentication is required") from error
    except IdentityConflictError as error:
        raise ServiceError(409, "identity_already_exists", "Identity already exists") from error
    return UserResponse.model_validate(updated)


@router.post("/api/auth/change-password", response_model=TokenResponse)
async def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    response: Response,
    user: CurrentUserDependency,
    service: AuthServiceDependency,
    context: RequestContextDependency,
) -> TokenResponse:
    validate_origin(request)
    try:
        result = await service.change_password(
            user, payload.current_password, payload.new_password, context
        )
    except AuthenticationError as error:
        raise ServiceError(401, "unauthorized", "Authentication is required") from error
    set_refresh_cookie(response, request.app.state.settings, result)
    return token_response(result)


@router.post("/api/auth/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    request: Request,
    response: Response,
    user: CurrentUserDependency,
    service: AuthServiceDependency,
    context: RequestContextDependency,
) -> None:
    validate_origin(request)
    await service.logout_all(user, context)
    clear_refresh_cookie(response, request.app.state.settings)


@router.delete("/api/auth/me", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_me(
    payload: PasswordConfirmationRequest,
    request: Request,
    response: Response,
    user: CurrentUserDependency,
    service: AuthServiceDependency,
    context: RequestContextDependency,
) -> None:
    validate_origin(request)
    try:
        await service.deactivate(user, payload.current_password, context)
    except AuthenticationError as error:
        raise ServiceError(401, "unauthorized", "Authentication is required") from error
    clear_refresh_cookie(response, request.app.state.settings)
