import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import RequestResponseEndpoint

from infra.postgres.auth_audit_db import AuthRepository, ErrorResponse, create_database
from shared.metrics import build_metrics_router, setup_metrics
from ..core.audit import AuthAuditSink, LoggingAuthAuditSink
from ..core.config import Settings
from ..service.security import KeyStore, PasswordManager, TokenManager
from .auth import router as auth_router
from .errors import register_error_handlers
from .health import router as health_router
from .users import router as users_router

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


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
        title="ScientificTangle Auth Audit",
        version="0.1.0",
        lifespan=lifespan,
        responses={
            401: {"model": ErrorResponse},
            403: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
        },
    )
    app.state.settings = resolved_settings
    app.state.repository = repository
    app.state.audit_sink = audit_sink or LoggingAuthAuditSink()
    app.state.key_store = key_store
    app.state.password_manager = password_manager
    app.state.token_manager = token_manager
    setup_metrics(app, resolved_settings.service_name)

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
        return response

    register_error_handlers(app)
    app.include_router(build_metrics_router())
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(health_router)
    return app
