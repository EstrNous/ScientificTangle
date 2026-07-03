from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from .api.health import router as health_router
from .api.v1 import router as v1_router
from .core.config import settings
from .core.logging import setup_logging

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

app.include_router(health_router)
app.include_router(v1_router)
