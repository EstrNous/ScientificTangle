from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from shared.contracts import (
    ReviewDecisionPayload,
    ReviewDecisionResult,
    ReviewQueuePayload,
)
from shared.security import AuthenticatedPrincipal
from shared.web import ServiceError, require_principal

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/queue", response_model=ReviewQueuePayload)
async def review_queue(
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    status_filter: str = Query(default="pending", alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
) -> ReviewQueuePayload:
    raise ServiceError(
        status.HTTP_501_NOT_IMPLEMENTED,
        "review_storage_not_implemented",
        "Review queue API contract is available; E2 storage is merged, workflow wiring is deferred to E3",
    )


@router.post("/decisions", response_model=ReviewDecisionResult)
async def review_decision(
    payload: ReviewDecisionPayload,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
) -> ReviewDecisionResult:
    raise ServiceError(
        status.HTTP_501_NOT_IMPLEMENTED,
        "review_storage_not_implemented",
        "Review decision API contract is available; E2 storage is merged, workflow wiring is deferred to E3",
    )
