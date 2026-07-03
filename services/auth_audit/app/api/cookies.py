from fastapi import Response
from infra.postgres.auth_audit_db import TokenResponse, UserResponse

from ..core.config import Settings
from ..service.service import TokenPairResult


def set_refresh_cookie(response: Response, settings: Settings, result: TokenPairResult) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=result.refresh_token,
        max_age=result.refresh_expires_in,
        path="/api/auth",
        secure=settings.refresh_cookie_secure,
        httponly=True,
        samesite="strict",
    )


def clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path="/api/auth",
        secure=settings.refresh_cookie_secure,
        httponly=True,
        samesite="strict",
    )


def token_response(result: TokenPairResult) -> TokenResponse:
    return TokenResponse(
        access_token=result.access_token,
        expires_in=result.expires_in,
        user=UserResponse.model_validate(result.user),
    )
