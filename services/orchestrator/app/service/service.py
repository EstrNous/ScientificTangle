import json
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
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
    AuditEvent,
    DictionaryIngestionReport,
    DictionaryPackagePayload,
    DictionaryVersionPayload,
    EvidenceBundle,
    ExportFormatStatus,
    ExportPayload,
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
    TaskKind,
    UserRole,
)
from shared.security import AuthenticatedPrincipal

from ..core.config import settings
from .base import BaseService, OrchestratorServiceError
from .query_stream import (
    QueryEventEmitter,
    auth_context,
    emit_answer_chunks,
    emit_phase,
    emit_retrieval_trace,
    terminal_phase,
    wrap_stream_query,
)
from .scientific_query import (
    access_levels_for_role,
    apply_conflict_signals,
    apply_table_extraction_method,
    build_verification_artifacts,
    graph_record_candidates,
    local_verification_reason_codes,
    merge_candidate_items,
    merge_graph_exact_evidence,
    partition_verified_evidence,
    planner_selects_graph,
    planner_selects_table,
    scientific_query_enabled,
)


class OrchestratorService(BaseService):
    def __init__(
        self,
        repository: IngestionTaskRepository,
        client: httpx.AsyncClient,
        ingestion_url: str,
        knowledge_url: str,
        retrieval_url: str,
        model_url: str,
        query_repository: QueryRunRepository | None = None,
        enforce_active_dictionary: bool = True,
    ) -> None:
        super().__init__(client)
        self._repository = repository
        self._ingestion_url = ingestion_url.rstrip("/")
        self._knowledge_url = knowledge_url.rstrip("/")
        self._retrieval_url = retrieval_url.rstrip("/")
        self._model_url = model_url.rstrip("/")
        self._query_repository = query_repository
        self._enforce_active_dictionary = enforce_active_dictionary

    async def start_ingestion_task(
        self,
        principal: AuthenticatedPrincipal,
        files: list[UploadFile],
        authorization: str,
        request_id: str,
    ) -> tuple[IngestionTaskPayload, UUID]:
        if self._enforce_active_dictionary:
            active_dictionary = await self._active_dictionary(request_id)
            task = await self._repository.create(
                principal.user_id,
                TaskKind.DOCUMENT_INGESTION,
                active_dictionary.id,
            )
        else:
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
        role: str = "",
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
                    role,
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
                principal.role.value,
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
        role: str,
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
        if task.dictionary_version_id is not None:
            for document in normalized.documents:
                document.metadata["dictionary_version_id"] = str(task.dictionary_version_id)
        knowledge_results = []
        for document in normalized.documents:
            knowledge_results.append(
                KnowledgeIngestionResponse.model_validate(
                    await self._request_downstream(
                        "POST",
                        self._knowledge_url,
                        "/v1/documents/extract",
                        KnowledgeIngestionRequest(
                            document=document,
                            dictionary_version_id=task.dictionary_version_id,
                        ).model_dump(mode="json"),
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
                "role": role,
                "status": "completed",
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

    async def upload_dictionary(
        self,
        principal: AuthenticatedPrincipal,
        package: UploadFile,
        authorization: str,
        request_id: str,
    ) -> IngestionTaskPayload:
        task = await self._repository.create(
            principal.user_id,
            TaskKind.DICTIONARY_INGESTION,
        )
        await self._repository.record_audit_event(
            principal.user_id,
            "dictionary_upload_started",
            "ingestion_task",
            str(task.id),
            {"filename": package.filename or "", "status": "started"},
            request_id,
        )
        try:
            response = await self._client.post(
                f"{self._ingestion_url}/ingestion/dictionaries/{task.id}/package",
                files={
                    "package": (
                        package.filename,
                        package.file,
                        package.content_type or "application/zip",
                    )
                },
                headers={"Authorization": authorization, "X-Request-ID": request_id},
            )
            if response.status_code >= 400:
                raise self._downstream_error(response, "ingestion")
            dictionary_package = DictionaryPackagePayload.model_validate(response.json())
            await self._repository.mark_processing(
                task,
                DictionaryIngestionReport(
                    version=dictionary_package.version,
                    package_sha256=dictionary_package.package_sha256,
                    files_count=len(dictionary_package.files),
                    entries_count=sum(len(item.entries) for item in dictionary_package.files),
                ),
            )
            version = DictionaryVersionPayload.model_validate(
                await self._request_downstream(
                    "POST",
                    self._knowledge_url,
                    "/v1/dictionaries",
                    {
                        "package": dictionary_package.model_dump(mode="json"),
                        "uploaded_by": str(principal.user_id),
                    },
                    request_id,
                    "knowledge",
                )
            )
            task.dictionary_version_id = version.id
            report = DictionaryIngestionReport(
                dictionary_version_id=version.id,
                version=version.version,
                package_sha256=version.package_sha256,
                files_count=len(version.files),
                entries_count=sum(len(item.entries) for item in version.files),
            )
            completed = await self._repository.mark_completed(task, report)
            await self._repository.record_audit_event(
                principal.user_id,
                "dictionary_upload_completed",
                "dictionary_version",
                str(version.id),
                {"version": version.version, "status": "completed"},
                request_id,
            )
            return self._payload(completed)
        except (OrchestratorServiceError, ValueError) as error:
            message = error.message if isinstance(error, OrchestratorServiceError) else "Dictionary package is invalid"
            await self._repository.mark_failed(task, message)
            await self._repository.record_audit_event(
                principal.user_id,
                "dictionary_validation_failed",
                "ingestion_task",
                str(task.id),
                {"status": "failed", "message": message},
                request_id,
            )
            if isinstance(error, OrchestratorServiceError):
                raise
            raise OrchestratorServiceError(502, "invalid_dictionary_response", message) from error

    async def list_dictionaries(self, request_id: str) -> list[DictionaryVersionPayload]:
        payload = await self._request_downstream(
            "GET", self._knowledge_url, "/v1/dictionaries", {}, request_id, "knowledge"
        )
        if not isinstance(payload, list):
            raise OrchestratorServiceError(502, "invalid_dictionary_response", "Knowledge returned invalid data")
        try:
            return [DictionaryVersionPayload.model_validate(item) for item in payload]
        except ValueError as error:
            raise OrchestratorServiceError(
                502, "invalid_dictionary_response", "Knowledge returned invalid dictionary data"
            ) from error

    async def get_active_dictionary(self, request_id: str) -> DictionaryVersionPayload:
        return await self._fetch_active_dictionary(request_id)

    async def activate_dictionary(
        self,
        principal: AuthenticatedPrincipal,
        version_id: UUID,
        request_id: str,
    ) -> DictionaryVersionPayload:
        try:
            version = DictionaryVersionPayload.model_validate(
                await self._request_downstream(
                    "POST",
                    self._knowledge_url,
                    f"/v1/dictionaries/{version_id}/activate",
                    {},
                    request_id,
                    "knowledge",
                )
            )
        except ValueError as error:
            raise OrchestratorServiceError(
                502, "invalid_dictionary_response", "Knowledge returned invalid dictionary data"
            ) from error
        await self._require_query_repository().record_audit_event(
            principal.user_id,
            "dictionary_activated",
            "dictionary_version",
            str(version.id),
            {"version": version.version, "status": "active"},
            request_id,
        )
        return version

    async def run_query(
        self,
        principal: AuthenticatedPrincipal,
        question: str,
        filters: dict,
        request_id: str,
        limit: int,
    ) -> QueryRunPayload:
        return QueryRunPayload.model_validate(
            await self._execute_query(principal, question, filters, request_id, limit)
        )

    async def stream_query(
        self,
        principal: AuthenticatedPrincipal,
        question: str,
        filters: dict,
        request_id: str,
        limit: int,
    ) -> AsyncIterator[str]:
        async def runner(on_event: QueryEventEmitter) -> dict:
            return await self._execute_query(
                principal,
                question,
                filters,
                request_id,
                limit,
                on_event=on_event,
            )

        async for chunk in wrap_stream_query(runner, principal):
            yield chunk

    async def _execute_query(
        self,
        principal: AuthenticatedPrincipal,
        question: str,
        filters: dict,
        request_id: str,
        limit: int,
        on_event: QueryEventEmitter | None = None,
    ) -> dict:
        repository = self._require_query_repository()
        if self._enforce_active_dictionary:
            active_dictionary = await self._active_dictionary(request_id)
            run = await repository.create(
                principal.user_id,
                question,
                request_id,
                active_dictionary.id,
            )
        else:
            active_dictionary = None
            run = await repository.create(principal.user_id, question, request_id)
        await repository.record_audit_event(
            principal.user_id,
            "query_created",
            "query_run",
            str(run.id),
            {"question": question, "role": principal.role.value, "status": "started"},
            request_id,
        )
        started_at = time.perf_counter()
        await repository.mark_processing(run)
        await emit_phase(on_event, "parsing")
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
                    "dictionary_version_id": str(active_dictionary.id) if active_dictionary else None,
                },
                request_id,
                "retrieval",
            )
            query_ir = QueryIR.model_validate(retrieval_response["query_ir"])
            evidence_bundle = EvidenceBundle.model_validate(retrieval_response["evidence_bundle"])
            retrieval_trace = dict(retrieval_response.get("retrieval_trace", {}))
            warnings = list(retrieval_response.get("warnings", []))
            retrieved_count = int(retrieval_trace.get("retrieved", 0))
            accessible_count = int(retrieval_trace.get("accessible", 0))
            if retrieved_count > accessible_count:
                await repository.record_audit_event(
                    principal.user_id,
                    "filtered_sources",
                    "query_run",
                    str(run.id),
                    {
                        "retrieved": retrieved_count,
                        "accessible": accessible_count,
                        "role": principal.role.value,
                        "status": "filtered",
                    },
                    request_id,
                )
            await emit_phase(on_event, "retrieval")
            await emit_retrieval_trace(on_event, retrieval_trace)
            candidate_items: list[dict] = []
            if scientific_query_enabled(settings.top1_scientific_query_enabled, filters):
                evidence_bundle, retrieval_trace, candidate_items, scientific_warnings = (
                    await self._enrich_scientific_query(
                        query_ir,
                        evidence_bundle,
                        retrieval_trace,
                        principal,
                        request_id,
                    )
                )
                warnings.extend(scientific_warnings)
            else:
                retrieval_trace["pipeline_mode"] = "legacy"
            await emit_phase(on_event, "verification")
            graph = GraphSubgraph()
            if evidence_bundle.evidence_items:
                await emit_phase(on_event, "synthesis")
                gaps_response = await self._request_downstream(
                    "POST",
                    self._model_url,
                    "/v1/gaps/suggest",
                    {
                        "query_ir": query_ir.model_dump(mode="json"),
                        "evidence_bundle": evidence_bundle.model_dump(mode="json"),
                        "candidates": candidate_items,
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
                            "access_levels": (
                                ["public", "internal", "restricted"]
                                if principal.role == UserRole.ADMIN
                                else ["public", "internal"]
                                if principal.role in {UserRole.RESEARCHER, UserRole.ANALYST, UserRole.MANAGER}
                                else ["public"]
                            ),
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
                        "candidate_items": candidate_items,
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
                await emit_answer_chunks(on_event, answer.answer_text)
            else:
                warning = "insufficient_accessible_evidence"
                warnings.append(warning)
                evidence_bundle.has_gaps = True
                if warning not in evidence_bundle.gaps:
                    evidence_bundle.gaps.append(warning)
                answer = AnswerPayload(
                    query_ir=query_ir,
                    evidence_bundle=evidence_bundle,
                    answer_text="Недостаточно доступных доказательств для подтверждённого ответа.",
                    confidence=0.0,
                    sources_count=0,
                    model_used="none",
                )
                await emit_answer_chunks(on_event, answer.answer_text)
            await emit_phase(on_event, "citations")
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
            await repository.record_audit_event(
                principal.user_id,
                "answer_generated",
                "query_run",
                str(run.id),
                {
                    "role": principal.role.value,
                    "status": "completed",
                    "confidence": answer.confidence,
                    "sources_count": answer.sources_count,
                    "warnings": list(dict.fromkeys(warnings)),
                    "has_gaps": evidence_bundle.has_gaps,
                    "has_conflicts": evidence_bundle.has_conflicts,
                },
                request_id,
            )
            await emit_phase(
                on_event,
                terminal_phase(answer.confidence, list(dict.fromkeys(warnings)), evidence_bundle),
            )
            payload = self._query_payload(run).model_dump(mode="json")
            payload["auth_context"] = auth_context(principal)
            return payload
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

    async def _enrich_scientific_query(
        self,
        query_ir: QueryIR,
        evidence_bundle: EvidenceBundle,
        retrieval_trace: dict,
        principal: AuthenticatedPrincipal,
        request_id: str,
    ) -> tuple[EvidenceBundle, dict, list[dict], list[str]]:
        warnings: list[str] = []
        candidate_items: list[dict] = []
        retrieval_trace = {
            **retrieval_trace,
            "pipeline_mode": "top1_scientific",
            "planner_selected_graph": planner_selects_graph(retrieval_trace),
            "planner_selected_table": planner_selects_table(retrieval_trace),
        }
        graph_result: dict = {}
        if retrieval_trace["planner_selected_graph"]:
            try:
                graph_result = await self._request_downstream(
                    "POST",
                    self._knowledge_url,
                    "/v1/graph/exact-search",
                    {
                        "query_ir": query_ir.model_dump(mode="json"),
                        "access_levels": access_levels_for_role(principal.role),
                    },
                    request_id,
                    "knowledge",
                )
                evidence_bundle, graph_trace = merge_graph_exact_evidence(evidence_bundle, graph_result)
                retrieval_trace["graph_exact"] = graph_trace
                candidate_items.extend(graph_record_candidates(graph_result))
            except OrchestratorServiceError as error:
                warnings.append(f"graph_exact_fallback:{error.code}")
                retrieval_trace["graph_exact"] = {"fallback": error.code}
        if retrieval_trace["planner_selected_table"]:
            evidence_bundle = apply_table_extraction_method(evidence_bundle)
        artifacts = build_verification_artifacts(evidence_bundle)
        for artifact in artifacts:
            reason_codes = local_verification_reason_codes(query_ir, artifact["value"])
            if reason_codes:
                artifact["reason_codes"] = reason_codes
                artifact["status"] = "candidate"
        if artifacts:
            try:
                conflicts_response = await self._request_downstream(
                    "POST",
                    self._model_url,
                    "/v1/conflicts/detect",
                    {"artifacts": artifacts},
                    request_id,
                    "model",
                )
                artifacts = apply_conflict_signals(artifacts, conflicts_response.get("conflicts", []))
                warnings.extend(conflicts_response.get("warnings", []))
                retrieval_trace["verification"] = {
                    "conflicts_detected": len(conflicts_response.get("conflicts", [])),
                    "artifacts_checked": len(artifacts),
                }
            except OrchestratorServiceError as error:
                warnings.append(f"verification_fallback:{error.code}")
                retrieval_trace["verification"] = {"fallback": error.code}
        evidence_bundle, verified_candidates = partition_verified_evidence(evidence_bundle, artifacts)
        candidate_items = merge_candidate_items(candidate_items, verified_candidates)
        return evidence_bundle, retrieval_trace, candidate_items, warnings

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
            {
                "document_id": payload.source_span.document_id,
                "source_span_id": source_span_id,
                "role": principal.role.value,
                "status": "success",
            },
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

    async def export_query_run(
        self,
        principal: AuthenticatedPrincipal,
        run_id: UUID,
        export_format: str,
        request_id: str,
    ) -> ExportPayload:
        if export_format not in {"markdown", "json"}:
            raise OrchestratorServiceError(422, "invalid_export_format", "Unsupported export format")
        repository = self._require_query_repository()
        run = await repository.get(run_id)
        if run is None or (
            principal.role != UserRole.ADMIN and run.user_id != principal.user_id
        ):
            raise OrchestratorServiceError(404, "query_run_not_found", "Query run not found")
        if run.status != QueryRunStatus.COMPLETED.value:
            raise OrchestratorServiceError(
                409,
                "query_run_not_completed",
                "Export is available only for completed query runs",
            )
        if not run.query_ir or not run.evidence_bundle or not run.answer:
            raise OrchestratorServiceError(
                409,
                "query_run_incomplete",
                "Query run does not contain a complete exportable payload",
            )
        export_job = await repository.create_export_job(
            principal.user_id,
            run.id,
            export_format,
        )
        await repository.mark_export_processing(export_job)
        query_payload = self._query_payload(run)
        try:
            resolved_sources = await self._resolve_export_sources(
                query_payload,
                principal,
                request_id,
            )
        except OrchestratorServiceError as error:
            await repository.mark_export_failed(export_job, error.message)
            if error.status_code in {403, 404, 409}:
                await repository.record_audit_event(
                    principal.user_id,
                    "access_denied",
                    "export_job",
                    str(export_job.id),
                    {
                        "query_run_id": str(run.id),
                        "format": export_format,
                        "role": principal.role.value,
                        "status": "denied",
                    },
                    request_id,
                )
            raise
        generated_at = datetime.now(UTC)
        file_url = self._export_file_url(export_job.id, export_format)
        response_payload = self._build_export_payload(
            export_job.id,
            query_payload,
            resolved_sources,
            export_format,
            principal.role.value,
            file_url,
            generated_at,
        )
        await repository.mark_export_completed(export_job, response_payload, file_url)
        await repository.record_audit_event(
            principal.user_id,
            "document_exported",
            "export_job",
            str(export_job.id),
            {
                "query_run_id": str(run.id),
                "format": export_format,
                "role": principal.role.value,
                "status": "completed",
            },
            request_id,
        )
        return response_payload

    async def list_audit_events(
        self,
        limit: int = 200,
        offset: int = 0,
        action: str | None = None,
        user_id: UUID | None = None,
    ) -> list[AuditEvent]:
        rows = await self._repository.list_audit_events(
            limit=limit,
            offset=offset,
            action=action,
            user_id=user_id,
        )
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
                    user_id=str(row.get("user_id") or ""),
                    role=str(details.get("role") or ""),
                    action=str(row["action"]),
                    object=str(row.get("resource_id") or ""),
                    status=str(details.get("status") or ""),
                    resource_type=str(row.get("resource_type") or ""),
                    resource_id=str(row.get("resource_id") or ""),
                    request_id=str(row.get("request_id") or ""),
                    timestamp=row["created_at"].isoformat() if row.get("created_at") else "",
                    details=details if isinstance(details, dict) else {},
                    source_span_id=details.get("source_span_id"),
                )
            )
        return events

    def _require_query_repository(self) -> QueryRunRepository:
        if self._query_repository is None:
            raise RuntimeError("query_repository_not_configured")
        return self._query_repository

    async def _resolve_export_sources(
        self,
        payload: QueryRunPayload,
        principal: AuthenticatedPrincipal,
        request_id: str,
    ) -> list[SourcePayload]:
        evidence_bundle = payload.evidence_bundle
        if evidence_bundle is None:
            return []
        resolved_sources: list[SourcePayload] = []
        seen_ids: set[str] = set()
        for item in evidence_bundle.evidence_items:
            source_span_id = item.source_span.id
            if source_span_id in seen_ids:
                continue
            seen_ids.add(source_span_id)
            try:
                source_payload = SourcePayload.model_validate(
                    await self._request_downstream(
                        "POST",
                        self._retrieval_url,
                        f"/v1/sources/{source_span_id}/resolve",
                        {"access_roles": [principal.role.value]},
                        request_id,
                        "retrieval",
                    )
                )
            except OrchestratorServiceError as error:
                if error.status_code in {403, 404}:
                    raise OrchestratorServiceError(
                        409,
                        "export_access_changed",
                        "Export was rejected because source access changed",
                    ) from error
                raise
            resolved_sources.append(source_payload)
        return resolved_sources

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
            dictionary_version_id=getattr(run, "dictionary_version_id", None),
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

    def _build_export_payload(
        self,
        export_job_id: UUID,
        payload: QueryRunPayload,
        sources: list[SourcePayload],
        export_format: str,
        role: str,
        file_url: str,
        generated_at: datetime,
    ) -> ExportPayload:
        export_document = self._export_document(payload, sources, role, generated_at)
        content: str | dict
        content_type: str
        if export_format == "markdown":
            content = self._render_export_markdown(export_document)
            content_type = "text/markdown"
        else:
            content = export_document
            content_type = "application/json"
        return ExportPayload(
            export_job_id=export_job_id,
            query_run_id=payload.id,
            format=export_format,
            status=QueryRunStatus.COMPLETED,
            content_type=content_type,
            content=content,
            file_url=file_url,
            warnings=payload.warnings,
            format_status=self._export_format_status(),
            generated_at=generated_at,
        )

    def _export_document(
        self,
        payload: QueryRunPayload,
        sources: list[SourcePayload],
        role: str,
        generated_at: datetime,
    ) -> dict:
        evidence_bundle = payload.evidence_bundle or EvidenceBundle(query_ir=payload.query_ir or QueryIR(raw_query=payload.question))
        answer = payload.answer or AnswerPayload(
            query_ir=payload.query_ir or QueryIR(raw_query=payload.question),
            evidence_bundle=evidence_bundle,
            answer_text="",
        )
        source_entries = [
            {
                "source_span_id": source.source_span.id,
                "document_id": source.source_span.document_id,
                "document_title": source.document_title,
                "page": source.source_span.page,
                "source_type": source.source_type,
                "text": source.source_span.text,
                "link": f"/api/source/{source.source_span.id}",
                "metadata": source.metadata,
            }
            for source in sources
        ]
        evidence_entries = [
            {
                "source_span_id": item.source_span.id,
                "text": item.source_span.text,
                "relevance_score": item.relevance_score,
                "claim_ids": item.claim_ids,
                "entity_ids": item.entity_ids,
                "page": item.source_span.page,
            }
            for item in evidence_bundle.evidence_items
        ]
        return {
            "query_run_id": str(payload.id),
            "dictionary_version_id": (
                str(payload.dictionary_version_id) if payload.dictionary_version_id else None
            ),
            "question": payload.question,
            "status": payload.status.value,
            "role": role,
            "user_role": role,
            "access_scope": access_levels_for_role(UserRole(role)),
            "generated_at": generated_at.isoformat(),
            "answer": answer.answer_text,
            "confidence": answer.confidence,
            "sources_count": answer.sources_count,
            "query_ir": answer.query_ir.model_dump(mode="json"),
            "evidence": evidence_entries,
            "sources": source_entries,
            "graph": payload.graph_subgraph.model_dump(mode="json"),
            "gaps": evidence_bundle.gaps,
            "conflicts": evidence_bundle.conflicts,
            "warnings": payload.warnings,
            "retrieval_trace": payload.retrieval_trace,
            "latency_ms": payload.latency_ms,
        }

    @staticmethod
    def _export_format_status() -> list[ExportFormatStatus]:
        return [
            ExportFormatStatus(format="markdown", available=True, status="available"),
            ExportFormatStatus(format="json", available=True, status="available"),
            ExportFormatStatus(
                format="jsonld",
                available=False,
                status="backlog",
                reason="model_jsonld_enrichment_ready_but_export_wiring_deferred",
            ),
            ExportFormatStatus(
                format="pdf",
                available=False,
                status="backlog",
                reason="server_pdf_renderer_not_wired",
            ),
        ]

    @staticmethod
    def _render_export_markdown(document: dict) -> str:
        lines = [
            f"# Export for query run {document['query_run_id']}",
            "",
            f"- Question: {document['question']}",
            f"- Role: {document['role']}",
            f"- Access scope: {', '.join(document['access_scope'])}",
            f"- Dictionary version: {document['dictionary_version_id'] or ''}",
            f"- Generated at: {document['generated_at']}",
            f"- Status: {document['status']}",
            f"- Latency ms: {document['latency_ms'] if document['latency_ms'] is not None else ''}",
            "",
            "## Answer",
            "",
            str(document["answer"]),
            "",
            "## Query IR",
            "",
            "```json",
            json.dumps(document["query_ir"], ensure_ascii=False, indent=2),
            "```",
            "",
            "## Evidence",
            "",
        ]
        for item in document["evidence"]:
            lines.extend(
                [
                    f"- {item['source_span_id']} (page {item['page']}, score {item['relevance_score']})",
                    f"  {item['text']}",
                ]
            )
        lines.extend(["", "## Sources", ""])
        for source in document["sources"]:
            lines.extend(
                [
                    f"- {source['document_title']} [{source['source_span_id']}]({source['link']})",
                    f"  {source['text']}",
                ]
            )
        lines.extend(
            [
                "",
                "## Graph",
                "",
                "```json",
                json.dumps(document["graph"], ensure_ascii=False, indent=2),
                "```",
                "",
                "## Gaps",
                "",
                *([f"- {item}" for item in document["gaps"]] or ["- none"]),
                "",
                "## Conflicts",
                "",
                *([f"- {item}" for item in document["conflicts"]] or ["- none"]),
                "",
                "## Retrieval Trace",
                "",
                "```json",
                json.dumps(document["retrieval_trace"], ensure_ascii=False, indent=2),
                "```",
                "",
                "## Warnings",
                "",
                *([f"- {item}" for item in document["warnings"]] or ["- none"]),
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _export_file_url(export_job_id: UUID, export_format: str) -> str:
        extension = "md" if export_format == "markdown" else "json"
        return f"inline://export-jobs/{export_job_id}.{extension}"

    async def _active_dictionary(self, request_id: str) -> DictionaryVersionPayload:
        try:
            return await self._fetch_active_dictionary(request_id)
        except OrchestratorServiceError as error:
            if error.status_code == 404:
                raise OrchestratorServiceError(
                    409,
                    "active_dictionary_required",
                    "An active dictionary version is required",
                ) from error
            raise

    async def _fetch_active_dictionary(self, request_id: str) -> DictionaryVersionPayload:
        try:
            return DictionaryVersionPayload.model_validate(
                await self._request_downstream(
                    "GET",
                    self._knowledge_url,
                    "/v1/dictionaries/active",
                    {},
                    request_id,
                    "knowledge",
                )
            )
        except ValueError as error:
            raise OrchestratorServiceError(
                502,
                "invalid_dictionary_response",
                "Knowledge returned invalid dictionary data",
            ) from error

    @staticmethod
    def _payload(task: IngestionTask) -> IngestionTaskPayload:
        task_kind = TaskKind(
            getattr(task, "task_kind", None) or TaskKind.DOCUMENT_INGESTION.value
        )
        report = None
        if task.report:
            report = (
                DictionaryIngestionReport.model_validate(task.report)
                if task_kind == TaskKind.DICTIONARY_INGESTION
                else IngestionReport.model_validate(task.report)
            )
        return IngestionTaskPayload(
            id=task.id,
            status=IngestionTaskStatus(task.status),
            task_kind=task_kind,
            dictionary_version_id=getattr(task, "dictionary_version_id", None),
            report=report,
            error_message=task.error_message,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
