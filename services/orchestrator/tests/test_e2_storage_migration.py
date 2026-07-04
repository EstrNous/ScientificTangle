from pathlib import Path


def test_e2_storage_migration_revision_chain() -> None:
    source = (
        Path(__file__).parents[1]
        / "storage"
        / "versions"
        / "0009_add_review_source_delete_storage.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "0009"' in source
    assert 'down_revision: str | None = "0008"' in source
    assert '"source_span_lookup"' in source
    assert '"document_cascade_refs"' in source


def test_e2_storage_migration_defines_expected_indexes() -> None:
    source = (
        Path(__file__).parents[1]
        / "storage"
        / "versions"
        / "0009_add_review_source_delete_storage.py"
    ).read_text(encoding="utf-8")
    assert '"ix_source_span_lookup_document_id"' in source
    assert '"ix_source_span_lookup_table_row_id"' in source
    assert '"ix_source_span_lookup_document_page"' in source
    assert '"ix_document_cascade_refs_updated_at"' in source
    assert '"highlight_start"' in source
    assert '"highlight_end"' in source
    assert '"table_row_id"' in source
    assert '"minio_object_refs"' in source
