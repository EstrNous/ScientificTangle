from shared.contracts import (
    IngestionReport,
    IngestionTaskPayload,
    KnowledgeIngestionRequest,
    NormalizeStoredSourcesResponse,
    RetrievalIndexResponse,
    SourceSpan,
    StorageWriteResult,
)


def test_existing_ingestion_contracts_remain_frozen() -> None:
    assert list(IngestionReport.model_fields) == ["stage", "sources", "warnings"]
    assert list(IngestionTaskPayload.model_fields) == [
        "id",
        "status",
        "report",
        "error_message",
        "created_at",
        "updated_at",
    ]


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
