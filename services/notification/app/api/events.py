from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
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
    payload: NotificationEventCreate,
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationPayload:
    return await service.create_event(
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


@router.post("/match", response_model=list[NotificationPayload])
async def match_interests(
    payload: InternalMatchRequest,
    service: Annotated[MatchingService, Depends(get_matching_service)],
) -> list[NotificationPayload]:
    return await service.match_and_notify(
        payload.user_id,
        payload.document_id,
        payload.artifacts,
    )
