from uuid import UUID

import httpx
from fastapi import UploadFile, status

from shared.contracts import ApiError, IngestionTaskPayload


class GatewayServiceError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


class GatewayService:
    def __init__(
        self,
        client: httpx.AsyncClient,
        orchestrator_url: str,
        upload_limit_bytes: int,
    ) -> None:
        self._client = client
        self._orchestrator_url = orchestrator_url.rstrip("/")
        self._upload_limit_bytes = upload_limit_bytes

    async def upload_documents(
        self,
        files: list[UploadFile],
        authorization: str,
        request_id: str,
    ) -> IngestionTaskPayload:
        await self._measure_uploads(files)
        multipart = [
            ("files", (upload.filename, upload.file, upload.content_type or "application/octet-stream"))
            for upload in files
        ]
        response = await self._request(
            "POST",
            "/ingestion/tasks",
            authorization,
            request_id,
            files=multipart,
        )
        if response.status_code != status.HTTP_202_ACCEPTED:
            raise self._downstream_error(response)
        return self._task_payload(response)

    async def get_ingestion_task(
        self,
        task_id: UUID,
        authorization: str,
        request_id: str,
    ) -> IngestionTaskPayload:
        response = await self._request(
            "GET",
            f"/ingestion/tasks/{task_id}",
            authorization,
            request_id,
        )
        if response.status_code != status.HTTP_200_OK:
            raise self._downstream_error(response)
        return self._task_payload(response)

    async def _measure_uploads(self, files: list[UploadFile]) -> None:
        total_size = 0
        for upload in files:
            if not upload.filename:
                raise GatewayServiceError(422, "invalid_file", "Every upload must have a filename")
            file_size = 0
            while chunk := await upload.read(1024 * 1024):
                file_size += len(chunk)
                total_size += len(chunk)
                if total_size > self._upload_limit_bytes:
                    raise GatewayServiceError(413, "upload_too_large", "Upload exceeds the 100 MB limit")
            await upload.seek(0)
            if file_size == 0:
                raise GatewayServiceError(422, "empty_file", "Empty files are not accepted")

    async def _request(
        self,
        method: str,
        path: str,
        authorization: str,
        request_id: str,
        files: list[tuple[str, tuple[str | None, object, str]]] | None = None,
    ) -> httpx.Response:
        try:
            return await self._client.request(
                method,
                f"{self._orchestrator_url}{path}",
                files=files,
                headers={"Authorization": authorization, "X-Request-ID": request_id},
            )
        except httpx.TimeoutException as error:
            raise GatewayServiceError(504, "orchestrator_timeout", "Orchestrator request timed out") from error
        except httpx.HTTPError as error:
            raise GatewayServiceError(503, "orchestrator_unavailable", "Orchestrator is unavailable") from error

    @staticmethod
    def _downstream_error(response: httpx.Response) -> GatewayServiceError:
        status_code = response.status_code if 400 <= response.status_code < 600 else 502
        try:
            payload = ApiError.model_validate(response.json())
            return GatewayServiceError(status_code, payload.code, payload.message)
        except (ValueError, TypeError):
            return GatewayServiceError(
                status_code, "downstream_error", "Downstream service request failed"
            )

    @staticmethod
    def _task_payload(response: httpx.Response) -> IngestionTaskPayload:
        try:
            return IngestionTaskPayload.model_validate(response.json())
        except ValueError as error:
            raise GatewayServiceError(
                502, "invalid_orchestrator_response", "Orchestrator returned invalid data"
            ) from error
