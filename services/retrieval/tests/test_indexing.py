import asyncio
from types import SimpleNamespace

from app.api.health import ready
from app.api.indexing import index_documents
from app.api.query import collect_index_links
from app.storage import PendingRetrievalStorageAdapter
from fastapi import Response

from shared.contracts import (
    KnowledgeIngestionResponse,
    NormalizedDocument,
    RetrievalIndexRequest,
    SourceSpan,
    StorageWriteResult,
    TableBlock,
)

COLLECTION_NAME = "st_evidence_v1"


class FakeStorageAdapter:
    is_ready = True

    async def index(self, request: RetrievalIndexRequest) -> StorageWriteResult:
        return StorageWriteResult(
            backend="qdrant",
            mode="live",
            document_ids=[document.id for document in request.documents],
            records_count=sum(len(document.source_spans) for document in request.documents),
        )


def test_indexing_uses_real_qdrant_adapter() -> None:
    request = RetrievalIndexRequest(
        documents=[
            NormalizedDocument(
                id="document-1",
                source_type="docx",
                title="report.docx",
                content="Nickel recovery 82 %",
            )
        ]
    )
    app_request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(storage_adapter=FakeStorageAdapter()))
    )

    result = asyncio.run(index_documents(request, app_request))

    assert result.vector_write.mode == "live"
    assert result.vector_write.document_ids == ["document-1"]


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


def test_indexing_returns_explicit_qdrant_mock_counts() -> None:
    table = TableBlock(
        id="table-1",
        document_id="document-1",
        page=1,
        headers=["parameter", "value"],
        rows=[["recovery", "82 %"]],
    )
    request = RetrievalIndexRequest(
        documents=[
            NormalizedDocument(
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
                table_blocks=[table],
            )
        ]
    )
    app_request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(storage_adapter=FakeStorageAdapter()))
    )

    result = asyncio.run(index_documents(request, app_request))

    assert result.vector_write.mode == "live"
    assert result.vector_write.records_count == 1


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
