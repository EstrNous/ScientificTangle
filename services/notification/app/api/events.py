from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from infra.postgres.notification_db.repository import NotificationData
from shared.contracts import NotificationPayload
from shared.web import require_internal_service

from ..core.dependencies import get_matching_service, get_notification_service
from ..service.matching_service import MatchingService
from ..service.notification_service import NotificationService

router = APIRouter(
    prefix="/internal/v1",
    tags=["internal"],
    dependencies=[Depends(require_internal_service)],
)


class NotificationEventCreate(BaseModel):
    user_id: UUID
    type: str
    message: str
    reference_id: str | None = None
    reference_type: str | None = None
    match_score: float | None = None
    match_reason: str = ""
    match_payload: dict[str, Any] | None = None


class InternalMatchRequest(BaseModel):
    user_id: UUID
    document_id: str
    artifacts: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/events", response_model=NotificationPayload)
async def create_event(
    request: Request,
    payload: NotificationEventCreate,
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationPayload:
    created = await service.create_event(
        NotificationData(
            user_id=payload.user_id,
            type=payload.type,
            message=payload.message,
            reference_id=payload.reference_id,
            reference_type=payload.reference_type,
            match_score=payload.match_score,
            match_reason=payload.match_reason,
            match_payload=payload.match_payload,
        )
    )
    redis_bus = getattr(request.app.state, "redis_bus", None)
    if redis_bus is not None:
        await redis_bus.publish_created(created, request_id=getattr(request.state, "request_id", ""))
    return created


@router.post("/match", response_model=list[NotificationPayload])
async def match_interests(
    request: Request,
    payload: InternalMatchRequest,
    service: Annotated[MatchingService, Depends(get_matching_service)],
) -> list[NotificationPayload]:
    created = await service.match_and_notify(
        payload.user_id,
        payload.document_id,
        payload.artifacts,
    )
    redis_bus = getattr(request.app.state, "redis_bus", None)
    if redis_bus is not None:
        request_id = getattr(request.state, "request_id", "")
        for item in created:
            await redis_bus.publish_created(item, request_id=request_id)
    return created
