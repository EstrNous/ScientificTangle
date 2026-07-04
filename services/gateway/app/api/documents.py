from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, Request, UploadFile, status

from shared.contracts import DeleteDocumentResult, IngestionTaskPayload
from shared.security import AuthenticatedPrincipal
from shared.web import ServiceError, require_principal

from ..core.dependencies import get_gateway_service
from ..service.service import GatewayService, GatewayServiceError

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


@router.delete("/documents/{document_id}", response_model=DeleteDocumentResult)
async def delete_document(
    document_id: str,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
) -> DeleteDocumentResult:
    raise ServiceError(
        status.HTTP_501_NOT_IMPLEMENTED,
        "document_delete_not_implemented",
        "Document deletion API contract is available, storage purge wiring is not implemented in E1",
    )
