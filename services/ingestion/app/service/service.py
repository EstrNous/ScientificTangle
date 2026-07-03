from uuid import UUID

from fastapi import UploadFile

from app.service.storage import InvalidUploadError, SourceStorage, StorageOperationError
from shared.contracts import IngestionReport


class UploadStorageError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


class IngestionService:
    def __init__(self, storage: SourceStorage) -> None:
        self._storage = storage

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
