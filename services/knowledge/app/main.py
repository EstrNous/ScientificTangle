from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import settings
from app.core.logging import setup_logging
from shared.metrics import build_metrics_router, setup_metrics

setup_logging(settings.service_name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = structlog.get_logger()
    logger.info("service_started", service=settings.service_name, port=settings.port)
    yield
    logger.info("service_stopped", service=settings.service_name)


app = FastAPI(
    title=settings.service_name,
    version="0.1.0",
    lifespan=lifespan,
)

setup_metrics(app, settings.service_name)
app.include_router(build_metrics_router())
app.include_router(health_router)
