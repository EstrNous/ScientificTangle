from contextlib import asynccontextmanager

import httpx
import structlog
from fastapi import FastAPI

from shared.metrics import build_metrics_router, setup_metrics
from shared.web import install_error_handlers, request_id_middleware

from .api.health import router as health_router
from .api.query import router as query_router
from .core.config import settings
from .core.logging import setup_logging
from .qdrant_adapter import QdrantRetrievalStorageAdapter

setup_logging(settings.service_name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = structlog.get_logger()
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0))
    app.state.http_client = http_client
    app.state.storage_adapter = QdrantRetrievalStorageAdapter(http_client)
    try:
        from .api.query import ensure_collection

        await ensure_collection(http_client)
    except httpx.HTTPError:
        logger.warning("qdrant_bootstrap_failed", service=settings.service_name)
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
app.include_router(query_router)
