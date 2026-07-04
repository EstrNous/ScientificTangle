from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request

from shared.contracts import UserInterestsPayload, UserInterestsUpdatePayload
from shared.security import AuthenticatedPrincipal
from shared.web import ServiceError, require_principal

from ..core.dependencies import get_notification_service
from ..service.notification_service import NotificationService, NotificationServiceError

router = APIRouter(prefix="/interests", tags=["interests"])


@router.get("", response_model=UserInterestsPayload)
async def get_interests(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
    authorization: Annotated[str, Header()],
) -> UserInterestsPayload:
    try:
        return await service.get_interests(
            principal,
            authorization=authorization,
            request_id=request.state.request_id,
        )
    except NotificationServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error


@router.put("", response_model=UserInterestsPayload)
async def update_interests(
    request: Request,
    payload: UserInterestsUpdatePayload,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
    authorization: Annotated[str, Header()],
) -> UserInterestsPayload:
    try:
        return await service.update_interests(
            principal,
            payload,
            authorization=authorization,
            request_id=request.state.request_id,
        )
    except NotificationServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error
