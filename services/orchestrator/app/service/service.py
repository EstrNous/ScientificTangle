import json
import time
from uuid import UUID

import httpx
from fastapi import UploadFile, status

from infra.postgres.orchestrator_db import (
    IngestionTask,
    IngestionTaskRepository,
    QueryRun,
    QueryRunRepository,
)
from shared.contracts import (
    AnswerPayload,
    ApiError,
    AuditEvent,
    EvidenceBundle,
    GraphSubgraph,
    IngestionReport,
    IngestionTaskPayload,
    IngestionTaskStatus,
    KnowledgeIngestionRequest,
    KnowledgeIngestionResponse,
    NormalizeStoredSourcesRequest,
    NormalizeStoredSourcesResponse,
    QueryIR,
    QueryRunPayload,
    QueryRunStatus,
    RetrievalIndexRequest,
    RetrievalIndexResponse,
    SearchResultPayload,
    SourcePayload,
    UserRole,
)
from shared.security import AuthenticatedPrincipal


class OrchestratorServiceError(Exception):
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


class OrchestratorService:
    def __init__(
        self,
        repository: IngestionTaskRepository,
        client: httpx.AsyncClient,
        ingestion_url: str,
        knowledge_url: str,
        retrieval_url: str,
        model_url: str,
        query_repository: QueryRunRepository | None = None,
    ) -> None:
        self._repository = repository
        self._client = client
        self._ingestion_url = ingestion_url.rstrip("/")
        self._knowledge_url = knowledge_url.rstrip("/")
        self._retrieval_url = retrieval_url.rstrip("/")
        self._model_url = model_url.rstrip("/")
        self._query_repository = query_repository

    async def start_ingestion_task(
        self,
        principal: AuthenticatedPrincipal,
        files: list[UploadFile],
        authorization: str,
        request_id: str,
    ) -> tuple[IngestionTaskPayload, UUID]:
        task = await self._repository.create(principal.user_id)
        try:
            report = await self._store_sources(
                task.id,
                files,
                authorization,
                request_id,
            )
            processing_task = await self._repository.mark_processing(task, report)
            return self._payload(processing_task), task.id
        except OrchestratorServiceError as error:
            await self._repository.mark_failed(task, error.message)
            raise

    async def continue_ingestion_task(
        self,
        task_id: UUID,
        user_id: UUID,
        authorization: str,
        request_id: str,
        session_factory,
    ) -> None:
        async with session_factory() as session:
            repository = IngestionTaskRepository(session)
            task = await repository.get(task_id)
            if task is None:
                return
            try:
                report = IngestionReport.model_validate(task.report or {})
                await self._run_ingestion_pipeline(
                    repository,
                    task,
                    user_id,
                    report,
                    authorization,
                    request_id,
                )
            except OrchestratorServiceError as error:
                await repository.mark_failed(task, error.message)
            except (KeyError, TypeError, ValueError):
                await repository.mark_failed(task, "Ingestion pipeline returned invalid data")

    async def create_task(
        self,
        principal: AuthenticatedPrincipal,
        files: list[UploadFile],
        authorization: str,
        request_id: str,
    ) -> IngestionTaskPayload:
        payload, task_id = await self.start_ingestion_task(
            principal, files, authorization, request_id
        )
        task = await self._repository.get(task_id)
        if task is None:
            return payload
        report = IngestionReport.model_validate(task.report or {})
        try:
            return await self._run_ingestion_pipeline(
                self._repository,
                task,
                principal.user_id,
                report,
                authorization,
                request_id,
            )
        except OrchestratorServiceError as error:
            await self._repository.mark_failed(task, error.message)
            raise
        except (KeyError, TypeError, ValueError):
            await self._repository.mark_failed(task, "Ingestion pipeline returned invalid data")
            raise

    async def _store_sources(
        self,
        task_id: UUID,
        files: list[UploadFile],
        authorization: str,
        request_id: str,
    ) -> IngestionReport:
        multipart = [
            (
                "files",
                (
                    upload.filename,
                    upload.file,
                    upload.content_type or "application/octet-stream",
                ),
            )
            for upload in files
        ]
        try:
            response = await self._client.post(
                f"{self._ingestion_url}/ingestion/tasks/{task_id}/sources",
                files=multipart,
                headers={"Authorization": authorization, "X-Request-ID": request_id},
            )
        except httpx.TimeoutException as error:
            raise OrchestratorServiceError(
                504,
                "ingestion_timeout",
                "Ingestion service request timed out",
            ) from error
        except httpx.HTTPError as error:
            raise OrchestratorServiceError(
                503,
                "ingestion_unavailable",
                "Ingestion service is unavailable",
            ) from error
        if response.status_code != status.HTTP_201_CREATED:
            raise self._downstream_error(response, "ingestion")
        try:
            return IngestionReport.model_validate(response.json())
        except ValueError as error:
            raise OrchestratorServiceError(
                502,
                "invalid_ingestion_response",
                "Ingestion service returned invalid data",
            ) from error

    async def _run_ingestion_pipeline(
        self,
        repository: IngestionTaskRepository,
        task: IngestionTask,
        user_id: UUID,
        report: IngestionReport,
        authorization: str,
        request_id: str,
    ) -> IngestionTaskPayload:
        normalized = NormalizeStoredSourcesResponse.model_validate(
            await self._request_downstream(
                "POST",
                self._ingestion_url,
                f"/ingestion/tasks/{task.id}/normalize",
                NormalizeStoredSourcesRequest(sources=report.sources).model_dump(mode="json"),
                request_id,
                "ingestion",
                authorization,
            )
        )
        if not normalized.documents:
            raise OrchestratorServiceError(
                422,
                "normalization_empty",
                "No supported documents were normalized",
            )
        knowledge_results = []
        for document in normalized.documents:
            knowledge_results.append(
                KnowledgeIngestionResponse.model_validate(
                    await self._request_downstream(
                        "POST",
                        self._knowledge_url,
                        "/v1/documents/extract",
                        KnowledgeIngestionRequest(document=document).model_dump(mode="json"),
                        request_id,
                        "knowledge",
                    )
                )
            )
        if any(result.graph_write.mode != "live" for result in knowledge_results):
            raise OrchestratorServiceError(
                503,
                "storage_adapter_not_ready",
                "Neo4j storage adapter is not ready",
            )
        retrieval_result = RetrievalIndexResponse.model_validate(
            await self._request_downstream(
                "POST",
                self._retrieval_url,
                "/v1/documents/index",
                RetrievalIndexRequest(
                    documents=normalized.documents,
                    knowledge_results=knowledge_results,
                ).model_dump(mode="json"),
                request_id,
                "retrieval",
            )
        )
        if retrieval_result.vector_write.mode != "live":
            raise OrchestratorServiceError(
                503,
                "storage_adapter_not_ready",
                "Qdrant storage adapter is not ready",
            )
        warnings = [*report.warnings, *normalized.warnings]
        for result in knowledge_results:
            warnings.extend(result.warnings)
            warnings.extend(result.graph_write.warnings)
        warnings.extend(retrieval_result.warnings)
        warnings.extend(retrieval_result.vector_write.warnings)
        completed_report = IngestionReport(
            sources=report.sources,
            warnings=list(dict.fromkeys(warnings)),
            normalized_documents=normalized.documents,
            documents_count=len(normalized.documents),
            source_spans_count=sum(
                len(document.source_spans)
                for document in normalized.documents
            ),
            tables_count=sum(
                len(document.table_blocks)
                for document in normalized.documents
            ),
            indexed_points_count=retrieval_result.vector_write.records_count,
            extracted_claims_count=sum(
                len(result.extraction.get("confirmed", []))
                for result in knowledge_results
                if isinstance(result.extraction, dict)
            ),
            candidates_count=sum(
                len(result.extraction.get("candidates", []))
                for result in knowledge_results
                if isinstance(result.extraction, dict)
            ),
        )
        completed_task = await repository.mark_completed(task, completed_report)
        await repository.record_audit_event(
            user_id,
            "ingestion_upload",
            "ingestion_task",
            str(task.id),
            {
                "documents_count": completed_report.documents_count,
                "source_spans_count": completed_report.source_spans_count,
                "indexed_points_count": completed_report.indexed_points_count,
            },
            request_id,
        )
        return self._payload(completed_task)

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
        question: str,
        filters: dict,
        request_id: str,
        limit: int,
    ) -> QueryRunPayload:
        repository = self._require_query_repository()
        run = await repository.create(principal.user_id, question, request_id)
        await repository.record_audit_event(
            principal.user_id,
            "query_created",
            "query_run",
            str(run.id),
            {"question": question},
            request_id,
        )
        started_at = time.perf_counter()
        await repository.mark_processing(run)
        try:
            retrieval_response = await self._request_downstream(
                "POST",
                self._retrieval_url,
                "/v1/query",
                {
                    "question": question,
                    "filters": filters,
                    "access_roles": [principal.role.value],
                    "limit": limit,
                },
                request_id,
                "retrieval",
            )
            query_ir = QueryIR.model_validate(retrieval_response["query_ir"])
            evidence_bundle = EvidenceBundle.model_validate(retrieval_response["evidence_bundle"])
            retrieval_trace = retrieval_response.get("retrieval_trace", {})
            warnings = list(retrieval_response.get("warnings", []))
            graph = GraphSubgraph()
            if evidence_bundle.evidence_items:
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
                evidence_bundle.gaps = [
                    gap.get("description", str(gap))
                    for gap in gaps_response.get("gaps", [])
                ]
                evidence_bundle.has_gaps = bool(evidence_bundle.gaps)
                graph = GraphSubgraph.model_validate(
                    await self._request_downstream(
                        "POST",
                        self._knowledge_url,
                        "/v1/graph/subgraph",
                        {
                            "claim_ids": sorted(
                                {
                                    claim_id
                                    for item in evidence_bundle.evidence_items
                                    for claim_id in item.claim_ids
                                }
                            ),
                            "entity_ids": sorted(
                                {
                                    entity_id
                                    for item in evidence_bundle.evidence_items
                                    for entity_id in item.entity_ids
                                }
                            ),
                            "source_span_ids": [
                                item.source_span.id
                                for item in evidence_bundle.evidence_items
                            ],
                        },
                        request_id,
                        "knowledge",
                    )
                )
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
                warnings.extend(gaps_response.get("warnings", []))
                warnings.extend(answer_response.get("warnings", []))
                for unsupported in answer_response.get("unsupported_warnings", []):
                    if not isinstance(unsupported, dict):
                        continue
                    reason_codes = unsupported.get("reason_codes") or ["unsupported_claim"]
                    warnings.extend(str(code) for code in reason_codes)
            else:
                warning = "insufficient_accessible_evidence"
                warnings.append(warning)
                evidence_bundle.has_gaps = True
                if warning not in evidence_bundle.gaps:
                    evidence_bundle.gaps.append(warning)
                await repository.record_audit_event(
                    principal.user_id,
                    "filtered_sources",
                    "query_run",
                    str(run.id),
                    {"retrieved": retrieval_trace.get("retrieved", 0), "accessible": 0},
                    request_id,
                )
                answer = AnswerPayload(
                    query_ir=query_ir,
                    evidence_bundle=evidence_bundle,
                    answer_text="Недостаточно доступных доказательств для подтверждённого ответа.",
                    confidence=0.0,
                    sources_count=0,
                    model_used="none",
                )
            latency_ms = round((time.perf_counter() - started_at) * 1000)
            await repository.mark_completed(
                run,
                query_ir,
                evidence_bundle,
                answer,
                graph,
                retrieval_trace,
                list(dict.fromkeys(warnings)),
                latency_ms,
            )
            return self._query_payload(run)
        except OrchestratorServiceError as error:
            latency_ms = round((time.perf_counter() - started_at) * 1000)
            await repository.mark_failed(run, error.code, error.message, latency_ms)
            error.query_run_id = run.id
            raise
        except (KeyError, TypeError, ValueError) as error:
            latency_ms = round((time.perf_counter() - started_at) * 1000)
            code = "invalid_query_pipeline_response"
            message = "Query pipeline returned invalid data"
            await repository.mark_failed(run, code, message, latency_ms)
            raise OrchestratorServiceError(502, code, message, run.id) from error

    async def get_run(
        self,
        run_id: UUID,
        principal: AuthenticatedPrincipal,
    ) -> QueryRunPayload:
        run = await self._require_query_repository().get(run_id)
        if run is None or (
            principal.role != UserRole.ADMIN and run.user_id != principal.user_id
        ):
            raise OrchestratorServiceError(404, "query_run_not_found", "Query run not found")
        return self._query_payload(run)

    async def get_source(
        self,
        source_span_id: str,
        principal: AuthenticatedPrincipal,
        request_id: str,
    ) -> SourcePayload:
        payload = SourcePayload.model_validate(
            await self._request_downstream(
                "POST",
                self._retrieval_url,
                f"/v1/sources/{source_span_id}/resolve",
                {"access_roles": [principal.role.value]},
                request_id,
                "retrieval",
            )
        )
        await self._require_query_repository().record_audit_event(
            principal.user_id,
            "source_viewed",
            "source_span",
            source_span_id,
            {"document_id": payload.source_span.document_id},
            request_id,
        )
        return payload

    async def get_subgraph(
        self,
        run_id: UUID,
        principal: AuthenticatedPrincipal,
    ) -> GraphSubgraph:
        return (await self.get_run(run_id, principal)).graph_subgraph

    async def search(
        self,
        principal: AuthenticatedPrincipal,
        question: str,
        filters: dict,
        limit: int,
        request_id: str,
    ) -> SearchResultPayload:
        return SearchResultPayload.model_validate(
            await self._request_downstream(
                "POST",
                self._retrieval_url,
                "/v1/search",
                {
                    "question": question,
                    "filters": filters,
                    "access_roles": [principal.role.value],
                    "limit": limit,
                },
                request_id,
                "retrieval",
            )
        )

    async def list_audit_events(self, limit: int = 200) -> list[AuditEvent]:
        rows = await self._repository.list_audit_events(limit)
        events = []
        for row in rows:
            details = row.get("details") or {}
            if isinstance(details, str):
                try:
                    details = json.loads(details)
                except (TypeError, ValueError):
                    details = {}
            events.append(
                AuditEvent(
                    id=str(row["id"]),
                    user=str(row.get("user_id") or ""),
                    role="",
                    action=str(row["action"]),
                    object=str(row.get("resource_id") or ""),
                    timestamp=row["created_at"].isoformat() if row.get("created_at") else "",
                    source_span_id=details.get("source_span_id"),
                )
            )
        return events

    def _require_query_repository(self) -> QueryRunRepository:
        if self._query_repository is None:
            raise RuntimeError("query_repository_not_configured")
        return self._query_repository

    @staticmethod
    def _query_payload(run: QueryRun) -> QueryRunPayload:
        return QueryRunPayload(
            id=run.id,
            status=QueryRunStatus(run.status),
            question=run.raw_question,
            query_ir=QueryIR.model_validate(run.query_ir) if run.query_ir else None,
            evidence_bundle=(
                EvidenceBundle.model_validate(run.evidence_bundle)
                if run.evidence_bundle
                else None
            ),
            answer=AnswerPayload.model_validate(run.answer) if run.answer else None,
            graph_subgraph=GraphSubgraph.model_validate(run.graph_subgraph or {}),
            retrieval_trace=run.retrieval_trace or {},
            warnings=run.warnings or [],
            error_code=run.error_code,
            error_message=run.error_message,
            request_id=run.request_id,
            latency_ms=run.latency_ms,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

    async def _request_downstream(
        self,
        method: str,
        base_url: str,
        path: str,
        payload: dict,
        request_id: str,
        service_name: str,
        authorization: str | None = None,
    ) -> dict:
        headers = {"X-Request-ID": request_id}
        if authorization is not None:
            headers["Authorization"] = authorization
        try:
            response = await self._client.request(
                method,
                f"{base_url}{path}",
                json=payload,
                headers=headers,
            )
            if response.status_code >= 400:
                raise self._downstream_error(response, service_name)
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
    def _downstream_error(
        response: httpx.Response,
        service_name: str,
    ) -> OrchestratorServiceError:
        status_code = response.status_code if 400 <= response.status_code < 600 else 502
        try:
            payload = ApiError.model_validate(response.json())
            return OrchestratorServiceError(status_code, payload.code, payload.message)
        except (ValueError, TypeError):
            return OrchestratorServiceError(
                status_code,
                f"{service_name}_error",
                f"{service_name} service request failed",
            )
