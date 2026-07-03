from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from infra.postgres.orchestrator_db import get_session, IngestionTaskRepository
from ..service.service import OrchestratorService


def get_orchestrator_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrchestratorService:
    return OrchestratorService(
        repository=IngestionTaskRepository(session),
        client=request.app.state.http_client,
        ingestion_url=settings.ingestion_url,
        retrieval_url=settings.retrieval_url,
        model_url=settings.model_url,
    )
