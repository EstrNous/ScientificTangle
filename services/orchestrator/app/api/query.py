from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from shared.contracts import (
    ExportPayload,
    GraphSubgraph,
    QueryRunPayload,
    SearchResultPayload,
    SourcePayload,
)
from shared.security import AuthenticatedPrincipal
from shared.web import ServiceError, require_principal

from ..core.config import settings
from ..core.dependencies import get_orchestrator_service
from ..service.service import OrchestratorService, OrchestratorServiceError

router = APIRouter(tags=["query"])


class QueryRunRequest(BaseModel):
    question: str = Field(min_length=1)
    filters: dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=20, ge=1, le=100)


class ExportRunRequest(BaseModel):
    query_run_id: UUID
    format: str = Field(pattern="^(markdown|json)$")


def raise_service_error(error: OrchestratorServiceError) -> None:
    raise ServiceError(
        error.status_code,
        error.code,
        error.message,
        query_run_id=error.query_run_id,
    ) from error


@router.post("/query/run", response_model=QueryRunPayload)
async def run_query(
    request: Request,
    payload: QueryRunRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[OrchestratorService, Depends(get_orchestrator_service)],
) -> QueryRunPayload:
    try:
        return await service.run_query(
            principal=principal,
            question=payload.question,
            filters=payload.filters,
            request_id=request.state.request_id,
            limit=payload.limit,
        )
    except OrchestratorServiceError as error:
        raise_service_error(error)


@router.post("/query/stream")
async def stream_query(
    request: Request,
    payload: QueryRunRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[OrchestratorService, Depends(get_orchestrator_service)],
) -> StreamingResponse:
    if not settings.top1_live_stream_enabled:
        raise ServiceError(
            status.HTTP_404_NOT_FOUND,
            "stream_disabled",
            "Live query stream is disabled",
        )
    try:
        return StreamingResponse(
            service.stream_query(
                principal=principal,
                question=payload.question,
                filters=payload.filters,
                request_id=request.state.request_id,
                limit=payload.limit,
            ),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    except OrchestratorServiceError as error:
        raise_service_error(error)


@router.get("/runs/{run_id}", response_model=QueryRunPayload)
async def get_run(
    run_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[OrchestratorService, Depends(get_orchestrator_service)],
) -> QueryRunPayload:
    try:
        return await service.get_run(run_id, principal)
    except OrchestratorServiceError as error:
        raise_service_error(error)


@router.post("/export", response_model=ExportPayload)
async def export_run(
    request: Request,
    payload: ExportRunRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[OrchestratorService, Depends(get_orchestrator_service)],
) -> ExportPayload:
    try:
        return await service.export_query_run(
            principal=principal,
            run_id=payload.query_run_id,
            export_format=payload.format,
            request_id=request.state.request_id,
        )
    except OrchestratorServiceError as error:
        raise_service_error(error)


@router.get("/source/{source_span_id}", response_model=SourcePayload)
async def get_source(
    source_span_id: str,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[OrchestratorService, Depends(get_orchestrator_service)],
) -> SourcePayload:
    try:
        return await service.get_source(
            source_span_id,
            principal,
            request.state.request_id,
        )
    except OrchestratorServiceError as error:
        raise_service_error(error)


@router.get("/graph/subgraph", response_model=GraphSubgraph)
async def get_subgraph(
    run_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[OrchestratorService, Depends(get_orchestrator_service)],
) -> GraphSubgraph:
    try:
        return await service.get_subgraph(run_id, principal)
    except OrchestratorServiceError as error:
        raise_service_error(error)


@router.get("/search", response_model=SearchResultPayload)
async def search(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[OrchestratorService, Depends(get_orchestrator_service)],
    question: str = Query(default=""),
    source_type: list[str] = Query(default=[]),
    geo: list[str] = Query(default=[]),
    limit: int = Query(default=20, ge=1, le=100),
) -> SearchResultPayload:
    filters = {}
    if source_type:
        filters["source_types"] = source_type
    if geo:
        filters["geo_constraints"] = geo
    try:
        return await service.search(
            principal,
            question,
            filters,
            limit,
            request.state.request_id,
        )
    except OrchestratorServiceError as error:
        raise_service_error(error)
