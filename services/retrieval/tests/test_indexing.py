import asyncio

from app.api.indexing import index_documents
from shared.contracts import (
    KnowledgeIngestionResponse,
    NormalizedDocument,
    RetrievalIndexRequest,
    SourceSpan,
    StorageWriteResult,
    TableBlock,
)


def test_indexing_returns_explicit_qdrant_mock_counts() -> None:
    table = TableBlock(
        id="table-1",
        document_id="document-1",
        page=1,
        headers=["parameter", "value"],
        rows=[["recovery", "82 %"]],
    )
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
        table_blocks=[table],
    )
    request = RetrievalIndexRequest(
        documents=[document],
        knowledge_results=[
            KnowledgeIngestionResponse(
                document_id=document.id,
                graph_write=StorageWriteResult(
                    backend="neo4j",
                    document_ids=[document.id],
                    warnings=["neo4j_adapter_pending"],
                ),
            )
        ],
    )

    result = asyncio.run(index_documents(request))

    assert result.vector_write.backend == "qdrant"
    assert result.vector_write.mode == "mock"
    assert result.vector_write.records_count == 3
    assert result.warnings == ["qdrant_adapter_pending"]
