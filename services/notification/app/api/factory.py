from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import structlog
from fastapi import FastAPI

from shared.contracts import ApiError
from shared.metrics import build_metrics_router, setup_metrics
from shared.security import JWKSValidator
from shared.web import install_error_handlers, request_id_middleware

from ..core.config import Settings, settings
from ..core.logging import setup_logging
from .events import router as events_router
from .health import router as health_router
from .interests import router as interests_router
from .notifications import router as notifications_router


def create_app(resolved_settings: Settings | None = None) -> FastAPI:
    resolved = resolved_settings or settings
    setup_logging(resolved.service_name)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        from infra.postgres.notification_db.database import create_database

        logger = structlog.get_logger()
        if not resolved.internal_service_token:
            logger.warning("internal_service_token_not_configured")
        engine, session_factory = create_database(resolved.postgres_url)
        http_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0))
        app.state.engine = engine
        app.state.session_factory = session_factory
        app.state.http_client = http_client
        app.state.jwt_validator = JWKSValidator(
            auth_url=resolved.auth_url,
            issuer=resolved.auth_jwt_issuer,
            audience=resolved.auth_jwt_audience,
            cache_seconds=resolved.auth_jwks_cache_seconds,
            clock_skew_seconds=resolved.auth_clock_skew_seconds,
            client=http_client,
        )
        app.state.internal_service_token = resolved.internal_service_token
        logger.info("service_started", service=resolved.service_name, port=resolved.port)
        yield
        await http_client.aclose()
        await engine.dispose()
        logger.info("service_stopped", service=resolved.service_name)

    app = FastAPI(
        title=resolved.service_name,
        version="0.1.0",
        lifespan=lifespan,
        responses={
            401: {"model": ApiError},
            403: {"model": ApiError},
            404: {"model": ApiError},
            422: {"model": ApiError},
        },
    )
    app.middleware("http")(request_id_middleware)
    setup_metrics(app, resolved.service_name)
    install_error_handlers(app)
    app.include_router(build_metrics_router())
    app.include_router(health_router)
    app.include_router(interests_router)
    app.include_router(notifications_router)
    app.include_router(events_router)
    return app
