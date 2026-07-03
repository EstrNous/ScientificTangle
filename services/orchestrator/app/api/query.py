from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.core.dependencies import get_orchestrator_service
from app.service.service import OrchestratorService, OrchestratorServiceError
from shared.contracts import NormalizedDocument
from shared.security import AuthenticatedPrincipal
from shared.web import ServiceError, require_principal

router = APIRouter(prefix="/query", tags=["query"])


class QueryRunRequest(BaseModel):
    query: str = Field(min_length=1)
    documents: list[NormalizedDocument] = Field(default_factory=list)
    limit: int = Field(default=20, ge=1, le=100)


@router.post("/run")
async def run_query(
    request: Request,
    payload: QueryRunRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[OrchestratorService, Depends(get_orchestrator_service)],
) -> dict:
    try:
        return await service.run_query(
            principal=principal,
            query=payload.query,
            documents=payload.documents,
            request_id=request.state.request_id,
            limit=payload.limit,
        )
    except OrchestratorServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error
