from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from shared.contracts import NormalizedDocument, QueryRunResponse
from shared.security import AuthenticatedPrincipal
from shared.web import ServiceError, require_principal

from ..core.dependencies import get_orchestrator_service
from ..service.service import OrchestratorService, OrchestratorServiceError

router = APIRouter(prefix="/query", tags=["query"])


class QueryRunRequest(BaseModel):
    query: str = Field(min_length=1)
    documents: list[NormalizedDocument] = Field(default_factory=list)
    limit: int = Field(default=20, ge=1, le=100)


@router.post("/run", response_model=QueryRunResponse)
async def run_query(
    request: Request,
    payload: QueryRunRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[OrchestratorService, Depends(get_orchestrator_service)],
) -> QueryRunResponse:
    try:
        result = await service.run_query(
            principal=principal,
            query=payload.query,
            documents=payload.documents,
            request_id=request.state.request_id,
            limit=payload.limit,
        )
        return QueryRunResponse.model_validate(result)
    except OrchestratorServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error
