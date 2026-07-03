from uuid import UUID

import httpx
from fastapi import UploadFile, status

from infra.postgres.orchestrator_db import IngestionTask
from infra.postgres.orchestrator_db import IngestionTaskRepository
from shared.contracts import (
    ApiError,
    IngestionReport,
    IngestionTaskPayload,
    IngestionTaskStatus,
    UserRole,
)
from shared.security import AuthenticatedPrincipal


class OrchestratorServiceError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


class OrchestratorService:
    def __init__(
        self,
        repository: IngestionTaskRepository,
        client: httpx.AsyncClient,
        ingestion_url: str,
    ) -> None:
        self._repository = repository
        self._client = client
        self._ingestion_url = ingestion_url.rstrip("/")

    async def create_task(
        self,
        principal: AuthenticatedPrincipal,
        files: list[UploadFile],
        authorization: str,
        request_id: str,
    ) -> IngestionTaskPayload:
        task = await self._repository.create(principal.user_id)
        multipart = [
            ("files", (upload.filename, upload.file, upload.content_type or "application/octet-stream"))
            for upload in files
        ]
        try:
            response = await self._client.post(
                f"{self._ingestion_url}/ingestion/tasks/{task.id}/sources",
                files=multipart,
                headers={"Authorization": authorization, "X-Request-ID": request_id},
            )
            if response.status_code != status.HTTP_201_CREATED:
                raise self._downstream_error(response)
            report = IngestionReport.model_validate(response.json())
        except httpx.TimeoutException as error:
            await self._repository.mark_failed(task, "Ingestion service request timed out")
            raise OrchestratorServiceError(
                504, "ingestion_timeout", "Ingestion service request timed out"
            ) from error
        except httpx.HTTPError as error:
            await self._repository.mark_failed(task, "Ingestion service is unavailable")
            raise OrchestratorServiceError(
                503, "ingestion_unavailable", "Ingestion service is unavailable"
            ) from error
        except OrchestratorServiceError as error:
            await self._repository.mark_failed(task, error.message)
            raise
        except ValueError as error:
            await self._repository.mark_failed(task, "Ingestion service returned invalid data")
            raise OrchestratorServiceError(
                502, "invalid_ingestion_response", "Ingestion service returned invalid data"
            ) from error
        return self._payload(await self._repository.set_report(task, report))

    async def get_task(
        self,
        task_id: UUID,
        principal: AuthenticatedPrincipal,
    ) -> IngestionTaskPayload:
        task = await self._repository.get(task_id)
        if task is None or (
            principal.role != UserRole.ADMIN and task.user_id != principal.user_id
        ):
            raise OrchestratorServiceError(404, "task_not_found", "Ingestion task not found")
        return self._payload(task)

    @staticmethod
    def _payload(task: IngestionTask) -> IngestionTaskPayload:
        return IngestionTaskPayload(
            id=task.id,
            status=IngestionTaskStatus(task.status),
            report=IngestionReport.model_validate(task.report) if task.report else None,
            error_message=task.error_message,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

    @staticmethod
    def _downstream_error(response: httpx.Response) -> OrchestratorServiceError:
        status_code = response.status_code if 400 <= response.status_code < 600 else 502
        try:
            payload = ApiError.model_validate(response.json())
            return OrchestratorServiceError(status_code, payload.code, payload.message)
        except (ValueError, TypeError):
            return OrchestratorServiceError(
                status_code, "ingestion_error", "Ingestion service request failed"
            )
