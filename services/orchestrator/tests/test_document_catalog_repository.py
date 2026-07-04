from datetime import UTC, datetime
from uuid import uuid4

from infra.postgres.orchestrator_db.document_catalog_repository import (
    DocumentCatalogRepository,
    vector_point_id,
)
from infra.postgres.orchestrator_db.models import IndexedDocument


def test_vector_point_id_is_stable_and_distinct() -> None:
    first = vector_point_id("span-alpha")
    second = vector_point_id("span-alpha")
    other = vector_point_id("span-beta")
    assert first == second
    assert first != other


def test_indexed_document_item_maps_catalog_status() -> None:
    repo = DocumentCatalogRepository(session=None)
    now = datetime.now(UTC)
    task_id = uuid4()
    completed = IndexedDocument(
        document_id="doc-completed",
        task_id=task_id,
        title="Completed",
        source_type="pdf",
        source_spans_count=3,
        indexed_points_count=3,
        access_level="internal",
        metadata_={"source_path": "reports/q1.pdf", "warnings": ["note"]},
        created_at=now,
    )
    no_index = IndexedDocument(
        document_id="doc-no-index",
        task_id=task_id,
        title="No index",
        source_type="pdf",
        source_spans_count=2,
        indexed_points_count=0,
        access_level="internal",
        metadata_={},
        created_at=now,
    )
    no_spans = IndexedDocument(
        document_id="doc-no-spans",
        task_id=task_id,
        title="No spans",
        source_type="pdf",
        source_spans_count=0,
        indexed_points_count=0,
        access_level="restricted",
        metadata_={"error_message": "empty"},
        created_at=now,
    )

    completed_item = repo._indexed_document_item(completed)
    no_index_item = repo._indexed_document_item(no_index)
    no_spans_item = repo._indexed_document_item(no_spans)

    assert completed_item["status"] == "completed"
    assert completed_item["source_path"] == "reports/q1.pdf"
    assert completed_item["warnings"] == ["note"]
    assert no_index_item["status"] == "no_index"
    assert no_spans_item["status"] == "no_source_spans"
    assert no_spans_item["error_message"] == "empty"
