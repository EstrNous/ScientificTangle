from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field

from ..core.dependencies import get_gateway_service
from ..service.service import GatewayService, GatewayServiceError
from shared.contracts import NormalizedDocument
from shared.security import AuthenticatedPrincipal
from shared.web import ServiceError, require_principal

router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    query: str = Field(min_length=1)
    documents: list[NormalizedDocument] = Field(default_factory=list)
    limit: int = Field(default=20, ge=1, le=100)


@router.post("/query")
async def query(
    request: Request,
    payload: QueryRequest,
    authorization: Annotated[str, Header()],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[GatewayService, Depends(get_gateway_service)],
) -> dict:
    try:
        return await service.run_query(payload.model_dump(mode="json"), authorization, request.state.request_id)
    except GatewayServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error
