from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_session
from app.db.repository import IngestionTaskRepository
from app.service.service import OrchestratorService


def get_orchestrator_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrchestratorService:
    return OrchestratorService(
        repository=IngestionTaskRepository(session),
        client=request.app.state.http_client,
        ingestion_url=settings.ingestion_url,
    )
