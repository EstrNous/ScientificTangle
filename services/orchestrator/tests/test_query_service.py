import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import httpx

from app.service.service import OrchestratorService, OrchestratorServiceError
from infra.postgres.orchestrator_db import QueryRun
from shared.contracts import QueryRunStatus, UserRole
from shared.security import AuthenticatedPrincipal


class FakeQueryRepository:
    def __init__(self) -> None:
        self.run = None
        self.transitions = []

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


def service(client, repository):
    return OrchestratorService(
        repository=None,
        client=client,
        ingestion_url="http://ingestion",
        knowledge_url="http://knowledge",
        retrieval_url="http://retrieval",
        model_url="http://model",
        query_repository=repository,
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
            return await service(client, repository).run_query(
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
                await service(client, repository).run_query(
                    principal(), "никель", {}, "request-1", 20
                )
            except OrchestratorServiceError as error:
                return error
        raise AssertionError

    error = asyncio.run(execute())

    assert error.query_run_id == repository.run.id
    assert repository.transitions == ["pending", "processing", "failed"]


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
            return await service(client, repository).run_query(
                principal(), "закрытый вопрос", {}, "request-1", 20
            )

    result = asyncio.run(execute())

    assert result.answer.sources_count == 0
    assert result.graph_subgraph.nodes == []
    assert "insufficient_accessible_evidence" in result.warnings
