from shared.contracts import (
    IngestionReport,
    IngestionTaskPayload,
    KnowledgeIngestionRequest,
    NormalizeStoredSourcesResponse,
    RetrievalIndexResponse,
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
