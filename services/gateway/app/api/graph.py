from typing import Annotated

from fastapi import APIRouter, Depends

from shared.contracts import GraphPayload, SearchResultsPayload
from shared.security import AuthenticatedPrincipal
from shared.web import require_principal

from ..core.dependencies import get_graph_service
from ..service.graph_service import GraphService

router = APIRouter(tags=["graph"])


@router.get("/graph", response_model_by_alias=True)
async def get_graph(
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[GraphService, Depends(get_graph_service)],
) -> GraphPayload:
    return await service.get_graph()


@router.get("/search", response_model_by_alias=True)
async def search(
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[GraphService, Depends(get_graph_service)],
) -> SearchResultsPayload:
    return await service.search()
