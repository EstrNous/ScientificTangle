from datetime import datetime

import pytest
from pydantic import ValidationError

from shared.contracts import (
    AuditEvent,
    DeleteDocumentResult,
    DocumentCatalogItem,
    DocumentCatalogResponse,
    EvalReportSummaryPayload,
    ExportPayload,
    ExportRequest,
    IngestionReport,
    IngestionTaskPayload,
    KnowledgeIngestionRequest,
    NormalizedDocument,
    NormalizeStoredSourcesResponse,
    NotificationListPayload,
    NotificationPayload,
    QueryIR,
    RetrievalIndexResponse,
    ReviewDecisionPayload,
    ReviewQueuePayload,
    SourceSpan,
    StorageWriteResult,
    UserInterestItem,
    UserInterestsPayload,
)


def test_ingestion_contract_extension_is_additive() -> None:
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
        "task_kind",
        "dictionary_version_id",
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
    assert ExportRequest.model_fields
    assert ExportPayload.model_fields
    assert KnowledgeIngestionRequest.model_fields
    assert NormalizeStoredSourcesResponse.model_fields
    assert RetrievalIndexResponse.model_fields
    assert DeleteDocumentResult.model_fields
    assert EvalReportSummaryPayload.model_fields
    assert NotificationPayload.model_fields
    assert NotificationListPayload.model_fields
    assert ReviewQueuePayload.model_fields
    assert ReviewDecisionPayload.model_fields
    assert UserInterestsPayload.model_fields
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


def test_audit_event_accepts_extended_runtime_fields() -> None:
    event = AuditEvent(
        id="event-1",
        user="user-1",
        user_id="user-1",
        role="researcher",
        action="source_viewed",
        status="success",
        object="span-1",
        resource_type="source_span",
        resource_id="span-1",
        request_id="req-1",
        timestamp="2026-07-04T12:00:00+00:00",
        details={"source_span_id": "span-1"},
        source_span_id="span-1",
    )

    assert event.role == "researcher"
    assert event.status == "success"
    assert event.details["source_span_id"] == "span-1"


def test_e1_payloads_accept_minimal_offline_shapes() -> None:
    span = SourceSpan(
        document_id="doc-1",
        page=1,
        start_offset=0,
        end_offset=10,
        text="Никель",
        source_type="text",
    )
    interest = UserInterestsPayload(
        user_id="550e8400-e29b-41d4-a716-446655440000",
        interests=[UserInterestItem(label="nickel", weight=0.8, source_terms=["Ni"])],
    )
    delete_result = DeleteDocumentResult(
        document_id=span.document_id,
        status="accepted",
        tombstone_id="550e8400-e29b-41d4-a716-446655440001",
    )
    report = EvalReportSummaryPayload(
        status="blocked_by_policy",
        blocked_checks=["live_model_quality"],
    )

    assert interest.interests[0].label == "nickel"
    assert delete_result.document_id == "doc-1"
    assert report.blocked_checks == ["live_model_quality"]


def test_document_catalog_contract_roundtrip() -> None:
    created_at = datetime.fromisoformat("2026-07-05T12:00:00+00:00")
    item = DocumentCatalogItem(
        document_id="doc-1",
        title="Quarterly report",
        source_path="reports/q1.pdf",
        source_type="application/pdf",
        status="completed",
        source_spans_count=4,
        indexed_points_count=4,
        created_at=created_at,
    )
    payload = DocumentCatalogResponse(items=[item], total=1, filters_applied={"status": "completed"})
    assert payload.items[0].document_id == "doc-1"
    assert payload.total == 1
    assert payload.filters_applied["status"] == "completed"
