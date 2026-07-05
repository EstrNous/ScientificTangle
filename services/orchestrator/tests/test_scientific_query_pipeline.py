import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import httpx
from app.core.config import settings
from app.service.query import QueryService

from infra.postgres.orchestrator_db import QueryRun
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

    async def create(self, user_id, question, request_id):
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
        )
        self.transitions.append("pending")
        return self.run

    async def get(self, run_id):
        return self.run if self.run and self.run.id == run_id else None

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


def orchestrator_service(client, repository):
    return QueryService(client=client, query_repository=repository)


def test_legacy_query_keeps_pipeline_mode_when_flag_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "top1_scientific_query_enabled", False)
    span = {
        "id": "span-1",
        "document_id": "doc-1",
        "page": 1,
        "start_offset": 0,
        "end_offset": 11,
        "text": "Никель 82 %",
        "source_type": "text",
    }
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.host == "retrieval":
            return httpx.Response(
                200,
                json={
                    "query_ir": {"raw_query": "никель", "filters": {}},
                    "evidence_bundle": {
                        "query_ir": {"raw_query": "никель", "filters": {}},
                        "evidence_items": [{"source_span": span, "claim_ids": ["claim-1"]}],
                        "total_found": 1,
                    },
                    "retrieval_trace": {"storage": "qdrant", "planner": {"trace": []}},
                    "warnings": [],
                },
            )
        if request.url.path.endswith("/exact-search"):
            raise AssertionError("graph exact must not run in legacy mode")
        if request.url.host == "knowledge":
            return httpx.Response(200, json={"nodes": [], "links": []})
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
                "unsupported_warnings": [],
            },
        )

    repository = FakeQueryRepository()

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await orchestrator_service(client, repository).run_query(
                principal(), "никель", {}, "request-legacy", 20
            )

    result = asyncio.run(execute())

    assert result.status == QueryRunStatus.COMPLETED
    assert repository.run.retrieval_trace["pipeline_mode"] == "legacy"
    assert "/v1/graph/exact-search" not in calls


def test_scientific_query_runs_graph_verification_and_synthesis(monkeypatch) -> None:
    monkeypatch.setattr(settings, "top1_scientific_query_enabled", True)
    span = {
        "id": "span-1",
        "document_id": "doc-1",
        "page": 1,
        "start_offset": 0,
        "end_offset": 11,
        "text": "Никель 82 %",
        "source_type": "text",
    }
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.host == "retrieval":
            return httpx.Response(
                200,
                json={
                    "query_ir": {"raw_query": "никель", "filters": {}},
                    "evidence_bundle": {
                        "query_ir": {"raw_query": "никель", "filters": {}},
                        "evidence_items": [{"source_span": span, "claim_ids": ["claim-1"]}],
                        "total_found": 1,
                    },
                    "retrieval_trace": {
                        "storage": "qdrant",
                        "planner": {
                            "trace": [{"profile": "graph", "selected": True, "reason": "graph_candidate_channel"}]
                        },
                    },
                    "warnings": [],
                },
            )
        if request.url.path.endswith("/exact-search"):
            return httpx.Response(
                200,
                json={
                    "fallback_state": "none",
                    "conflicts": [],
                    "gaps": [],
                    "evidence": [],
                    "claim_ids": ["claim-graph-1"],
                    "source_span_ids": [],
                },
            )
        if request.url.path.endswith("/conflicts/detect"):
            return httpx.Response(200, json={"conflicts": [], "warnings": []})
        if request.url.host == "knowledge" and request.url.path.endswith("/subgraph"):
            return httpx.Response(200, json={"nodes": [{"id": "entity-1", "label": "Ni", "type": "Material"}], "links": []})
        if request.url.path.endswith("/gaps/suggest"):
            body = request.read().decode()
            assert '"candidates"' in body
            return httpx.Response(200, json={"gaps": [], "warnings": []})
        if request.url.path.endswith("/answers/synthesize"):
            body = request.read().decode()
            assert '"candidate_items"' in body
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
                        "answer_text": "Научный ответ",
                        "sources_count": 1,
                    },
                    "warnings": [],
                    "unsupported_warnings": [],
                    "candidate_count": 0,
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    repository = FakeQueryRepository()

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await orchestrator_service(client, repository).run_query(
                principal(), "никель", {}, "request-scientific", 20
            )

    result = asyncio.run(execute())

    assert result.status == QueryRunStatus.COMPLETED
    assert repository.run.retrieval_trace["pipeline_mode"] == "top1_scientific"
    assert repository.run.retrieval_trace["planner_selected_graph"] is True
    assert "/v1/graph/exact-search" in calls
    assert "/v1/conflicts/detect" in calls
    assert result.answer.answer_text == "Научный ответ"


def test_scientific_query_graph_exact_fallback_keeps_legacy_completion(monkeypatch) -> None:
    monkeypatch.setattr(settings, "top1_scientific_query_enabled", True)
    span = {
        "id": "span-1",
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
                        "evidence_items": [{"source_span": span}],
                        "total_found": 1,
                    },
                    "retrieval_trace": {
                        "planner": {
                            "trace": [{"profile": "graph", "selected": True}]
                        }
                    },
                    "warnings": [],
                },
            )
        if request.url.path.endswith("/exact-search"):
            return httpx.Response(503, json={"detail": "neo4j unavailable"})
        if request.url.path.endswith("/conflicts/detect"):
            return httpx.Response(200, json={"conflicts": [], "warnings": []})
        if request.url.host == "knowledge":
            return httpx.Response(200, json={"nodes": [], "links": []})
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
                    "answer_text": "Fallback ответ",
                    "sources_count": 1,
                },
                "warnings": [],
                "unsupported_warnings": [],
            },
        )

    repository = FakeQueryRepository()

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await orchestrator_service(client, repository).run_query(
                principal(), "никель", {}, "request-fallback", 20
            )

    result = asyncio.run(execute())

    assert result.status == QueryRunStatus.COMPLETED
    assert "graph_exact_fallback:knowledge_error" in result.warnings