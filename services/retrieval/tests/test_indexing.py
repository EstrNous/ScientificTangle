from unittest.mock import AsyncMock

from app.api.query import collect_index_links
import httpx
from fastapi.testclient import TestClient
from app.api.query import source_span_id
from app.main import app
from shared.contracts import (
    KnowledgeIngestionResponse,
    NormalizedDocument,
    SourceSpan,
    StorageWriteResult,
)

COLLECTION_NAME = "st_evidence_v1"


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
