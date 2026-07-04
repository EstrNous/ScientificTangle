from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from shared.contracts import NotificationListPayload, NotificationMarkReadPayload
from shared.security import AuthenticatedPrincipal
from shared.web import ServiceError, require_principal

from ..core.dependencies import get_notification_service
from ..service.notification_service import NotificationService, NotificationServiceError

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListPayload)
async def list_notifications(
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
    since: datetime | None = Query(default=None),
) -> NotificationListPayload:
    return await service.list_notifications(principal, since=since)


@router.post("/read-all", response_model=NotificationMarkReadPayload)
async def mark_all_read(
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationMarkReadPayload:
    return await service.mark_all_read(principal)


@router.post("/{notification_id}/read", response_model=NotificationMarkReadPayload)
async def mark_read(
    notification_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationMarkReadPayload:
    try:
        return await service.mark_read(principal, notification_id)
    except NotificationServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error
