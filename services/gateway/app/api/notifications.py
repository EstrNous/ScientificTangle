from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from shared.security import AuthenticatedPrincipal
from shared.web import ServiceError, require_principal

from ..core.dependencies import get_notification_service
from ..service.notification_service import NotificationService, NotificationServiceError

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> list[dict]:
    return await service.list_notifications(principal)


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> None:
    await service.mark_all_read(principal)


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    notification_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> None:
    try:
        await service.mark_read(principal, notification_id)
    except NotificationServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error
