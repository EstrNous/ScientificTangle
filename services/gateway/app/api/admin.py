from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field

from shared.contracts import (
    AccessPolicy,
    AuditEvent,
    LabCoveragePayload,
    StrategicEvaluationPayload,
    StrategicMetricsPayload,
    UserRole,
)
from shared.security import AuthenticatedPrincipal
from shared.web import ServiceError, require_principal

from ..core.dependencies import get_admin_service, get_analytics_service
from ..service.analytics_service import AdminService, AnalyticsService

router = APIRouter(tags=["admin"])


class AdminUserPatchRequest(BaseModel):
    role: str | None = None
    active: bool | None = Field(default=None, alias="is_active")

    model_config = {"populate_by_name": True}


class AdminPolicyPatchRequest(BaseModel):
    access_policy: AccessPolicy


def require_admin(principal: AuthenticatedPrincipal = Depends(require_principal)) -> AuthenticatedPrincipal:
    if principal.role != UserRole.ADMIN:
        raise ServiceError(403, "forbidden", "Admin access required")
    return principal


@router.get("/admin")
async def get_admin(
    authorization: Annotated[str, Header()],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_admin)],
    service: Annotated[AdminService, Depends(get_admin_service)],
) -> dict:
    return await service.get_admin(authorization)


@router.get("/admin/stats")
async def get_admin_stats(
    authorization: Annotated[str, Header()],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_admin)],
    service: Annotated[AdminService, Depends(get_admin_service)],
) -> dict:
    return await service.get_admin_stats(authorization)


@router.get("/audit/events", response_model=list[AuditEvent])
async def list_audit_events(
    authorization: Annotated[str, Header()],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_admin)],
    service: Annotated[AdminService, Depends(get_admin_service)],
) -> list[AuditEvent]:
    return await service.list_audit_events(authorization)


@router.get("/strategic/metrics", response_model=StrategicMetricsPayload)
async def strategic_metrics(
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
) -> StrategicMetricsPayload:
    return await service.get_strategic_metrics()


@router.get("/strategic/evaluation", response_model=StrategicEvaluationPayload)
async def strategic_evaluation(
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
) -> StrategicEvaluationPayload:
    return await service.get_strategic_evaluation()


@router.get("/lab/coverage", response_model=LabCoveragePayload)
async def lab_coverage(
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
) -> LabCoveragePayload:
    return await service.get_lab_coverage()


@router.patch("/admin/users/{user_id}")
async def patch_admin_user(
    user_id: UUID,
    payload: AdminUserPatchRequest,
    authorization: Annotated[str, Header()],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_admin)],
    service: Annotated[AdminService, Depends(get_admin_service)],
) -> dict:
    return await service.patch_user(user_id, payload, authorization)


@router.patch("/admin/policies/{document_id}")
async def patch_admin_policy(
    document_id: str,
    payload: AdminPolicyPatchRequest,
    authorization: Annotated[str, Header()],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_admin)],
    service: Annotated[AdminService, Depends(get_admin_service)],
) -> dict:
    return await service.patch_policy(document_id, payload.access_policy, authorization)
