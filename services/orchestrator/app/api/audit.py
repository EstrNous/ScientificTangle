from typing import Annotated

from fastapi import APIRouter, Depends, Query

from shared.contracts import AuditEvent, UserRole
from shared.security import AuthenticatedPrincipal
from shared.web import ServiceError, require_principal

from ..core.dependencies import get_orchestrator_service
from ..service.service import OrchestratorService, OrchestratorServiceError

router = APIRouter(prefix="/audit", tags=["audit"])


def require_admin(principal: AuthenticatedPrincipal = Depends(require_principal)) -> AuthenticatedPrincipal:
    if principal.role != UserRole.ADMIN:
        raise ServiceError(403, "forbidden", "Admin access required")
    return principal


@router.get("/events", response_model=list[AuditEvent])
async def list_audit_events(
    principal: Annotated[AuthenticatedPrincipal, Depends(require_admin)],
    service: Annotated[OrchestratorService, Depends(get_orchestrator_service)],
    limit: int = Query(default=200, ge=1, le=500),
) -> list[AuditEvent]:
    try:
        return await service.list_audit_events(limit)
    except OrchestratorServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error
