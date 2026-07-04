from typing import Annotated

from fastapi import APIRouter, Depends

from shared.contracts import UserInterestsPayload, UserInterestsUpdatePayload
from shared.security import AuthenticatedPrincipal
from shared.web import require_principal

from ..core.dependencies import get_notification_service
from ..service.notification_service import NotificationService

router = APIRouter(prefix="/interests", tags=["interests"])


@router.get("", response_model=UserInterestsPayload)
async def get_interests(
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> UserInterestsPayload:
    return await service.get_interests(principal)


@router.put("", response_model=UserInterestsPayload)
async def update_interests(
    payload: UserInterestsUpdatePayload,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> UserInterestsPayload:
    return await service.update_interests(principal, payload)
