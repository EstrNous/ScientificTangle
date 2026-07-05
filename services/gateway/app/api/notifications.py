from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request

from shared.contracts import (
    NotificationListPayload,
    NotificationMarkReadPayload,
)
from shared.security import AuthenticatedPrincipal
from shared.web import ServiceError, require_principal

from ..core.dependencies import get_notification_service
from ..service.notification_service import NotificationService, NotificationServiceError

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListPayload)
async def list_notifications(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
    authorization: Annotated[str, Header()],
    since: datetime | None = Query(default=None),
    cursor: str | None = Query(default=None),
) -> NotificationListPayload:
    try:
        return await service.list_notifications(
            principal,
            since=since,
            cursor=cursor,
            authorization=authorization,
            request_id=request.state.request_id,
        )
    except NotificationServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error


@router.post("/read-all", response_model=NotificationMarkReadPayload)
async def mark_all_read(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
    authorization: Annotated[str, Header()],
) -> NotificationMarkReadPayload:
    try:
        return await service.mark_all_read(
            principal,
            authorization=authorization,
            request_id=request.state.request_id,
        )
    except NotificationServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error


@router.post("/{notification_id}/read", response_model=NotificationMarkReadPayload)
async def mark_read(
    notification_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
    authorization: Annotated[str, Header()],
) -> NotificationMarkReadPayload:
    try:
        return await service.mark_read(
            principal,
            notification_id,
            authorization=authorization,
            request_id=request.state.request_id,
        )
    except NotificationServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error
