from contextlib import asynccontextmanager

import httpx
import structlog
from fastapi import FastAPI
from minio import Minio

from shared.metrics import build_metrics_router, setup_metrics
from shared.security import JWKSValidator
from shared.web import install_error_handlers, request_id_middleware

from .api.health import router as health_router
from .api.jobs import router as jobs_router
from .core.config import settings
from .core.logging import setup_logging
from .service.job_store import JobStore
from .service.service import ExportService
from .service.storage import ArtifactStorage

setup_logging(settings.service_name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = structlog.get_logger()
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0))
    artifact_storage = ArtifactStorage(
        client=Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        ),
        bucket=settings.exports_bucket,
    )
    await artifact_storage.ensure_bucket()
    job_store = JobStore(settings.redis_url, ttl_seconds=settings.export_job_ttl_seconds)
    app.state.export_service = ExportService(
        storage=artifact_storage,
        job_store=job_store,
        client=http_client,
        model_url=settings.model_url,
        exports_bucket=settings.exports_bucket,
    )
    app.state.jwt_validator = JWKSValidator(
        auth_url=settings.auth_url,
        issuer=settings.auth_jwt_issuer,
        audience=settings.auth_jwt_audience,
        cache_seconds=settings.auth_jwks_cache_seconds,
        clock_skew_seconds=settings.auth_clock_skew_seconds,
        client=http_client,
    )
    app.state.artifact_storage = artifact_storage
    logger.info("service_started", service=settings.service_name, port=settings.port)
    yield
    await http_client.aclose()
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
app.include_router(jobs_router)
