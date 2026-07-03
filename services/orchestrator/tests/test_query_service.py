import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest

from app.service.service import OrchestratorService
from infra.postgres.orchestrator_db import QueryRun
from shared.contracts import NormalizedDocument, SourceSpan, UserRole
from shared.security import AuthenticatedPrincipal


class FakeRepository:
    async def create(self, user_id):
        raise NotImplementedError

    async def get(self, task_id):
        return None

    async def set_report(self, task, report):
        return task

    async def mark_failed(self, task, message):
        return task

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
        return None


def principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(user_id=uuid4(), role=UserRole.RESEARCHER, token_id=uuid4())


def test_run_query_pipeline_calls_downstream_services() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path.endswith("/v1/query"):
            query_ir = {
                "raw_query": "никель",
                "filters": {},
                "entities": [],
                "intent": "fact_lookup",
            }
            return httpx.Response(
                200,
                json={
                    "query_ir": query_ir,
                    "evidence_bundle": {
                        "query_ir": query_ir,
                        "evidence_items": [],
                        "total_found": 0,
                        "has_gaps": True,
                        "has_conflicts": False,
                        "gaps": [],
                        "conflicts": [],
                    },
                    "warnings": [],
                },
            )
        if request.url.path.endswith("/v1/gaps/suggest"):
            return httpx.Response(200, json={"gaps": [{"description": "need more data"}]})
        if request.url.path.endswith("/v1/answers/synthesize"):
            query_ir = {
                "raw_query": "никель",
                "filters": {},
                "entities": [],
                "intent": "fact_lookup",
            }
            evidence_bundle = {
                "query_ir": query_ir,
                "evidence_items": [],
                "total_found": 0,
                "has_gaps": True,
                "has_conflicts": False,
                "gaps": ["need more data"],
                "conflicts": [],
            }
            return httpx.Response(
                200,
                json={
                    "answer": {
                        "query_ir": query_ir,
                        "evidence_bundle": evidence_bundle,
                        "answer_text": "ответ",
                        "confidence": 0.5,
                    }
                },
            )
        return httpx.Response(404)

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = OrchestratorService(
                repository=FakeRepository(),
                client=client,
                ingestion_url="http://ingestion",
                knowledge_url="http://knowledge",
                retrieval_url="http://retrieval",
                model_url="http://model",
            )
            document = NormalizedDocument(
                id="doc-1",
                source_type="article",
                title="T",
                content="никель 82 %",
                source_spans=[
                    SourceSpan(
                        document_id="doc-1",
                        page=1,
                        start_offset=0,
                        end_offset=10,
                        text="никель 82 %",
                        source_type="text",
                    )
                ],
            )
            result = await service.run_query(
                principal=principal(),
                query="никель",
                documents=[document],
                request_id="req-1",
                limit=5,
            )
            assert result["answer"]["answer_text"] == "ответ"
            assert result["evidence_bundle"]["gaps"] == ["need more data"]

    asyncio.run(run())
    assert any("/v1/query" in path for path in calls)
    assert any("/v1/gaps/suggest" in path for path in calls)
    assert any("/v1/answers/synthesize" in path for path in calls)
