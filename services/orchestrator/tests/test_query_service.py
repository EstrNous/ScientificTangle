import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
import pytest
from app.service.query import QueryService
from app.service.audit import AuditService
from app.service.export import ExportService
from app.service.base import OrchestratorServiceError

from infra.postgres.orchestrator_db import ExportJob, QueryRun
from shared.contracts import QueryRunStatus, UserRole
from shared.security import AuthenticatedPrincipal


class FakeQueryRepository:
    def __init__(self) -> None:
        self.run = None
        self.transitions = []
        self.audit_rows: list[dict[str, object]] = []
        self.audit_events: list[dict[str, object]] = []
        self.export_job = None
        self.export_transitions: list[str] = []
        self.last_audit_filters: dict[str, object] | None = None

    async def create(self, user_id, question, request_id, dictionary_version_id=None):
        now = datetime.now(UTC)
        self.run = QueryRun(
            id=uuid4(),
            user_id=user_id,
            status=QueryRunStatus.PENDING.value,
            raw_question=question,
            request_id=request_id,
            warnings=[],
            graph_subgraph={},
            created_at=now,
            updated_at=now,
            dictionary_version_id=dictionary_version_id,
        )
        self.transitions.append("pending")
        return self.run

    async def get(self, run_id):
        return self.run if self.run and self.run.id == run_id else None

    async def set_report(self, task, report):
        return task

    async def mark_processing(self, run):
        run.status = QueryRunStatus.PROCESSING.value
        self.transitions.append("processing")
        return run

    async def mark_completed(
        self,
        run,
        query_ir,
        evidence_bundle,
        answer,
        graph_subgraph,
        retrieval_trace,
        warnings,
        latency_ms,
    ):
        run.status = QueryRunStatus.COMPLETED.value
        run.query_ir = query_ir.model_dump(mode="json")
        run.evidence_bundle = evidence_bundle.model_dump(mode="json")
        run.answer = answer.model_dump(mode="json")
        run.graph_subgraph = graph_subgraph.model_dump(mode="json")
        run.retrieval_trace = retrieval_trace
        run.warnings = warnings
        run.latency_ms = latency_ms
        self.transitions.append("completed")
        return run

    async def create_query_run(self, user_id, raw_query: str) -> QueryRun:
        now = datetime.now(UTC)
        return QueryRun(
            id=uuid4(),
            user_id=user_id,
            status="processing",
            raw_query=raw_query,
            created_at=now,
            updated_at=now,
        )

    async def complete_query_run(self, run, query_ir, retrieval_trace, answer_payload, latency_ms):
        run.status = "completed"
        run.query_ir = query_ir
        run.retrieval_trace = retrieval_trace
        run.answer_payload = answer_payload
        run.latency_ms = latency_ms
        return run

    async def fail_query_run(self, run, message, latency_ms):
        run.status = "failed"
        run.error_message = message
        run.latency_ms = latency_ms
        return run

    async def record_audit_event(self, user_id, action, resource_type, resource_id, details, request_id):
        self.audit_events.append(
            {
                "user_id": user_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": details,
                "request_id": request_id,
            }
        )

    async def create_export_job(self, user_id, query_run_id, export_format):
        now = datetime.now(UTC)
        self.export_job = ExportJob(
            id=uuid4(),
            user_id=user_id,
            query_run_id=query_run_id,
            status="pending",
            format=export_format,
            created_at=now,
            updated_at=now,
        )
        self.export_transitions.append("pending")
        return self.export_job

    async def mark_export_processing(self, job):
        job.status = "processing"
        self.export_transitions.append("processing")
        return job

    async def mark_export_completed(self, job, payload, file_url):
        job.status = "completed"
        job.payload = payload.model_dump(mode="json")
        job.file_url = file_url
        self.export_transitions.append("completed")
        return job

    async def mark_export_failed(self, job, message):
        job.status = "failed"
        job.error_message = message
        self.export_transitions.append("failed")
        return job

    async def list_audit_events(
        self,
        limit: int = 200,
        offset: int = 0,
        action: str | None = None,
        user_id: UUID | None = None,
    ):
        self.last_audit_filters = {
            "limit": limit,
            "offset": offset,
            "action": action,
            "user_id": user_id,
        }
        return self.audit_rows

    async def mark_failed(self, run, code, message, latency_ms):
        run.status = QueryRunStatus.FAILED.value
        run.error_code = code
        run.error_message = message
        run.latency_ms = latency_ms
        self.transitions.append("failed")
        return run


def principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        user_id=uuid4(),
        role=UserRole.RESEARCHER,
        token_id=uuid4(),
    )


def test_query_run_is_persisted_with_evidence_graph_and_answer() -> None:
    span = {
        "document_id": "doc-1",
        "page": 1,
        "start_offset": 0,
        "end_offset": 11,
        "text": "Никель 82 %",
        "source_type": "text",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "retrieval":
            return httpx.Response(
                200,
                json={
                    "query_ir": {"raw_query": "никель", "filters": {}},
                    "evidence_bundle": {
                        "query_ir": {"raw_query": "никель", "filters": {}},
                        "evidence_items": [
                            {
                                "source_span": span,
                                "claim_ids": ["claim-1"],
                                "entity_ids": ["entity-1"],
                            }
                        ],
                        "total_found": 1,
                    },
                    "retrieval_trace": {"storage": "qdrant"},
                    "warnings": [],
                },
            )
        if request.url.host == "knowledge":
            return httpx.Response(
                200,
                json={
                    "nodes": [{"id": "entity-1", "label": "Никель", "type": "Material"}],
                    "links": [],
                },
            )
        if request.url.path.endswith("/gaps/suggest"):
            return httpx.Response(200, json={"gaps": [], "warnings": []})
        return httpx.Response(
            200,
            json={
                "answer": {
                    "query_ir": {"raw_query": "никель", "filters": {}},
                    "evidence_bundle": {
                        "query_ir": {"raw_query": "никель", "filters": {}},
                        "evidence_items": [{"source_span": span}],
                        "total_found": 1,
                    },
                    "answer_text": "Подтверждённый ответ",
                    "sources_count": 1,
                },
                "warnings": [],
            },
        )

    repository = FakeQueryRepository()

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = QueryService(client=client, query_repository=repository)
            return await service.run_query(
                principal(), "никель", {}, "request-1", 20
            )

    result = asyncio.run(execute())

    assert result.status == QueryRunStatus.COMPLETED
    assert result.graph_subgraph.nodes[0].id == "entity-1"
    assert repository.transitions == ["pending", "processing", "completed"]


def test_query_failure_is_persisted_and_exposes_run_id() -> None:
    repository = FakeQueryRepository()

    async def execute():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(503))
        ) as client:
            try:
                service = QueryService(client=client, query_repository=repository)
                await service.run_query(
                    principal(), "никель", {}, "request-1", 20
                )
            except OrchestratorServiceError as error:
                return error
        raise AssertionError

    error = asyncio.run(execute())

    assert error.query_run_id == repository.run.id
    assert repository.transitions == ["pending", "processing", "failed"]


def test_query_requires_active_dictionary_before_creating_run() -> None:
    repository = FakeQueryRepository()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/dictionaries/active"
        return httpx.Response(
            404,
            json={
                "code": "active_dictionary_not_found",
                "message": "Active dictionary was not found",
                "request_id": "request-1",
            },
        )

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = QueryService(client=client, query_repository=repository)
            with pytest.raises(OrchestratorServiceError) as error:
                await service.run_query(principal(), "никель", {}, "request-1", 20)
            assert error.value.code == "active_dictionary_required"

    asyncio.run(execute())
    assert repository.run is None


def test_empty_evidence_skips_synthesis_and_completes_with_warning() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "retrieval"
        return httpx.Response(
            200,
            json={
                "query_ir": {"raw_query": "закрытый вопрос", "filters": {}},
                "evidence_bundle": {
                    "query_ir": {"raw_query": "закрытый вопрос", "filters": {}},
                    "evidence_items": [],
                    "total_found": 0,
                },
                "retrieval_trace": {"accessible": 0},
                "warnings": [],
            },
        )

    repository = FakeQueryRepository()

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = QueryService(client=client, query_repository=repository)
            return await service.run_query(
                principal(), "закрытый вопрос", {}, "request-1", 20
            )

    result = asyncio.run(execute())

    assert result.answer.sources_count == 0
    assert result.graph_subgraph.nodes == []
    assert "insufficient_accessible_evidence" in result.warnings


def test_list_audit_events_maps_extended_fields_and_filters() -> None:
    repository = FakeQueryRepository()
    user_id = uuid4()
    repository.audit_rows = [
        {
            "id": uuid4(),
            "user_id": user_id,
            "action": "source_viewed",
            "resource_type": "source_span",
            "resource_id": "span-1",
            "details": {
                "source_span_id": "span-1",
                "role": "researcher",
                "status": "success",
            },
            "request_id": "req-1",
            "created_at": datetime(2026, 7, 4, tzinfo=UTC),
        }
    ]

    async def execute():
        service = AuditService(query_repository=repository)
        return await service.list_audit_events(
            limit=25,
            offset=10,
            action="source_viewed",
            user_id=user_id,
        )

    events = asyncio.run(execute())

    assert repository.last_audit_filters == {
        "limit": 25,
        "offset": 10,
        "action": "source_viewed",
        "user_id": user_id,
    }
    assert events[0].user == str(user_id)
    assert events[0].user_id == str(user_id)
    assert events[0].role == "researcher"
    assert events[0].status == "success"
    assert events[0].resource_type == "source_span"
    assert events[0].resource_id == "span-1"
    assert events[0].request_id == "req-1"


def test_export_query_run_returns_markdown_for_completed_run() -> None:
    repository = FakeQueryRepository()
    owner = principal()
    now = datetime.now(UTC)
    repository.run = QueryRun(
        id=uuid4(),
        user_id=owner.user_id,
        status=QueryRunStatus.COMPLETED.value,
        raw_question="Никель 82 %",
        query_ir={"raw_query": "Никель 82 %", "filters": {}},
        evidence_bundle={
            "query_ir": {"raw_query": "Никель 82 %", "filters": {}},
            "evidence_items": [
                {
                    "source_span": {
                        "id": "span-1",
                        "document_id": "doc-1",
                        "page": 1,
                        "start_offset": 0,
                        "end_offset": 11,
                        "text": "Никель 82 %",
                        "source_type": "text",
                    },
                    "relevance_score": 0.9,
                    "claim_ids": ["claim-1"],
                    "entity_ids": ["entity-1"],
                }
            ],
            "total_found": 1,
            "gaps": [],
            "conflicts": [],
        },
        answer={
            "query_ir": {"raw_query": "Никель 82 %", "filters": {}},
            "evidence_bundle": {
                "query_ir": {"raw_query": "Никель 82 %", "filters": {}},
                "evidence_items": [],
                "total_found": 0,
            },
            "answer_text": "Подтверждённый ответ",
            "confidence": 0.8,
            "sources_count": 1,
        },
        graph_subgraph={"nodes": [{"id": "entity-1", "label": "Никель", "type": "Material"}], "links": []},
        retrieval_trace={"storage": "qdrant"},
        warnings=["gap_checked"],
        request_id="req-1",
        latency_ms=321,
        created_at=now,
        updated_at=now,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/resolve")
        return httpx.Response(
            200,
            json={
                "source_span": {
                    "id": "span-1",
                    "document_id": "doc-1",
                    "page": 1,
                    "start_offset": 0,
                    "end_offset": 11,
                    "text": "Никель 82 %",
                    "source_type": "text",
                },
                "document_title": "doc-1.pdf",
                "source_type": "pdf",
                "metadata": {"year": 2024},
                "access_policy": {"level": "internal", "allowed_roles": ["researcher"]},
            },
        )

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = ExportService(client=client, query_repository=repository)
            return await service.export_query_run(
                owner,
                repository.run.id,
                "markdown",
                "request-2",
            )

    result = asyncio.run(execute())

    assert result.format == "markdown"
    assert result.content_type == "text/markdown"
    assert "Подтверждённый ответ" in result.content
    assert repository.export_transitions == ["pending", "processing", "completed"]
    assert repository.audit_events[-1]["action"] == "document_exported"


def test_export_query_run_fails_when_source_access_changed() -> None:
    repository = FakeQueryRepository()
    owner = principal()
    now = datetime.now(UTC)
    repository.run = QueryRun(
        id=uuid4(),
        user_id=owner.user_id,
        status=QueryRunStatus.COMPLETED.value,
        raw_question="Закрытый источник",
        query_ir={"raw_query": "Закрытый источник", "filters": {}},
        evidence_bundle={
            "query_ir": {"raw_query": "Закрытый источник", "filters": {}},
            "evidence_items": [
                {
                    "source_span": {
                        "id": "span-denied",
                        "document_id": "doc-denied",
                        "page": 1,
                        "start_offset": 0,
                        "end_offset": 16,
                        "text": "Закрытый текст",
                        "source_type": "text",
                    }
                }
            ],
            "total_found": 1,
        },
        answer={
            "query_ir": {"raw_query": "Закрытый источник", "filters": {}},
            "evidence_bundle": {
                "query_ir": {"raw_query": "Закрытый источник", "filters": {}},
                "evidence_items": [],
                "total_found": 0,
            },
            "answer_text": "Ответ",
        },
        graph_subgraph={"nodes": [], "links": []},
        retrieval_trace={"storage": "qdrant"},
        warnings=[],
        request_id="req-3",
        latency_ms=100,
        created_at=now,
        updated_at=now,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "source_not_found"})

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            try:
                service = ExportService(client=client, query_repository=repository)
                await service.export_query_run(
                    owner,
                    repository.run.id,
                    "json",
                    "request-3",
                )
            except OrchestratorServiceError as error:
                return error
        raise AssertionError

    error = asyncio.run(execute())

    assert error.code == "export_access_changed"
    assert repository.export_transitions == ["pending", "processing", "failed"]
    assert repository.audit_events[-1]["action"] == "access_denied"