import json
from uuid import UUID

import httpx

from shared.contracts import AnswerPayload, ApiError
from shared.security import AuthenticatedPrincipal

from ..schemas import (
    ExportArtifactMeta,
    ExportJobCreateRequest,
    ExportJobProcessResponse,
    ExportJobStatusResponse,
)
from .job_store import JobStore
from .renderer import content_type_for_format, render_markdown
from .storage import ArtifactStorage, StorageOperationError


class ExportServiceError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


class ExportService:
    def __init__(
        self,
        storage: ArtifactStorage,
        job_store: JobStore,
        client: httpx.AsyncClient,
        model_url: str,
        exports_bucket: str,
    ) -> None:
        self._storage = storage
        self._job_store = job_store
        self._client = client
        self._model_url = model_url.rstrip("/")
        self._exports_bucket = exports_bucket

    async def create_job(self, request: ExportJobCreateRequest, request_id: str) -> ExportJobProcessResponse:
        existing = await self._job_store.get(request.job_id)
        if existing is not None and existing.status == "completed":
            return self._completed_response(existing)
        if existing is None:
            await self._job_store.create_pending(
                request.job_id,
                request.user_id,
                request.query_run_id,
                request.format,
            )
        await self._job_store.mark_processing(request.job_id)
        try:
            content, content_type, warnings = await self._render_content(request, request_id)
            encoded = self._encode_content(content, content_type)
            storage_key, byte_size, checksum = await self._storage.store(
                request.user_id,
                request.query_run_id,
                request.job_id,
                request.format,
                encoded,
                content_type,
            )
            artifact = ExportArtifactMeta(
                artifact_kind=request.format,
                bucket_name=self._exports_bucket,
                storage_key=storage_key,
                content_type=content_type,
                byte_size=byte_size,
                checksum=checksum,
                file_url=self._storage.artifact_url(request.job_id),
            )
            await self._job_store.mark_completed(request.job_id, [artifact])
            return ExportJobProcessResponse(
                job_id=request.job_id,
                status="completed",
                format=request.format,
                artifacts=[artifact],
                content=content,
                content_type=content_type,
                warnings=warnings,
            )
        except ExportServiceError as error:
            await self._job_store.mark_failed(request.job_id, error.message)
            raise
        except StorageOperationError as error:
            message = "Artifact storage is unavailable"
            await self._job_store.mark_failed(request.job_id, message)
            raise ExportServiceError(503, "storage_unavailable", message) from error
        except Exception as error:
            message = "Export processing failed"
            await self._job_store.mark_failed(request.job_id, message)
            raise ExportServiceError(500, "export_processing_failed", message) from error

    async def get_job(self, job_id: UUID) -> ExportJobStatusResponse:
        job = await self._job_store.get(job_id)
        if job is None:
            raise ExportServiceError(404, "export_job_not_found", "Export job not found")
        return job

    async def download_artifact(
        self,
        job_id: UUID,
        principal: AuthenticatedPrincipal,
    ) -> tuple[bytes, str, str]:
        job = await self.get_job(job_id)
        if principal.role.value != "admin" and job.user_id != principal.user_id:
            raise ExportServiceError(403, "export_access_denied", "Export job access denied")
        if job.status != "completed" or not job.artifacts:
            raise ExportServiceError(409, "export_artifact_not_ready", "Export artifact is not ready")
        artifact = job.artifacts[0]
        try:
            content, stored_type = await self._storage.read(artifact.storage_key)
        except StorageOperationError as error:
            raise ExportServiceError(503, "storage_unavailable", "Artifact storage is unavailable") from error
        content_type = stored_type or artifact.content_type
        filename = artifact.storage_key.rsplit("/", 1)[-1]
        return content, content_type, filename

    async def _render_content(
        self,
        request: ExportJobCreateRequest,
        request_id: str,
    ) -> tuple[str | dict, str, list[str]]:
        warnings = list(request.document.get("warnings") or [])
        content_type = content_type_for_format(request.format)
        if request.format == "markdown":
            return render_markdown(request.document), content_type, warnings
        if request.format == "json":
            return request.document, content_type, warnings
        if request.format == "jsonld":
            if request.answer is None:
                raise ExportServiceError(422, "export_answer_required", "JSON-LD export requires answer payload")
            jsonld, model_warnings = await self._enrich_jsonld(request.answer, request_id)
            warnings.extend(model_warnings)
            return jsonld, content_type, warnings
        raise ExportServiceError(422, "invalid_export_format", "Unsupported export format")

    async def _enrich_jsonld(self, answer: AnswerPayload, request_id: str) -> tuple[dict, list[str]]:
        try:
            response = await self._client.post(
                f"{self._model_url}/v1/jsonld/enrich",
                json={"answer": answer.model_dump(mode="json")},
                headers={"X-Request-ID": request_id},
            )
        except httpx.TimeoutException as error:
            raise ExportServiceError(504, "model_timeout", "Model request timed out") from error
        except httpx.HTTPError as error:
            raise ExportServiceError(503, "model_unavailable", "Model service is unavailable") from error
        if response.status_code >= 400:
            raise self._downstream_error(response, "model")
        payload = response.json()
        jsonld = payload.get("jsonld")
        if not isinstance(jsonld, dict):
            raise ExportServiceError(502, "invalid_model_response", "Model returned invalid JSON-LD data")
        warnings = payload.get("warnings") or []
        if not isinstance(warnings, list):
            warnings = []
        return jsonld, [str(item) for item in warnings]

    @staticmethod
    def _encode_content(content: str | dict, content_type: str) -> bytes:
        if isinstance(content, str):
            return content.encode("utf-8")
        if content_type == "application/ld+json":
            return json.dumps(content, ensure_ascii=False, indent=2).encode("utf-8")
        return json.dumps(content, ensure_ascii=False, indent=2).encode("utf-8")

    @staticmethod
    def _completed_response(job: ExportJobStatusResponse) -> ExportJobProcessResponse:
        artifact = job.artifacts[0] if job.artifacts else None
        return ExportJobProcessResponse(
            job_id=job.job_id,
            status="completed",
            format=job.format,
            artifacts=job.artifacts,
            content_type=artifact.content_type if artifact else "",
        )

    @staticmethod
    def _downstream_error(response: httpx.Response, service_name: str) -> ExportServiceError:
        status_code = response.status_code if 400 <= response.status_code < 600 else 502
        try:
            payload = ApiError.model_validate(response.json())
            return ExportServiceError(status_code, payload.code, payload.message)
        except (ValueError, TypeError):
            return ExportServiceError(
                status_code,
                f"{service_name}_error",
                f"{service_name} service request failed",
            )
