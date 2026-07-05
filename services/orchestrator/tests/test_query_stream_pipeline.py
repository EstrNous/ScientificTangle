import asyncio
import json
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
        return self.run

    async def record_audit_event(self, *args, **kwargs):
        return None

    async def mark_processing(self, run):
        run.status = QueryRunStatus.PROCESSING.value
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
        return run

    async def mark_failed(self, run, code, message, latency_ms):
        run.status = QueryRunStatus.FAILED.value
        run.error_code = code
        run.error_message = message
        run.latency_ms = latency_ms
        return run


def _retrieval_payload():
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
            "planner": {"trace": [{"profile": "semantic", "selected": True}]},
        },
        "warnings": [],
    }


def test_stream_query_emits_phase_and_done_events(monkeypatch) -> None:
    monkeypatch.setattr(settings, "top1_scientific_query_enabled", False)

    repository = FakeQueryRepository()
    principal = AuthenticatedPrincipal(user_id=uuid4(), role=UserRole.RESEARCHER, token_id=uuid4())

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/v1/query"):
            return httpx.Response(200, json=_retrieval_payload())
        if path.endswith("/v1/gaps/suggest"):
            return httpx.Response(200, json={"gaps": [], "warnings": []})
        if path.endswith("/v1/graph/subgraph"):
            return httpx.Response(200, json={"nodes": [], "links": []})
        if path.endswith("/v1/answers/synthesize"):
            return httpx.Response(
                200,
                json={
                    "answer": {
                        "query_ir": _retrieval_payload()["query_ir"],
                        "evidence_bundle": _retrieval_payload()["evidence_bundle"],
                        "answer_text": "Подтверждённый ответ по никелю.",
                        "confidence": 0.82,
                        "sources_count": 1,
                        "model_used": "stub",
                    },
                    "warnings": [],
                },
            )
        return httpx.Response(404, json={"code": "missing", "message": "not found", "request_id": "r"})

    async def run() -> list[dict]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = QueryService(
                client=client,
                query_repository=repository,
            )
            events = []
            async for chunk in service.stream_query(
                principal=principal,
                question="никель",
                filters={},
                request_id="req-stream",
                limit=20,
            ):
                line = chunk.strip()
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))
            return events

    events = asyncio.run(run())
    types = [event.get("type") for event in events]
    phases = [event.get("phase") for event in events if event.get("type") == "phase"]
    assert "phase" in types
    assert "retrieval" in phases
    assert "done" in types
    done = next(event for event in events if event.get("type") == "done")
    assert done["payload"]["auth_context"]["role"] == "researcher"
    assert any(event.get("type") == "answer_chunk" for event in events)