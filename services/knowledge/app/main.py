from contextlib import asynccontextmanager

import httpx
import structlog
from adapters.driver import create_driver, verify_connectivity
from adapters.neo4j_adapter import Neo4jKnowledgeAdapter
from adapters.neo4j_storage_adapter import Neo4jStorageAdapter
from adapters.schema import seed_schema_registry
from fastapi import FastAPI

from shared.metrics import build_metrics_router, setup_metrics
from shared.web import install_error_handlers, request_id_middleware

from .api.extraction import router as extraction_router
from .api.graph import router as graph_router
from .api.health import router as health_router
from .core.config import settings
from .core.logging import setup_logging
from .storage import PendingKnowledgeStorageAdapter

setup_logging(settings.service_name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = structlog.get_logger()
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0))
    app.state.http_client = http_client
    driver = create_driver(settings.neo4j_url, settings.neo4j_user, settings.neo4j_password)
    app.state.neo4j_driver = driver
    adapter = Neo4jKnowledgeAdapter(driver)
    app.state.neo4j_adapter = adapter
    if await verify_connectivity(driver):
        app.state.storage_adapter = Neo4jStorageAdapter(adapter)
        try:
            await seed_schema_registry(driver)
            logger.info("neo4j_schema_bootstrapped", service=settings.service_name)
        except Exception as exc:
            logger.warning("neo4j_schema_bootstrap_failed", error=str(exc))
    else:
        app.state.storage_adapter = PendingKnowledgeStorageAdapter()
        logger.warning("neo4j_unavailable", service=settings.service_name)
    logger.info("service_started", service=settings.service_name, port=settings.port)
    yield
    await driver.close()
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
app.include_router(extraction_router)
app.include_router(graph_router)
