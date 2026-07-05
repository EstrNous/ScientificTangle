import asyncio
from types import SimpleNamespace

import httpx
from app.api.health import ready
from app.api.query import EMBEDDING_BATCH_SIZE, build_embeddings, build_index_links_by_span, collect_index_links
from app.storage import PendingRetrievalStorageAdapter
from fastapi import Response

from shared.contracts import (
    KnowledgeIngestionResponse,
    NormalizedDocument,
    RetrievalIndexRequest,
    SourceSpan,
    StorageWriteResult,
)


def test_readiness_is_closed_for_pending_adapter() -> None:
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(storage_adapter=PendingRetrievalStorageAdapter())
        )
    )
    response = Response()

    result = asyncio.run(ready(request, response))

    assert response.status_code == 503
    assert result["ready"] is False


def test_collect_index_links_from_knowledge_results() -> None:
    document = NormalizedDocument(
        id="document-1",
        source_type="docx",
        title="report.docx",
        content="Nickel recovery 82 %",
        source_spans=[
            SourceSpan(
                document_id="document-1",
                page=1,
                start_offset=0,
                end_offset=20,
                text="Nickel recovery 82 %",
                source_type="text",
            )
        ],
    )
    request = RetrievalIndexRequest(
        documents=[document],
        knowledge_results=[
            KnowledgeIngestionResponse(
                document_id=document.id,
                graph_write=StorageWriteResult(
                    backend="neo4j",
                    mode="live",
                    document_ids=[document.id],
                    claim_ids=["claim-1", "claim-2"],
                    graph_entity_ids=["entity-1"],
                ),
            )
        ],
    )
    claim_ids, entity_ids = collect_index_links(request)
    assert claim_ids == ["claim-1", "claim-2"]
    assert entity_ids == ["entity-1"]


def test_build_index_links_by_span_maps_graph_write_to_document_spans() -> None:
    document = NormalizedDocument(
        id="document-1",
        source_type="docx",
        title="report.docx",
        content="Nickel recovery 82 %",
        source_spans=[
            SourceSpan(
                document_id="document-1",
                page=1,
                start_offset=0,
                end_offset=20,
                text="Nickel recovery 82 %",
                source_type="text",
            )
        ],
    )
    request = RetrievalIndexRequest(
        documents=[document],
        knowledge_results=[
            KnowledgeIngestionResponse(
                document_id=document.id,
                graph_write=StorageWriteResult(
                    backend="neo4j",
                    mode="live",
                    document_ids=[document.id],
                    claim_ids=["claim-1"],
                    graph_entity_ids=["entity-1"],
                ),
            )
        ],
    )

    claim_ids_by_span, entity_ids_by_span = build_index_links_by_span(request)

    span_id = document.source_spans[0].id
    assert claim_ids_by_span[span_id] == ["claim-1"]
    assert entity_ids_by_span[span_id] == ["entity-1"]


def test_qdrant_adapter_index_writes_documents() -> None:
    document = NormalizedDocument(
        id="document-1",
        source_type="docx",
        title="report.docx",
        content="Nickel recovery 82 %",
        source_spans=[
            SourceSpan(
                document_id="document-1",
                page=1,
                start_offset=0,
                end_offset=20,
                text="Nickel recovery 82 %",
                source_type="text",
            )
        ],
    )
    request = RetrievalIndexRequest(documents=[document], knowledge_results=[])

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/collections/st_evidence_v1"):
            return httpx.Response(200, json={"result": {"status": "green"}})
        if req.url.path.endswith("/index"):
            return httpx.Response(200, json={"result": {"status": "ok"}})
        if req.url.path.endswith("/v1/embeddings"):
            return httpx.Response(
                200,
                json={"embeddings": [{"vector": [0.1, 0.2, 0.3]}]},
            )
        if req.url.path.endswith("/points") and req.method == "PUT":
            return httpx.Response(200, json={"result": {"status": "ok"}})
        return httpx.Response(404)

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            from app.qdrant_adapter import QdrantRetrievalStorageAdapter

            adapter = QdrantRetrievalStorageAdapter(client)
            return await adapter.index(request)

    result = asyncio.run(execute())
    assert result.records_count == 1
    assert result.document_ids == ["document-1"]


def test_build_embeddings_chunks_requests_above_model_limit() -> None:
    import json

    calls: list[int] = []

    def handler(req: httpx.Request) -> httpx.Response:
        texts = json.loads(req.content.decode("utf-8")).get("texts", [])
        calls.append(len(texts))
        return httpx.Response(
            200,
            json={"embeddings": [{"vector": [0.1, 0.2]} for _ in texts]},
        )

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            texts = [f"chunk-{index}" for index in range(EMBEDDING_BATCH_SIZE + 3)]
            return await build_embeddings(client, texts, "document")

    result = asyncio.run(execute())
    assert len(result["vectors"]) == EMBEDDING_BATCH_SIZE + 3
    assert calls == [EMBEDDING_BATCH_SIZE, 3]
