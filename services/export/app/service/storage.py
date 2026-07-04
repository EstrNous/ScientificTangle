import hashlib
import io
from uuid import UUID

from anyio import to_thread
from minio import Minio


class StorageOperationError(Exception):
    pass


class ArtifactStorage:
    def __init__(self, client: Minio, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    async def ensure_bucket(self) -> None:
        await to_thread.run_sync(self._ensure_bucket)

    async def store(
        self,
        user_id: UUID,
        query_run_id: UUID,
        job_id: UUID,
        artifact_kind: str,
        content: bytes,
        content_type: str,
    ) -> tuple[str, int, str]:
        return await to_thread.run_sync(
            self._store,
            user_id,
            query_run_id,
            job_id,
            artifact_kind,
            content,
            content_type,
        )

    async def read(self, storage_key: str) -> tuple[bytes, str | None]:
        return await to_thread.run_sync(self._read, storage_key)

    def artifact_url(self, job_id: UUID) -> str:
        return f"/v1/jobs/{job_id}/artifact"

    def _ensure_bucket(self) -> None:
        try:
            if not self._client.bucket_exists(self._bucket):
                self._client.make_bucket(self._bucket)
        except Exception as error:
            raise StorageOperationError from error

    def _store(
        self,
        user_id: UUID,
        query_run_id: UUID,
        job_id: UUID,
        artifact_kind: str,
        content: bytes,
        content_type: str,
    ) -> tuple[str, int, str]:
        extension = _artifact_extension(artifact_kind)
        storage_key = f"exports/{user_id}/{query_run_id}/{job_id}/report.{extension}"
        checksum = hashlib.sha256(content).hexdigest()
        try:
            self._client.put_object(
                self._bucket,
                storage_key,
                io.BytesIO(content),
                len(content),
                content_type=content_type,
            )
        except Exception as error:
            raise StorageOperationError from error
        return storage_key, len(content), f"sha256:{checksum}"

    def _read(self, storage_key: str) -> tuple[bytes, str | None]:
        response = None
        try:
            response = self._client.get_object(self._bucket, storage_key)
            content = response.read()
            content_type = response.headers.get("Content-Type")
        except Exception as error:
            raise StorageOperationError from error
        finally:
            if response is not None:
                response.close()
                response.release_conn()
        return content, content_type


def _artifact_extension(artifact_kind: str) -> str:
    if artifact_kind == "markdown":
        return "md"
    if artifact_kind == "jsonld":
        return "jsonld"
    return "json"
