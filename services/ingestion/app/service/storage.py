import hashlib
import re
from pathlib import PurePosixPath
from uuid import UUID, uuid4

from anyio import to_thread
from fastapi import UploadFile
from minio import Minio

from shared.contracts import StoredSource


class InvalidUploadError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


class StorageOperationError(Exception):
    pass


class SourceStorage:
    def __init__(self, client: Minio, bucket: str, upload_limit_bytes: int) -> None:
        self._client = client
        self._bucket = bucket
        self._upload_limit_bytes = upload_limit_bytes

    async def ensure_bucket(self) -> None:
        await to_thread.run_sync(self._ensure_bucket)

    async def store(
        self,
        user_id: UUID,
        task_id: UUID,
        files: list[UploadFile],
    ) -> list[StoredSource]:
        return await to_thread.run_sync(self._store, user_id, task_id, files)

    async def read(self, source: StoredSource) -> bytes:
        return await to_thread.run_sync(self._read, source)

    def _ensure_bucket(self) -> None:
        try:
            if not self._client.bucket_exists(self._bucket):
                self._client.make_bucket(self._bucket)
        except Exception as error:
            raise StorageOperationError from error

    def _store(
        self,
        user_id: UUID,
        task_id: UUID,
        files: list[UploadFile],
    ) -> list[StoredSource]:
        stored: list[StoredSource] = []
        total_size = 0
        try:
            for upload in files:
                original_filename = self._original_filename(upload.filename)
                safe_filename = self._safe_filename(original_filename)
                size_bytes, checksum = self._inspect(upload)
                total_size += size_bytes
                if total_size > self._upload_limit_bytes:
                    raise InvalidUploadError(413, "upload_too_large", "Upload exceeds the 100 MB limit")
                object_key = (
                    f"uploads/{user_id}/{task_id}/{uuid4().hex}-{safe_filename}"
                )
                content_type = upload.content_type or "application/octet-stream"
                upload.file.seek(0)
                self._client.put_object(
                    self._bucket,
                    object_key,
                    upload.file,
                    size_bytes,
                    content_type=content_type,
                )
                stored.append(
                    StoredSource(
                        object_key=object_key,
                        original_filename=original_filename,
                        content_type=content_type,
                        size_bytes=size_bytes,
                        sha256=checksum,
                    )
                )
            return stored
        except InvalidUploadError:
            self._rollback(stored)
            raise
        except Exception as error:
            self._rollback(stored)
            raise StorageOperationError from error

    def _read(self, source: StoredSource) -> bytes:
        response = None
        try:
            response = self._client.get_object(self._bucket, source.object_key)
            content = response.read()
        except Exception as error:
            raise StorageOperationError from error
        finally:
            if response is not None:
                response.close()
                response.release_conn()
        checksum = hashlib.sha256(content).hexdigest()
        if len(content) != source.size_bytes or checksum != source.sha256:
            raise StorageOperationError
        return content

    def _inspect(self, upload: UploadFile) -> tuple[int, str]:
        if not upload.filename:
            raise InvalidUploadError(422, "invalid_file", "Every upload must have a filename")
        digest = hashlib.sha256()
        size_bytes = 0
        upload.file.seek(0)
        while chunk := upload.file.read(1024 * 1024):
            size_bytes += len(chunk)
            digest.update(chunk)
        upload.file.seek(0)
        if size_bytes == 0:
            raise InvalidUploadError(422, "empty_file", "Empty files are not accepted")
        return size_bytes, digest.hexdigest()

    def _rollback(self, sources: list[StoredSource]) -> None:
        for source in sources:
            try:
                self._client.remove_object(self._bucket, source.object_key)
            except Exception:
                continue

    @staticmethod
    def _original_filename(filename: str | None) -> str:
        if not filename:
            raise InvalidUploadError(422, "invalid_file", "Every upload must have a filename")
        return PurePosixPath(filename.replace("\\", "/")).name

    @staticmethod
    def _safe_filename(filename: str) -> str:
        sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("._")
        return sanitized or "source"
