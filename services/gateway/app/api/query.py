from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel, Field

from shared.contracts import GraphSubgraph, QueryRunPayload, SearchResultPayload, SourcePayload
from shared.security import AuthenticatedPrincipal
from shared.web import ServiceError, require_principal

from app.core.dependencies import get_gateway_service
from app.service.service import GatewayService, GatewayServiceError

router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    filters: dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=20, ge=1, le=100)


def raise_service_error(error: GatewayServiceError) -> None:
    raise ServiceError(
        error.status_code,
        error.code,
        error.message,
        query_run_id=error.query_run_id,
    ) from error


@router.post("/query", response_model=QueryRunPayload)
async def query(
    request: Request,
    payload: QueryRequest,
    authorization: Annotated[str, Header()],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[GatewayService, Depends(get_gateway_service)],
) -> QueryRunPayload:
    try:
        response = await service.run_query(
            payload.model_dump(mode="json"),
            authorization,
            request.state.request_id,
        )
        return QueryRunPayload.model_validate(response)
    except GatewayServiceError as error:
        raise_service_error(error)


@router.get("/runs/{run_id}", response_model=QueryRunPayload)
async def get_run(
    run_id: UUID,
    request: Request,
    authorization: Annotated[str, Header()],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[GatewayService, Depends(get_gateway_service)],
) -> QueryRunPayload:
    try:
        return QueryRunPayload.model_validate(
            await service.get_query_run(run_id, authorization, request.state.request_id)
        )
    except GatewayServiceError as error:
        raise_service_error(error)


@router.get("/source/{source_span_id}", response_model=SourcePayload)
async def get_source(
    source_span_id: str,
    request: Request,
    authorization: Annotated[str, Header()],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[GatewayService, Depends(get_gateway_service)],
) -> SourcePayload:
    try:
        return SourcePayload.model_validate(
            await service.get_source(
                source_span_id,
                authorization,
                request.state.request_id,
            )
        )
    except GatewayServiceError as error:
        raise_service_error(error)


@router.get("/graph/subgraph", response_model=GraphSubgraph)
async def get_subgraph(
    run_id: UUID,
    request: Request,
    authorization: Annotated[str, Header()],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[GatewayService, Depends(get_gateway_service)],
) -> GraphSubgraph:
    try:
        return GraphSubgraph.model_validate(
            await service.get_subgraph(run_id, authorization, request.state.request_id)
        )
    except GatewayServiceError as error:
        raise_service_error(error)


@router.get("/search", response_model=SearchResultPayload)
async def search(
    request: Request,
    authorization: Annotated[str, Header()],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[GatewayService, Depends(get_gateway_service)],
    question: str = Query(default=""),
    source_type: list[str] = Query(default=[]),
    geo: list[str] = Query(default=[]),
    limit: int = Query(default=20, ge=1, le=100),
) -> SearchResultPayload:
    params = [("question", question), ("limit", str(limit))]
    params.extend(("source_type", value) for value in source_type)
    params.extend(("geo", value) for value in geo)
    try:
        return SearchResultPayload.model_validate(
            await service.search(params, authorization, request.state.request_id)
        )
    except GatewayServiceError as error:
        raise_service_error(error)
