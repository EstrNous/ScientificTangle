from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile

from shared.contracts import DictionaryPackagePayload
from shared.security import AuthenticatedPrincipal
from shared.web import ServiceError, require_principal

from ..core.config import settings
from ..core.dependencies import get_ingestion_service
from ..service.service import IngestionService, UploadStorageError

router = APIRouter(prefix="/ingestion/dictionaries", tags=["dictionaries"])


@router.post("/{task_id}/package", response_model=DictionaryPackagePayload)
async def store_dictionary_package(
    task_id: UUID,
    package: Annotated[UploadFile, File()],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[IngestionService, Depends(get_ingestion_service)],
) -> DictionaryPackagePayload:
    try:
        return await service.store_dictionary_package(
            principal.user_id,
            task_id,
            package,
            settings.archive_max_entries,
            settings.archive_max_uncompressed_bytes,
        )
    except UploadStorageError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error
