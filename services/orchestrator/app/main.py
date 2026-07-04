from contextlib import asynccontextmanager

import httpx
import structlog
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from shared.metrics import build_metrics_router, setup_metrics
from shared.security import JWKSValidator
from shared.web import install_error_handlers, request_id_middleware

from .api.audit import router as audit_router
from .api.dictionaries import router as dictionaries_router
from .api.health import router as health_router
from .api.ingestion import router as ingestion_router
from .api.query import router as query_router
from .core.config import settings
from .core.logging import setup_logging

setup_logging(settings.service_name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = structlog.get_logger()
    engine = create_async_engine(settings.postgres_url, pool_pre_ping=True)
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0))
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.http_client = http_client
    app.state.jwt_validator = JWKSValidator(
        auth_url=settings.auth_url,
        issuer=settings.auth_jwt_issuer,
        audience=settings.auth_jwt_audience,
        cache_seconds=settings.auth_jwks_cache_seconds,
        clock_skew_seconds=settings.auth_clock_skew_seconds,
        client=http_client,
    )
    logger.info("service_started", service=settings.service_name, port=settings.port)
    yield
    await http_client.aclose()
    await engine.dispose()
    logger.info("service_stopped", service=settings.service_name)


app = FastAPI(
    title=settings.service_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.middleware("http")(request_id_middleware)
setup_metrics(app, settings.service_name)
install_error_handlers(app)
app.include_router(build_metrics_router())
app.include_router(health_router)
app.include_router(ingestion_router)
app.include_router(query_router)
app.include_router(audit_router)
app.include_router(dictionaries_router)
