from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, Request, UploadFile, status

from shared.contracts import DictionaryVersionPayload, IngestionTaskPayload, UserRole
from shared.security import AuthenticatedPrincipal
from shared.web import ServiceError, require_principal

from ..core.dependencies import get_orchestrator_service
from ..service.service import OrchestratorService, OrchestratorServiceError

router = APIRouter(prefix="/dictionaries", tags=["dictionaries"])


def require_admin(
    principal: AuthenticatedPrincipal = Depends(require_principal),
) -> AuthenticatedPrincipal:
    if principal.role != UserRole.ADMIN:
        raise ServiceError(403, "forbidden", "Admin access required")
    return principal


@router.post("/upload", response_model=IngestionTaskPayload, status_code=status.HTTP_202_ACCEPTED)
async def upload_dictionary(
    request: Request,
    package: Annotated[UploadFile, File()],
    authorization: Annotated[str, Header()],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_admin)],
    service: Annotated[OrchestratorService, Depends(get_orchestrator_service)],
) -> IngestionTaskPayload:
    try:
        return await service.upload_dictionary(principal, package, authorization, request.state.request_id)
    except OrchestratorServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error


@router.get("", response_model=list[DictionaryVersionPayload])
async def list_dictionaries(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_admin)],
    service: Annotated[OrchestratorService, Depends(get_orchestrator_service)],
) -> list[DictionaryVersionPayload]:
    try:
        return await service.list_dictionaries(request.state.request_id)
    except OrchestratorServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error


@router.get("/active", response_model=DictionaryVersionPayload)
async def get_active_dictionary(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[OrchestratorService, Depends(get_orchestrator_service)],
) -> DictionaryVersionPayload:
    try:
        return await service.get_active_dictionary(request.state.request_id)
    except OrchestratorServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error


@router.post("/{version_id}/activate", response_model=DictionaryVersionPayload)
async def activate_dictionary(
    version_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_admin)],
    service: Annotated[OrchestratorService, Depends(get_orchestrator_service)],
) -> DictionaryVersionPayload:
    try:
        return await service.activate_dictionary(principal, version_id, request.state.request_id)
    except OrchestratorServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error
