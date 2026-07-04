import json
from collections.abc import AsyncIterator
from uuid import UUID

import httpx
from fastapi import UploadFile, status

from shared.contracts import (
    ApiError,
    DictionaryVersionPayload,
    DocumentCatalogResponse,
    IngestionTaskPayload,
)

from ..core.config import settings


class GatewayServiceError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        query_run_id: UUID | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.query_run_id = query_run_id
        super().__init__(message)


class GatewayService:
    def __init__(
        self,
        client: httpx.AsyncClient,
        orchestrator_url: str,
        upload_limit_bytes: int,
        export_url: str = "http://export",
    ) -> None:
        self._client = client
        self._orchestrator_url = orchestrator_url.rstrip("/")
        self._export_url = export_url.rstrip("/")
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

    async def list_documents(
        self,
        authorization: str,
        request_id: str,
        status_filter: str | None = None,
        catalog_filter: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> DocumentCatalogResponse:
        params: dict[str, str | int] = {"limit": limit, "offset": offset}
        if status_filter is not None:
            params["status"] = status_filter
        if catalog_filter is not None:
            params["filter"] = catalog_filter
        response = await self._request(
            "GET",
            "/documents",
            authorization,
            request_id,
            params=params,
        )
        if response.status_code != status.HTTP_200_OK:
            raise self._downstream_error(response)
        return DocumentCatalogResponse.model_validate(response.json())

    async def delete_document(
        self,
        document_id: str,
        authorization: str,
        request_id: str,
    ) -> dict:
        response = await self._request(
            "DELETE",
            f"/documents/{document_id}",
            authorization,
            request_id,
        )
        if response.status_code != status.HTTP_200_OK:
            raise self._downstream_error(response)
        return self._json_payload(response)

    async def get_review_queue(
        self,
        authorization: str,
        request_id: str,
        status_filter: str,
        limit: int,
    ) -> dict:
        return await self._get_json(
            "/review/queue",
            authorization,
            request_id,
            params={"status": status_filter, "limit": limit},
        )

    async def post_review_queue(
        self,
        authorization: str,
        request_id: str,
        status_filter: str,
        limit: int,
    ) -> dict:
        response = await self._request(
            "POST",
            "/review/queue",
            authorization,
            request_id,
            json_body={"status": status_filter, "limit": limit},
        )
        if response.status_code != status.HTTP_200_OK:
            raise self._downstream_error(response)
        return self._json_payload(response)

    async def review_decision(
        self,
        payload: dict,
        authorization: str,
        request_id: str,
    ) -> dict:
        response = await self._request(
            "POST",
            "/review/decisions",
            authorization,
            request_id,
            json_body=payload,
        )
        if response.status_code != status.HTTP_200_OK:
            raise self._downstream_error(response)
        return self._json_payload(response)

    async def upload_dictionary(
        self,
        package: UploadFile,
        authorization: str,
        request_id: str,
    ) -> IngestionTaskPayload:
        await self._measure_uploads([package])
        response = await self._request(
            "POST",
            "/dictionaries/upload",
            authorization,
            request_id,
            files=[(
                "package",
                (package.filename, package.file, package.content_type or "application/zip"),
            )],
        )
        if response.status_code != status.HTTP_202_ACCEPTED:
            raise self._downstream_error(response)
        return self._task_payload(response)

    async def list_dictionaries(
        self, authorization: str, request_id: str
    ) -> list[DictionaryVersionPayload]:
        response = await self._request("GET", "/dictionaries", authorization, request_id)
        if response.status_code != status.HTTP_200_OK:
            raise self._downstream_error(response)
        try:
            return [DictionaryVersionPayload.model_validate(item) for item in response.json()]
        except (TypeError, ValueError) as error:
            raise GatewayServiceError(502, "invalid_orchestrator_response", "Orchestrator returned invalid data") from error

    async def get_active_dictionary(
        self, authorization: str, request_id: str
    ) -> DictionaryVersionPayload:
        try:
            return DictionaryVersionPayload.model_validate(
                await self._get_json("/dictionaries/active", authorization, request_id)
            )
        except ValueError as error:
            raise GatewayServiceError(
                502, "invalid_orchestrator_response", "Orchestrator returned invalid data"
            ) from error

    async def activate_dictionary(
        self,
        version_id: UUID,
        authorization: str,
        request_id: str,
    ) -> DictionaryVersionPayload:
        response = await self._request(
            "POST", f"/dictionaries/{version_id}/activate", authorization, request_id, json_body={}
        )
        if response.status_code != status.HTTP_200_OK:
            raise self._downstream_error(response)
        try:
            return DictionaryVersionPayload.model_validate(self._json_payload(response))
        except ValueError as error:
            raise GatewayServiceError(
                502, "invalid_orchestrator_response", "Orchestrator returned invalid data"
            ) from error

    async def run_query(
        self,
        payload: dict,
        authorization: str,
        request_id: str,
    ) -> dict:
        response = await self._request(
            "POST",
            "/query/run",
            authorization,
            request_id,
            json_body=self._with_scientific_query_flag(payload),
        )
        if response.status_code != status.HTTP_200_OK:
            raise self._downstream_error(response)
        return self._json_payload(response)

    async def stream_query(
        self,
        payload: dict,
        authorization: str,
        request_id: str,
    ) -> AsyncIterator[bytes]:
        try:
            async with self._client.stream(
                "POST",
                f"{self._orchestrator_url}/query/stream",
                json=self._with_scientific_query_flag(payload),
                headers={"Authorization": authorization, "X-Request-ID": request_id},
            ) as response:
                if response.status_code != status.HTTP_200_OK:
                    body = await response.aread()
                    raise self._downstream_error_from_body(response.status_code, body)
                async for chunk in response.aiter_bytes():
                    yield chunk
        except httpx.TimeoutException as error:
            raise GatewayServiceError(504, "orchestrator_timeout", "Orchestrator request timed out") from error
        except httpx.HTTPError as error:
            raise GatewayServiceError(503, "orchestrator_unavailable", "Orchestrator is unavailable") from error

    async def get_query_run(
        self,
        run_id: UUID,
        authorization: str,
        request_id: str,
    ) -> dict:
        return await self._get_json(f"/runs/{run_id}", authorization, request_id)

    async def get_source(
        self,
        source_span_id: str,
        authorization: str,
        request_id: str,
    ) -> dict:
        return await self._get_json(
            f"/source/{source_span_id}", authorization, request_id
        )

    async def export_query_run(
        self,
        payload: dict,
        authorization: str,
        request_id: str,
    ) -> dict:
        response = await self._request(
            "POST",
            "/export",
            authorization,
            request_id,
            json_body=payload,
        )
        if response.status_code != status.HTTP_200_OK:
            raise self._downstream_error(response)
        return self._json_payload(response)

    async def download_export_artifact(
        self,
        job_id: UUID,
        authorization: str,
        request_id: str,
    ) -> httpx.Response:
        response = await self._client.get(
            f"{self._export_url}/v1/jobs/{job_id}/artifact",
            headers={
                "Authorization": authorization,
                "X-Request-ID": request_id,
            },
        )
        if response.status_code != status.HTTP_200_OK:
            raise self._downstream_error(response)
        return response

    async def get_subgraph(
        self,
        run_id: UUID,
        authorization: str,
        request_id: str,
    ) -> dict:
        return await self._get_json(
            "/graph/subgraph",
            authorization,
            request_id,
            params={"run_id": str(run_id)},
        )

    async def search(
        self,
        params: list[tuple[str, str]],
        authorization: str,
        request_id: str,
    ) -> dict:
        return await self._get_json(
            "/search", authorization, request_id, params=params
        )

    async def _get_json(
        self,
        path: str,
        authorization: str,
        request_id: str,
        params: dict | list[tuple[str, str]] | None = None,
    ) -> dict:
        response = await self._request(
            "GET",
            path,
            authorization,
            request_id,
            params=params,
        )
        if response.status_code != status.HTTP_200_OK:
            raise self._downstream_error(response)
        return self._json_payload(response)

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
        json_body: dict | None = None,
        params: dict | list[tuple[str, str]] | None = None,
    ) -> httpx.Response:
        try:
            return await self._client.request(
                method,
                f"{self._orchestrator_url}{path}",
                files=files,
                json=json_body,
                headers={"Authorization": authorization, "X-Request-ID": request_id},
                params=params,
            )
        except httpx.TimeoutException as error:
            raise GatewayServiceError(504, "orchestrator_timeout", "Orchestrator request timed out") from error
        except httpx.HTTPError as error:
            raise GatewayServiceError(503, "orchestrator_unavailable", "Orchestrator is unavailable") from error

    @staticmethod
    def _with_scientific_query_flag(payload: dict) -> dict:
        body = dict(payload)
        filters = dict(body.get("filters") or {})
        if "top1_scientific_query" not in filters and settings.top1_scientific_query_enabled:
            filters["top1_scientific_query"] = True
        body["filters"] = filters
        return body

    @staticmethod
    def _downstream_error_from_body(status_code: int, body: bytes) -> GatewayServiceError:
        code_status = status_code if 400 <= status_code < 600 else 502
        try:
            payload = ApiError.model_validate(json.loads(body))
            return GatewayServiceError(
                code_status,
                payload.code,
                payload.message,
                payload.query_run_id,
            )
        except (ValueError, TypeError):
            return GatewayServiceError(
                code_status, "downstream_error", "Downstream service request failed"
            )

    @staticmethod
    def _downstream_error(response: httpx.Response) -> GatewayServiceError:
        status_code = response.status_code if 400 <= response.status_code < 600 else 502
        try:
            payload = ApiError.model_validate(response.json())
            return GatewayServiceError(
                status_code,
                payload.code,
                payload.message,
                payload.query_run_id,
            )
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

    @staticmethod
    def _json_payload(response: httpx.Response) -> dict:
        try:
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError
            return payload
        except ValueError as error:
            raise GatewayServiceError(
                502,
                "invalid_orchestrator_response",
                "Orchestrator returned invalid data",
            ) from error
