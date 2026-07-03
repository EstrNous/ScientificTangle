from uuid import UUID

from fastapi import UploadFile

from shared.contracts import (
    IngestionReport,
    NormalizeStoredSourcesRequest,
    NormalizeStoredSourcesResponse,
)

from ..parsers import ParserRegistry, SourceContent
from .storage import InvalidUploadError, SourceStorage, StorageOperationError


class UploadStorageError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


class SourceNormalizationError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


class IngestionService:
    def __init__(self, storage: SourceStorage, parser_registry: ParserRegistry) -> None:
        self._storage = storage
        self._parser_registry = parser_registry

    async def store_sources(
        self,
        user_id: UUID,
        task_id: UUID,
        files: list[UploadFile],
    ) -> IngestionReport:
        try:
            sources = await self._storage.store(user_id, task_id, files)
            return IngestionReport(sources=sources)
        except InvalidUploadError as error:
            raise UploadStorageError(error.status_code, error.code, error.message) from error
        except StorageOperationError as error:
            raise UploadStorageError(503, "storage_unavailable", "Source storage is unavailable") from error

    async def normalize_sources(
        self,
        user_id: UUID,
        task_id: UUID,
        request: NormalizeStoredSourcesRequest,
    ) -> NormalizeStoredSourcesResponse:
        expected_prefix = f"uploads/{user_id}/{task_id}/"
        documents = []
        warnings = []
        for source in request.sources:
            if not source.object_key.startswith(expected_prefix):
                raise SourceNormalizationError(
                    403,
                    "source_scope_mismatch",
                    "Stored source does not belong to the ingestion task",
                )
            try:
                content = await self._storage.read(source)
            except StorageOperationError:
                warnings.append(f"source_read_failed:{source.original_filename}")
                continue
            source_documents, source_warnings = self._parser_registry.normalize(
                SourceContent(
                    object_key=source.object_key,
                    original_filename=source.original_filename,
                    source_checksum=source.sha256,
                    content=content,
                ),
                request.access_policy,
            )
            documents.extend(source_documents)
            warnings.extend(source_warnings)
        return NormalizeStoredSourcesResponse(documents=documents, warnings=warnings)
