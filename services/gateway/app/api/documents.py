from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, Query, Request, UploadFile, status

from shared.contracts import (
    DeleteDocumentResult,
    DocumentCatalogItem,
    DocumentCatalogResponse,
    IngestionTaskPayload,
    UserRole,
)
from shared.security import AuthenticatedPrincipal
from shared.web import ServiceError, require_principal

from ..core.dependencies import get_gateway_service
from ..service.service import GatewayService, GatewayServiceError

router = APIRouter(tags=["documents"])

_RESERVED_DOCUMENT_SEGMENTS = frozenset({"upload"})


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


@router.get("/documents", response_model=DocumentCatalogResponse)
async def list_documents(
    request: Request,
    authorization: Annotated[str, Header()],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[GatewayService, Depends(get_gateway_service)],
    status_filter: str | None = Query(default=None, alias="status"),
    catalog_filter: str | None = Query(default=None, alias="filter"),
    limit: int = 50,
    offset: int = 0,
) -> DocumentCatalogResponse:
    if principal.role != UserRole.ADMIN:
        from shared.web import ServiceError

        raise ServiceError(403, "forbidden", "Admin access required")
    try:
        return await service.list_documents(
            authorization,
            request.state.request_id,
            status_filter=status_filter,
            catalog_filter=catalog_filter,
            limit=limit,
            offset=offset,
        )
    except GatewayServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error


@router.get("/documents/{document_id}", response_model=DocumentCatalogItem)
async def get_document(
    document_id: str,
    request: Request,
    authorization: Annotated[str, Header()],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[GatewayService, Depends(get_gateway_service)],
) -> DocumentCatalogItem:
    if document_id in _RESERVED_DOCUMENT_SEGMENTS:
        raise ServiceError(404, "document_not_found", "Document not found")
    try:
        return await service.get_document(document_id, authorization, request.state.request_id)
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
    request: Request,
    authorization: Annotated[str, Header()],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[GatewayService, Depends(get_gateway_service)],
) -> DeleteDocumentResult:
    if document_id in _RESERVED_DOCUMENT_SEGMENTS:
        raise ServiceError(404, "document_not_found", "Document not found")
    try:
        return DeleteDocumentResult.model_validate(
            await service.delete_document(document_id, authorization, request.state.request_id)
        )
    except GatewayServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error
