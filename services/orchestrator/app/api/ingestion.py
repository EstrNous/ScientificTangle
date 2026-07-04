from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Header, Request, UploadFile, status

from shared.contracts import IngestionTaskPayload
from shared.security import AuthenticatedPrincipal
from shared.web import ServiceError, require_principal

from ..core.dependencies import get_orchestrator_service
from ..service.service import OrchestratorService, OrchestratorServiceError

router = APIRouter(prefix="/ingestion/tasks", tags=["ingestion"])


@router.post("", response_model=IngestionTaskPayload, status_code=status.HTTP_202_ACCEPTED)
async def create_ingestion_task(
    request: Request,
    background_tasks: BackgroundTasks,
    files: Annotated[list[UploadFile], File()],
    authorization: Annotated[str, Header()],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[OrchestratorService, Depends(get_orchestrator_service)],
) -> IngestionTaskPayload:
    try:
        payload, task_id = await service.start_ingestion_task(
            principal,
            files,
            authorization,
            request.state.request_id,
        )
        background_tasks.add_task(
            service.continue_ingestion_task,
            task_id,
            principal.user_id,
            authorization,
            request.state.request_id,
            request.app.state.session_factory,
        )
        return payload
    except OrchestratorServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error


@router.get("/{task_id}", response_model=IngestionTaskPayload)
async def get_ingestion_task(
    task_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[OrchestratorService, Depends(get_orchestrator_service)],
) -> IngestionTaskPayload:
    try:
        return await service.get_task(task_id, principal)
    except OrchestratorServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error
