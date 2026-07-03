from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, Request, UploadFile, status

from app.core.dependencies import get_gateway_service
from app.service.service import GatewayService, GatewayServiceError
from shared.contracts import IngestionTaskPayload
from shared.security import AuthenticatedPrincipal
from shared.web import ServiceError, require_principal

router = APIRouter(tags=["documents"])


@router.post(
    "/documents/upload",
    response_model=IngestionTaskPayload,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_documents(
    request: Request,
    files: Annotated[list[UploadFile], File()],
    authorization: Annotated[str, Header()],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[GatewayService, Depends(get_gateway_service)],
) -> IngestionTaskPayload:
    try:
        return await service.upload_documents(
            files,
            authorization,
            request.state.request_id,
        )
    except GatewayServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error


@router.get("/tasks/{task_id}", response_model=IngestionTaskPayload)
async def get_ingestion_task(
    task_id: UUID,
    request: Request,
    authorization: Annotated[str, Header()],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[GatewayService, Depends(get_gateway_service)],
) -> IngestionTaskPayload:
    try:
        return await service.get_ingestion_task(
            task_id,
            authorization,
            request.state.request_id,
        )
    except GatewayServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error
