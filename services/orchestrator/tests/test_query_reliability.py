import asyncio
import json
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from app.core.config import settings
from app.service.base import OrchestratorServiceError
from app.service.query import QueryService

from infra.postgres.orchestrator_db import QueryRun
from shared.contracts import QueryRunStatus, UserRole
from shared.security import AuthenticatedPrincipal


class FakeQueryRepository:
    def __init__(self) -> None:
        self.run = None
        self.transitions: list[str] = []

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

    async def record_audit_event(self, *args, **kwargs):
        return None

    async def mark_processing(self, run):
        run.status = QueryRunStatus.PROCESSING.value
        self.transitions.append("processing")
        return run

    async def mark_completed(self, run, query_ir, evidence_bundle, answer, graph_subgraph, retrieval_trace, warnings, latency_ms):
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

    async def mark_failed(self, run, code, message, latency_ms):
        run.status = QueryRunStatus.FAILED.value
        run.error_code = code
        run.error_message = message
        run.latency_ms = latency_ms
        self.transitions.append("failed")
        return run


def _principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(user_id=uuid4(), role=UserRole.RESEARCHER, token_id=uuid4())


def _service(client: httpx.AsyncClient, repository: FakeQueryRepository) -> QueryService:
    return QueryService(client=client, query_repository=repository)


def _retrieval_payload(*, planner_profiles: list[dict] | None = None) -> dict:
    planner_trace = planner_profiles or [{"profile": "semantic", "selected": True}]
    return {
        "query_ir": {"raw_query": "никель", "entities": ["никель"], "filters": {}},
        "evidence_bundle": {
            "query_ir": {"raw_query": "никель", "entities": ["никель"], "filters": {}},
            "evidence_items": [
                {
                    "source_span": {
                        "id": "span-1",
                        "document_id": "doc-1",
                        "page": 1,
                        "start_offset": 0,
                        "end_offset": 10,
                        "text": "никель 12%",
                        "source_type": "text",
                    },
                    "relevance_score": 0.9,
                    "claim_ids": [],
                    "entity_ids": [],
                    "extraction_method": "semantic",
                }
            ],
            "total_found": 1,
        },
        "retrieval_trace": {
            "storage": "hybrid",
            "retrieved": 1,
            "accessible": 1,
            "planner": {"trace": planner_trace},
        },
        "warnings": [],
    }


def _downstream_ok_handler() -> httpx.MockTransport:
    payload = _retrieval_payload()

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/v1/query"):
            return httpx.Response(200, json=payload)
        if path.endswith("/v1/gaps/suggest"):
            return httpx.Response(200, json={"gaps": [], "warnings": []})
        if path.endswith("/v1/graph/subgraph"):
            return httpx.Response(200, json={"nodes": [], "links": []})
        if path.endswith("/v1/answers/synthesize"):
            return httpx.Response(
                200,
                json={
                    "answer": {
                        "query_ir": payload["query_ir"],
                        "evidence_bundle": payload["evidence_bundle"],
                        "answer_text": "Подтверждённый ответ.",
                        "confidence": 0.82,
                        "sources_count": 1,
                        "model_used": "stub",
                    },
                    "warnings": [],
                },
            )
        return httpx.Response(404, json={"code": "missing", "message": "not found", "request_id": "r"})

    return httpx.MockTransport(handler)


def test_default_flow_uses_legacy_pipeline_when_flag_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "top1_scientific_query_enabled", False)
    repository = FakeQueryRepository()

    async def execute():
        async with httpx.AsyncClient(transport=_downstream_ok_handler()) as client:
            return await _service(client, repository).run_query(
                _principal(), "никель", {}, "req-legacy", 20
            )

    result = asyncio.run(execute())
    assert result.status == QueryRunStatus.COMPLETED
    assert result.retrieval_trace["pipeline_mode"] == "legacy"
    assert repository.transitions == ["pending", "processing", "completed"]


def test_explicit_scientific_filter_false_keeps_legacy_when_settings_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "top1_scientific_query_enabled", True)
    repository = FakeQueryRepository()

    async def execute():
        async with httpx.AsyncClient(transport=_downstream_ok_handler()) as client:
            return await _service(client, repository).run_query(
                _principal(),
                "никель",
                {"top1_scientific_query": False},
                "req-override",
                20,
            )

    result = asyncio.run(execute())
    assert result.retrieval_trace["pipeline_mode"] == "legacy"


def test_scientific_pipeline_survives_graph_exact_timeout(monkeypatch) -> None:
    monkeypatch.setattr(settings, "top1_scientific_query_enabled", True)
    repository = FakeQueryRepository()
    payload = _retrieval_payload(
        planner_profiles=[
            {"profile": "semantic", "selected": True},
            {"profile": "graph", "selected": True},
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/v1/query"):
            return httpx.Response(200, json=payload)
        if path.endswith("/v1/graph/exact-search"):
            raise httpx.ReadTimeout("graph timeout")
        if path.endswith("/v1/gaps/suggest"):
            return httpx.Response(200, json={"gaps": [], "warnings": []})
        if path.endswith("/v1/graph/subgraph"):
            return httpx.Response(200, json={"nodes": [], "links": []})
        if path.endswith("/v1/conflicts/detect"):
            return httpx.Response(200, json={"conflicts": [], "warnings": []})
        if path.endswith("/v1/answers/synthesize"):
            return httpx.Response(
                200,
                json={
                    "answer": {
                        "query_ir": payload["query_ir"],
                        "evidence_bundle": payload["evidence_bundle"],
                        "answer_text": "Ответ после graph fallback.",
                        "confidence": 0.75,
                        "sources_count": 1,
                        "model_used": "stub",
                    },
                    "warnings": [],
                },
            )
        return httpx.Response(404, json={"code": "missing", "message": "not found", "request_id": "r"})

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await _service(client, repository).run_query(
                _principal(), "никель", {"top1_scientific_query": True}, "req-graph-fallback", 20
            )

    result = asyncio.run(execute())
    assert result.status == QueryRunStatus.COMPLETED
    assert result.retrieval_trace["pipeline_mode"] == "top1_scientific"
    assert result.retrieval_trace["graph_exact"]["fallback"] == "knowledge_timeout"
    assert any("graph_exact_fallback:knowledge_timeout" in warning for warning in result.warnings)


def test_scientific_pipeline_survives_verification_timeout(monkeypatch) -> None:
    monkeypatch.setattr(settings, "top1_scientific_query_enabled", True)
    repository = FakeQueryRepository()
    payload = _retrieval_payload()

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/v1/query"):
            return httpx.Response(200, json=payload)
        if path.endswith("/v1/gaps/suggest"):
            return httpx.Response(200, json={"gaps": [], "warnings": []})
        if path.endswith("/v1/graph/subgraph"):
            return httpx.Response(200, json={"nodes": [], "links": []})
        if path.endswith("/v1/conflicts/detect"):
            raise httpx.ReadTimeout("verification timeout")
        if path.endswith("/v1/answers/synthesize"):
            return httpx.Response(
                200,
                json={
                    "answer": {
                        "query_ir": payload["query_ir"],
                        "evidence_bundle": payload["evidence_bundle"],
                        "answer_text": "Ответ после verification fallback.",
                        "confidence": 0.7,
                        "sources_count": 1,
                        "model_used": "stub",
                    },
                    "warnings": [],
                },
            )
        return httpx.Response(404, json={"code": "missing", "message": "not found", "request_id": "r"})

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await _service(client, repository).run_query(
                _principal(), "никель", {"top1_scientific_query": True}, "req-verify-fallback", 20
            )

    result = asyncio.run(execute())
    assert result.status == QueryRunStatus.COMPLETED
    assert result.retrieval_trace["verification"]["fallback"] == "model_timeout"
    assert any("verification_fallback:model_timeout" in warning for warning in result.warnings)


def test_retrieval_timeout_fails_run_with_504() -> None:
    repository = FakeQueryRepository()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/v1/query"):
            raise httpx.ReadTimeout("retrieval timeout")
        return httpx.Response(503)

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(OrchestratorServiceError) as error:
                await _service(client, repository).run_query(
                    _principal(), "никель", {}, "req-timeout", 20
                )
            return error.value

    error = asyncio.run(execute())
    assert error.status_code == 504
    assert error.code == "retrieval_timeout"
    assert error.query_run_id == repository.run.id
    assert repository.transitions == ["pending", "processing", "failed"]
    assert repository.run.latency_ms is not None


def test_stream_emits_error_phase_on_retrieval_failure(monkeypatch) -> None:
    monkeypatch.setattr(settings, "top1_scientific_query_enabled", False)
    repository = FakeQueryRepository()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/v1/query"):
            return httpx.Response(
                503,
                json={"code": "retrieval_unavailable", "message": "down", "request_id": "r"},
            )
        return httpx.Response(404)

    async def run() -> list[dict]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            events = []
            async for chunk in _service(client, repository).stream_query(
                _principal(), "никель", {}, "req-stream-error", 20
            ):
                line = chunk.strip()
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))
            return events

    events = asyncio.run(run())
    error_event = next(event for event in events if event.get("phase") == "error")
    assert error_event["code"] == "retrieval_unavailable"
    assert repository.transitions == ["pending", "processing", "failed"]


def test_stream_marks_degraded_terminal_phase_without_evidence(monkeypatch) -> None:
    monkeypatch.setattr(settings, "top1_scientific_query_enabled", False)
    repository = FakeQueryRepository()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/v1/query"):
            return httpx.Response(
                200,
                json={
                    "query_ir": {"raw_query": "пусто", "filters": {}},
                    "evidence_bundle": {
                        "query_ir": {"raw_query": "пусто", "filters": {}},
                        "evidence_items": [],
                        "total_found": 0,
                    },
                    "retrieval_trace": {"accessible": 0},
                    "warnings": [],
                },
            )
        return httpx.Response(404)

    async def run() -> list[dict]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            events = []
            async for chunk in _service(client, repository).stream_query(
                _principal(), "пусто", {}, "req-stream-degraded", 20
            ):
                line = chunk.strip()
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))
            return events

    events = asyncio.run(run())
    phases = [event.get("phase") for event in events if event.get("type") == "phase"]
    assert "degraded" in phases
    done = next(event for event in events if event.get("type") == "done")
    assert "insufficient_accessible_evidence" in done["payload"]["warnings"]
