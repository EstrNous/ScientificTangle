from __future__ import annotations

import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any, cast
from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, generate_latest
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import RequestResponseEndpoint

from app.audit import AuthAuditSink, NullAuthAuditSink
from app.config import Settings
from app.database import create_database
from app.dependencies import (
    get_auth_service,
    get_current_user,
    get_request_context,
)
from app.models import User
from app.repository import AuthRepository
from app.schemas import (
    ErrorDetails,
    ErrorResponse,
    HealthResponse,
    LoginRequest,
    TokenResponse,
    UserResponse,
)
from app.security import KeyStore, PasswordManager, TokenManager
from app.service import AuthenticationError, AuthService, RequestContext, TokenPairResult

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
RequestContextDependency = Annotated[RequestContext, Depends(get_request_context)]
CurrentUserDependency = Annotated[User, Depends(get_current_user)]


class UnauthorizedError(Exception):
    pass


class ForbiddenError(Exception):
    pass


def create_app(
    settings: Settings | None = None,
    repository: AuthRepository | None = None,
    audit_sink: AuthAuditSink | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings()
    key_store = KeyStore(resolved_settings)
    password_manager = PasswordManager()
    token_manager = TokenManager(resolved_settings, key_store)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if repository is None:
            engine, session_factory = create_database(resolved_settings.database_url)
            app.state.engine = engine
            app.state.session_factory = session_factory
        yield
        if repository is None:
            await app.state.engine.dispose()

    app = FastAPI(
        title="ScientificTangle Auth Service",
        version="0.1.0",
        lifespan=lifespan,
        responses={
            401: {"model": ErrorResponse},
            403: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
        },
    )
    app.state.settings = resolved_settings
    app.state.repository = repository
    app.state.audit_sink = audit_sink or NullAuthAuditSink()
    app.state.key_store = key_store
    app.state.password_manager = password_manager
    app.state.token_manager = token_manager
    registry = CollectorRegistry()
    request_counter = Counter(
        "auth_http_requests_total",
        "Количество HTTP-запросов к сервису аутентификации",
        ["method", "path", "status"],
        registry=registry,
    )
    app.state.metrics_registry = registry

    @app.middleware("http")
    async def request_metadata(request: Request, call_next: RequestResponseEndpoint) -> Response:
        supplied_request_id = request.headers.get("x-request-id", "")
        request.state.request_id = (
            supplied_request_id
            if REQUEST_ID_PATTERN.fullmatch(supplied_request_id)
            else str(uuid4())
        )
        response = await call_next(request)
        response.headers["x-request-id"] = request.state.request_id
        route = request.scope.get("route")
        path = getattr(route, "path", "unmatched")
        request_counter.labels(request.method, path, str(response.status_code)).inc()
        return response

    register_error_handlers(app)
    app.include_router(build_router())
    return app


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(UnauthorizedError)
    async def unauthorized_handler(request: Request, error: UnauthorizedError) -> JSONResponse:
        return error_response(request, "UNAUTHORIZED", "Authentication is required", 401)

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(request: Request, error: ForbiddenError) -> JSONResponse:
        return error_response(request, "FORBIDDEN", "Access is denied", 403)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, error: RequestValidationError) -> JSONResponse:
        return error_response(request, "VALIDATION_ERROR", "Request validation failed", 422)

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(request: Request, error: StarletteHTTPException) -> JSONResponse:
        return error_response(request, "HTTP_ERROR", "Request failed", error.status_code)

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, error: Exception) -> JSONResponse:
        return error_response(request, "INTERNAL_ERROR", "Internal server error", 500)


def build_router() -> APIRouter:
    router = APIRouter()

    @router.post("/api/auth/login", response_model=TokenResponse)
    async def login(
        payload: LoginRequest,
        request: Request,
        response: Response,
        service: AuthServiceDependency,
        context: RequestContextDependency,
    ) -> TokenResponse:
        try:
            result = await service.login(payload.username, payload.password, context)
        except AuthenticationError as error:
            raise UnauthorizedError from error
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
            raise UnauthorizedError
        try:
            result = await service.refresh(refresh_token, context)
        except AuthenticationError as error:
            clear_refresh_cookie(response, settings)
            raise UnauthorizedError from error
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

    @router.get("/.well-known/jwks.json")
    async def jwks(request: Request) -> dict[str, list[dict[str, Any]]]:
        key_store = cast(KeyStore, request.app.state.key_store)
        return key_store.jwks()

    @router.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse()

    @router.get("/ready", response_model=HealthResponse)
    async def ready(request: Request) -> Response:
        try:
            request.app.state.key_store.validate_pair()
            if request.app.state.repository is None:
                async with request.app.state.session_factory() as session:
                    await session.execute(text("SELECT 1"))
        except Exception:
            return JSONResponse(status_code=503, content={"status": "unavailable"})
        return JSONResponse(content=HealthResponse().model_dump())

    @router.get("/metrics", response_class=PlainTextResponse)
    async def metrics(request: Request) -> PlainTextResponse:
        content = generate_latest(request.app.state.metrics_registry)
        return PlainTextResponse(content=content, media_type=CONTENT_TYPE_LATEST)

    return router


def validate_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    settings: Settings = request.app.state.settings
    if origin is not None and origin not in settings.origin_allowlist:
        raise ForbiddenError


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


def error_response(request: Request, code: str, message: str, status_code: int) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    payload = ErrorResponse(error=ErrorDetails(code=code, message=message, request_id=request_id))
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    return JSONResponse(status_code=status_code, content=payload.model_dump(), headers=headers)
