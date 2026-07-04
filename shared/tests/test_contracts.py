import pytest
from pydantic import ValidationError

from shared.contracts import (
    IngestionReport,
    IngestionTaskPayload,
    KnowledgeIngestionRequest,
    NormalizedDocument,
    NormalizeStoredSourcesResponse,
    QueryIR,
    RetrievalIndexResponse,
    SourceSpan,
    StorageWriteResult,
)


def test_existing_ingestion_contracts_remain_frozen() -> None:
    assert list(IngestionReport.model_fields) == [
        "stage",
        "sources",
        "warnings",
        "normalized_documents",
        "documents_count",
        "source_spans_count",
        "tables_count",
        "indexed_points_count",
        "extracted_claims_count",
        "candidates_count",
    ]
    assert list(IngestionTaskPayload.model_fields) == [
        "id",
        "status",
        "report",
        "error_message",
        "created_at",
        "updated_at",
    ]


def test_source_span_rejects_invalid_source_type() -> None:
    with pytest.raises(ValidationError):
        SourceSpan(
            document_id="d1",
            page=1,
            start_offset=0,
            end_offset=1,
            text="x",
            source_type="invalid",
        )


def test_new_cross_service_contracts_are_exported() -> None:
    assert KnowledgeIngestionRequest.model_fields
    assert NormalizeStoredSourcesResponse.model_fields
    assert RetrievalIndexResponse.model_fields
    result = StorageWriteResult(backend="neo4j")
    assert result.mode == "mock"


def test_source_span_id_is_stable_and_serialized() -> None:
    payload = {
        "document_id": "doc-1",
        "page": 2,
        "start_offset": 10,
        "end_offset": 20,
        "text": "Никель 82 %",
        "source_type": "text",
    }

    first = SourceSpan.model_validate(payload)
    second = SourceSpan.model_validate(payload)

    assert first.id == second.id
    assert first.model_dump()["id"] == first.id


def test_normalized_document_accepts_valid_span() -> None:
    span = SourceSpan(
        document_id="d1",
        page=1,
        start_offset=0,
        end_offset=5,
        text="hello",
        source_type="text",
    )
    document = NormalizedDocument(
        id="d1",
        source_type="article",
        title="T",
        content="hello",
        source_spans=[span],
    )
    assert document.source_spans[0].text == "hello"


def test_query_ir_minimal() -> None:
    query = QueryIR(
        raw_query="test",
        filters={},
        entities=[],
        intent="fact_lookup",
    )
    assert query.raw_query == "test"
