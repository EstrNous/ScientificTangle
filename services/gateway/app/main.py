from contextlib import asynccontextmanager

import httpx
import structlog
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from shared.metrics import build_metrics_router, setup_metrics
from shared.security import JWKSValidator
from shared.web import (
    RateLimitRule,
    install_error_handlers,
    install_rate_limit_middleware,
    request_id_middleware,
)

from .api.admin import router as admin_router
from .api.chat import router as chat_router
from .api.dictionaries import router as dictionaries_router
from .api.documents import router as documents_router
from .api.graph import router as graph_router
from .api.health import router as health_router
from .api.interests import router as interests_router
from .api.notifications import router as notifications_router
from .api.query import router as query_router
from .api.review import router as review_router
from .core.config import Settings, settings
from .core.logging import setup_logging
from .service.notification_service import NotificationService
from .service.service import GatewayService

setup_logging(settings.service_name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = structlog.get_logger()
    resolved_settings: Settings = app.state.settings
    engine = create_async_engine(resolved_settings.postgres_url, pool_pre_ping=True)
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=5.0))
    jwt_validator = JWKSValidator(
        auth_url=resolved_settings.auth_url,
        issuer=resolved_settings.auth_jwt_issuer,
        audience=resolved_settings.auth_jwt_audience,
        cache_seconds=resolved_settings.auth_jwks_cache_seconds,
        clock_skew_seconds=resolved_settings.auth_clock_skew_seconds,
        client=http_client,
    )
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.http_client = http_client
    app.state.gateway_service = GatewayService(
        client=http_client,
        orchestrator_url=resolved_settings.orchestrator_url,
        upload_limit_bytes=resolved_settings.upload_limit_bytes,
        export_url=resolved_settings.export_url,
    )
    app.state.notification_service = NotificationService(
        http_client,
        internal_service_token=resolved_settings.internal_service_token,
    )
    app.state.jwt_validator = jwt_validator
    logger.info(
        "service_started",
        service=resolved_settings.service_name,
        port=resolved_settings.port,
    )
    yield
    rate_limiter = getattr(app.state, "rate_limiter", None)
    if rate_limiter is not None:
        await rate_limiter.aclose()
    await http_client.aclose()
    await engine.dispose()
    logger.info("service_stopped", service=resolved_settings.service_name)


def create_app(resolved_settings: Settings | None = None) -> FastAPI:
    resolved = resolved_settings or settings
    app = FastAPI(
        title=resolved.service_name,
        version="0.1.0",
        lifespan=lifespan,
        root_path="/api",
    )
    app.state.settings = resolved
    install_rate_limit_middleware(
        app,
        enabled=resolved.rate_limit_enabled,
        redis_url=resolved.redis_url,
        service_name=resolved.service_name,
        rules=(
            RateLimitRule(
                name="gateway_default",
                limit=resolved.rate_limit_default_per_minute,
            ),
        ),
        excluded_paths=("/health", "/ready", "/metrics"),
        trust_proxy_headers=resolved.rate_limit_trust_proxy_headers,
        use_redis=resolved.rate_limit_use_redis,
    )
    app.middleware("http")(request_id_middleware)
    setup_metrics(app, resolved.service_name)
    install_error_handlers(app)
    app.include_router(build_metrics_router())
    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(dictionaries_router)
    app.include_router(query_router)
    app.include_router(interests_router)
    app.include_router(chat_router)
    app.include_router(graph_router)
    app.include_router(admin_router)
    app.include_router(notifications_router)
    app.include_router(review_router)
    return app


app = create_app()
