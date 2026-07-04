import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
import pytest

from app.schemas import ExportJobCreateRequest
from app.service.job_store import JobStore
from app.service.service import ExportService
from shared.contracts import AnswerPayload, EvidenceBundle, QueryIR, UserRole
from shared.security import AuthenticatedPrincipal


class FakeArtifactStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def ensure_bucket(self) -> None:
        return None

    async def store(
        self,
        user_id: UUID,
        query_run_id: UUID,
        job_id: UUID,
        artifact_kind: str,
        content: bytes,
        content_type: str,
    ) -> tuple[str, int, str]:
        storage_key = f"exports/{user_id}/{query_run_id}/{job_id}/report.bin"
        self.objects[storage_key] = content
        return storage_key, len(content), "sha256:demo"

    async def read(self, storage_key: str) -> tuple[bytes, str | None]:
        return self.objects[storage_key], "text/markdown"

    def artifact_url(self, job_id: UUID) -> str:
        return f"/v1/jobs/{job_id}/artifact"


def sample_document() -> dict:
    return {
        "query_run_id": str(uuid4()),
        "question": "Никель 82 %",
        "role": "researcher",
        "access_scope": ["internal"],
        "dictionary_version_id": None,
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "completed",
        "latency_ms": 100,
        "answer": "Подтверждённый ответ",
        "confidence": 0.8,
        "sources_count": 1,
        "query_ir": {"raw_query": "Никель 82 %", "filters": {}},
        "evidence": [
            {
                "source_span_id": "span-1",
                "text": "Никель 82 %",
                "relevance_score": 0.9,
                "claim_ids": [],
                "entity_ids": [],
                "page": 1,
            }
        ],
        "sources": [
            {
                "source_span_id": "span-1",
                "document_id": "doc-1",
                "document_title": "doc-1.pdf",
                "page": 1,
                "source_type": "pdf",
                "text": "Никель 82 %",
                "link": "/api/source/span-1",
                "metadata": {},
            }
        ],
        "graph": {"nodes": [], "links": []},
        "gaps": [],
        "conflicts": [],
        "warnings": [],
        "retrieval_trace": {"storage": "qdrant"},
    }


def sample_answer() -> AnswerPayload:
    query_ir = QueryIR(raw_query="Никель 82 %", filters={})
    evidence_bundle = EvidenceBundle(query_ir=query_ir, evidence_items=[], total_found=0)
    return AnswerPayload(
        query_ir=query_ir,
        evidence_bundle=evidence_bundle,
        answer_text="Подтверждённый ответ",
        confidence=0.8,
        sources_count=1,
    )


def principal(user_id: UUID | None = None) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        user_id=user_id or uuid4(),
        role=UserRole.RESEARCHER,
        token_id=uuid4(),
    )


def test_create_markdown_job_stores_artifact_and_status() -> None:
    storage = FakeArtifactStorage()
    job_store = JobStore("redis://invalid:6379/0")
    job_id = uuid4()
    user_id = uuid4()
    query_run_id = uuid4()

    async def execute():
        async with httpx.AsyncClient() as client:
            service = ExportService(storage, job_store, client, "http://model", "exports")
            return await service.create_job(
                ExportJobCreateRequest(
                    job_id=job_id,
                    user_id=user_id,
                    query_run_id=query_run_id,
                    format="markdown",
                    document=sample_document(),
                ),
                "req-1",
            )

    result = asyncio.run(execute())

    assert result.status == "completed"
    assert result.content_type == "text/markdown"
    assert "Подтверждённый ответ" in str(result.content)
    assert result.artifacts[0].storage_key in storage.objects

    status = asyncio.run(job_store.get(job_id))
    assert status is not None
    assert status.status == "completed"


def test_create_jsonld_job_calls_model_endpoint() -> None:
    storage = FakeArtifactStorage()
    job_store = JobStore("redis://invalid:6379/0")
    job_id = uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/v1/jsonld/enrich")
        return httpx.Response(
            200,
            json={
                "jsonld": {"@type": "st:Answer", "st:answerText": "Подтверждённый ответ"},
                "warnings": [],
            },
        )

    async def execute():
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            service = ExportService(storage, job_store, client, "http://model", "exports")
            return await service.create_job(
                ExportJobCreateRequest(
                    job_id=job_id,
                    user_id=uuid4(),
                    query_run_id=uuid4(),
                    format="jsonld",
                    document=sample_document(),
                    answer=sample_answer(),
                ),
                "req-2",
            )

    result = asyncio.run(execute())

    assert result.status == "completed"
    assert result.content_type == "application/ld+json"
    assert result.content["@type"] == "st:Answer"


def test_download_artifact_requires_owner() -> None:
    storage = FakeArtifactStorage()
    job_store = JobStore("redis://invalid:6379/0")
    job_id = uuid4()
    owner_id = uuid4()

    async def setup():
        async with httpx.AsyncClient() as client:
            service = ExportService(storage, job_store, client, "http://model", "exports")
            await service.create_job(
                ExportJobCreateRequest(
                    job_id=job_id,
                    user_id=owner_id,
                    query_run_id=uuid4(),
                    format="json",
                    document=sample_document(),
                ),
                "req-3",
            )

    asyncio.run(setup())

    async def download():
        async with httpx.AsyncClient() as client:
            service = ExportService(storage, job_store, client, "http://model", "exports")
            return await service.download_artifact(job_id, principal(owner_id))

    content, content_type, filename = asyncio.run(download())
    assert content
    assert content_type == "text/markdown"
    assert filename.endswith(".bin")
