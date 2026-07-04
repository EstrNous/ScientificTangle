from contextlib import asynccontextmanager

import httpx
import structlog
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from shared.metrics import build_metrics_router, setup_metrics
from shared.security import JWKSValidator
from shared.web import install_error_handlers, request_id_middleware

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
from .core.config import settings
from .core.logging import setup_logging
from .service.notification_service import NotificationService
from .service.service import GatewayService

setup_logging(settings.service_name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = structlog.get_logger()
    engine = create_async_engine(settings.postgres_url, pool_pre_ping=True)
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=5.0))
    jwt_validator = JWKSValidator(
        auth_url=settings.auth_url,
        issuer=settings.auth_jwt_issuer,
        audience=settings.auth_jwt_audience,
        cache_seconds=settings.auth_jwks_cache_seconds,
        clock_skew_seconds=settings.auth_clock_skew_seconds,
        client=http_client,
    )
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.http_client = http_client
    app.state.gateway_service = GatewayService(
        client=http_client,
        orchestrator_url=settings.orchestrator_url,
        upload_limit_bytes=settings.upload_limit_bytes,
        export_url=settings.export_url,
    )
    app.state.notification_service = NotificationService(
        http_client,
        internal_service_token=settings.internal_service_token,
    )
    app.state.jwt_validator = jwt_validator
    logger.info("service_started", service=settings.service_name, port=settings.port)
    yield
    await http_client.aclose()
    await engine.dispose()
    logger.info("service_stopped", service=settings.service_name)


app = FastAPI(
    title=settings.service_name,
    version="0.1.0",
    lifespan=lifespan,
    root_path="/api",
)

app.middleware("http")(request_id_middleware)
setup_metrics(app, settings.service_name)
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
