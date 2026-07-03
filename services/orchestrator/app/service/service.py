from uuid import UUID

import httpx
from fastapi import UploadFile, status

from app.db.models import IngestionTask
from app.db.repository import IngestionTaskRepository
from shared.contracts import (
    ApiError,
    AnswerPayload,
    EvidenceBundle,
    IngestionReport,
    IngestionTaskPayload,
    IngestionTaskStatus,
    NormalizedDocument,
    QueryIR,
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
        retrieval_url: str,
        model_url: str,
    ) -> None:
        self._repository = repository
        self._client = client
        self._ingestion_url = ingestion_url.rstrip("/")
        self._retrieval_url = retrieval_url.rstrip("/")
        self._model_url = model_url.rstrip("/")

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

    async def run_query(
        self,
        principal: AuthenticatedPrincipal,
        query: str,
        documents: list[NormalizedDocument],
        request_id: str,
        limit: int,
    ) -> dict:
        retrieval_response = await self._request_downstream(
            "POST",
            self._retrieval_url,
            "/v1/query",
            {
                "query": query,
                "documents": [document.model_dump(mode="json") for document in documents],
                "access_roles": [principal.role.value],
                "limit": limit,
            },
            request_id,
            "retrieval",
        )
        query_ir = QueryIR.model_validate(retrieval_response["query_ir"])
        evidence_bundle = EvidenceBundle.model_validate(retrieval_response["evidence_bundle"])
        gaps_response = await self._request_downstream(
            "POST",
            self._model_url,
            "/v1/gaps/suggest",
            {
                "query_ir": query_ir.model_dump(mode="json"),
                "evidence_bundle": evidence_bundle.model_dump(mode="json"),
                "candidates": [],
            },
            request_id,
            "model",
        )
        evidence_bundle.gaps = [gap.get("description", str(gap)) for gap in gaps_response.get("gaps", [])]
        evidence_bundle.has_gaps = bool(evidence_bundle.gaps)
        answer_response = await self._request_downstream(
            "POST",
            self._model_url,
            "/v1/answers/synthesize",
            {
                "query_ir": query_ir.model_dump(mode="json"),
                "evidence_bundle": evidence_bundle.model_dump(mode="json"),
                "candidate_items": [],
            },
            request_id,
            "model",
        )
        answer = AnswerPayload.model_validate(answer_response["answer"])
        return {
            "query_ir": query_ir.model_dump(mode="json"),
            "evidence_bundle": evidence_bundle.model_dump(mode="json"),
            "answer": answer.model_dump(mode="json"),
            "unsupported_warnings": answer_response.get("unsupported_warnings", []),
            "warnings": [
                *retrieval_response.get("warnings", []),
                *gaps_response.get("warnings", []),
                *answer_response.get("warnings", []),
            ],
        }

    async def _request_downstream(
        self,
        method: str,
        base_url: str,
        path: str,
        payload: dict,
        request_id: str,
        service_name: str,
    ) -> dict:
        try:
            response = await self._client.request(
                method,
                f"{base_url}{path}",
                json=payload,
                headers={"X-Request-ID": request_id},
            )
            if response.status_code >= 400:
                raise self._downstream_error(response)
            return response.json()
        except httpx.TimeoutException as error:
            raise OrchestratorServiceError(504, f"{service_name}_timeout", f"{service_name} request timed out") from error
        except httpx.HTTPError as error:
            raise OrchestratorServiceError(503, f"{service_name}_unavailable", f"{service_name} service is unavailable") from error
        except ValueError as error:
            raise OrchestratorServiceError(502, f"invalid_{service_name}_response", f"{service_name} returned invalid data") from error

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
