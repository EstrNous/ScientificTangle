from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from shared.contracts import AuditEvent, UserRole
from shared.security import AuthenticatedPrincipal
from shared.web import ServiceError, require_principal

from ..core.dependencies import get_orchestrator_service
from ..service.orchestrator import OrchestratorService, OrchestratorServiceError

router = APIRouter(prefix="/audit", tags=["audit"])


def require_admin(principal: AuthenticatedPrincipal = Depends(require_principal)) -> AuthenticatedPrincipal:
    if principal.role != UserRole.ADMIN:
        raise ServiceError(403, "forbidden", "Admin access required")
    return principal


@router.get("/events", response_model=list[AuditEvent])
async def list_audit_events(
    principal: Annotated[AuthenticatedPrincipal, Depends(require_admin)],
    service: Annotated[OrchestratorService, Depends(get_orchestrator_service)],
    action: str | None = Query(default=None, min_length=1),
    user_id: UUID | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[AuditEvent]:
    try:
        return await service.list_audit_events(
            limit=limit,
            offset=offset,
            action=action,
            user_id=user_id,
        )
    except OrchestratorServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error
