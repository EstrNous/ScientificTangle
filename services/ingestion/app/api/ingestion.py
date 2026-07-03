from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status

from shared.contracts import (
    IngestionReport,
    NormalizeStoredSourcesRequest,
    NormalizeStoredSourcesResponse,
)
from shared.security import AuthenticatedPrincipal
from shared.web import ServiceError, require_principal

from ..core.dependencies import get_ingestion_service
from ..service.service import IngestionService, SourceNormalizationError, UploadStorageError

router = APIRouter(prefix="/ingestion/tasks", tags=["ingestion"])


@router.post(
    "/{task_id}/sources",
    response_model=IngestionReport,
    status_code=status.HTTP_201_CREATED,
)
async def store_sources(
    task_id: UUID,
    files: Annotated[list[UploadFile], File()],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[IngestionService, Depends(get_ingestion_service)],
) -> IngestionReport:
    try:
        return await service.store_sources(principal.user_id, task_id, files)
    except UploadStorageError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error


@router.post(
    "/{task_id}/normalize",
    response_model=NormalizeStoredSourcesResponse,
)
async def normalize_sources(
    task_id: UUID,
    payload: NormalizeStoredSourcesRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[IngestionService, Depends(get_ingestion_service)],
) -> NormalizeStoredSourcesResponse:
    try:
        return await service.normalize_sources(principal.user_id, task_id, payload)
    except SourceNormalizationError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error
