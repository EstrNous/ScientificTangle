from contextlib import asynccontextmanager

import structlog
import httpx
from fastapi import FastAPI
from minio import Minio

from .api.documents import router as documents_router
from .api.health import router as health_router
from .api.ingestion import router as ingestion_router
from .core.config import settings
from .core.logging import setup_logging
from .parsers import ParserRegistry
from .service.service import IngestionService
from .service.storage import SourceStorage
from shared.metrics import build_metrics_router, setup_metrics
from shared.security import JWKSValidator
from shared.web import install_error_handlers, request_id_middleware

setup_logging(settings.service_name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = structlog.get_logger()
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))
    source_storage = SourceStorage(
        client=Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        ),
        bucket=settings.source_bucket,
        upload_limit_bytes=settings.upload_limit_bytes,
    )
    await source_storage.ensure_bucket()
    parser_registry = ParserRegistry(
        libreoffice_binary=settings.libreoffice_binary,
        conversion_timeout_seconds=settings.doc_conversion_timeout_seconds,
        archive_max_entries=settings.archive_max_entries,
        archive_max_uncompressed_bytes=settings.archive_max_uncompressed_bytes,
    )
    app.state.ingestion_service = IngestionService(source_storage, parser_registry)
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
app.include_router(documents_router)
app.include_router(ingestion_router)
