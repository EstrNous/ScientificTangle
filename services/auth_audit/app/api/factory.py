import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from infra.postgres.auth_audit_db import AuthRepository, create_database
from shared.contracts import ApiError
from shared.metrics import build_metrics_router, setup_metrics
from shared.web import install_error_handlers, request_id_middleware
from ..core.audit import AuthAuditSink, LoggingAuthAuditSink
from ..core.config import Settings
from ..service.security import KeyStore, PasswordManager, TokenManager
from .auth import router as auth_router
from .health import router as health_router
from .users import router as users_router


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
            401: {"model": ApiError},
            403: {"model": ApiError},
            404: {"model": ApiError},
            409: {"model": ApiError},
            422: {"model": ApiError},
        },
    )
    app.state.settings = resolved_settings
    app.state.repository = repository
    app.state.audit_sink = audit_sink or LoggingAuthAuditSink()
    app.state.key_store = key_store
    app.state.password_manager = password_manager
    app.state.token_manager = token_manager
    app.middleware("http")(request_id_middleware)
    setup_metrics(app, resolved_settings.service_name)
    install_error_handlers(app)
    app.include_router(build_metrics_router())
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(health_router)
    return app
