from pathlib import Path


def test_e4_storage_migration_revision_chain() -> None:
    source = (
        Path(__file__).parents[1]
        / "storage"
        / "versions"
        / "0011_add_evidence_access_storage.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "0011"' in source
    assert 'down_revision: str | None = "0010"' in source
    assert '"access_level"' in source
    assert '"allowed_roles"' in source


def test_e4_storage_migration_defines_expected_indexes() -> None:
    source = (
        Path(__file__).parents[1]
        / "storage"
        / "versions"
        / "0011_add_evidence_access_storage.py"
    ).read_text(encoding="utf-8")
    assert '"ix_source_span_lookup_access_level"' in source
    assert '"ix_source_span_lookup_document_access"' in source
    assert '"ix_indexed_documents_access_deletion"' in source
