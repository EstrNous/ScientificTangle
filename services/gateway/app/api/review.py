from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel, Field

from shared.contracts import (
    ReviewDecisionPayload,
    ReviewDecisionResult,
    ReviewQueuePayload,
)
from shared.security import AuthenticatedPrincipal
from shared.web import ServiceError, require_principal

from ..core.dependencies import get_gateway_service
from ..service.service import GatewayService, GatewayServiceError

router = APIRouter(prefix="/review", tags=["review"])


class ReviewQueueRequest(BaseModel):
    status: str = "pending"
    limit: int = Field(default=20, ge=1, le=100)


@router.get("/queue", response_model=ReviewQueuePayload)
async def review_queue(
    request: Request,
    authorization: Annotated[str, Header()],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[GatewayService, Depends(get_gateway_service)],
    status_filter: str = Query(default="pending", alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
) -> ReviewQueuePayload:
    try:
        return ReviewQueuePayload.model_validate(
            await service.get_review_queue(
                authorization,
                request.state.request_id,
                status_filter,
                limit,
            )
        )
    except GatewayServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error


@router.post("/queue", response_model=ReviewQueuePayload)
async def post_review_queue(
    request_payload: ReviewQueueRequest,
    request: Request,
    authorization: Annotated[str, Header()],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[GatewayService, Depends(get_gateway_service)],
) -> ReviewQueuePayload:
    try:
        return ReviewQueuePayload.model_validate(
            await service.post_review_queue(
                authorization,
                request.state.request_id,
                request_payload.status,
                request_payload.limit,
            )
        )
    except GatewayServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error


@router.post("/decisions", response_model=ReviewDecisionResult)
async def review_decision(
    payload: ReviewDecisionPayload,
    request: Request,
    authorization: Annotated[str, Header()],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[GatewayService, Depends(get_gateway_service)],
) -> ReviewDecisionResult:
    try:
        return ReviewDecisionResult.model_validate(
            await service.review_decision(
                payload.model_dump(mode="json"),
                authorization,
                request.state.request_id,
            )
        )
    except GatewayServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error
