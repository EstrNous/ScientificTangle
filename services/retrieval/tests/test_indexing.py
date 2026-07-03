import asyncio

from app.api.query import collect_index_links
from shared.contracts import (
    KnowledgeIngestionResponse,
    NormalizedDocument,
    RetrievalIndexRequest,
    SourceSpan,
    StorageWriteResult,
)


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
