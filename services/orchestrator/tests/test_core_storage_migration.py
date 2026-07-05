from pathlib import Path


def test_core_storage_migration_revision_chain() -> None:
    source = (
        Path(__file__).parents[1]
        / "storage"
        / "versions"
        / "0008_add_core_storage_foundation.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "0008"' in source
    assert 'down_revision: str | None = "0007"' in source
    assert '"review_decisions"' in source
    assert '"export_artifacts"' in source
    assert '"deletion_status"' in source
    assert '"ix_audit_events_user_created_id"' in source


def test_core_storage_migration_defines_expected_objects() -> None:
    source = (
        Path(__file__).parents[1]
        / "storage"
        / "versions"
        / "0008_add_core_storage_foundation.py"
    ).read_text(encoding="utf-8")
    assert '"review_decisions"' in source
    assert '"export_artifacts"' in source
    assert '"deletion_status"' in source
    assert '"tombstone_reason"' in source
    assert '"ix_audit_events_user_created_id"' in source
    assert '"ix_export_jobs_user_status_created"' in source
    assert "uq_review_decisions_candidate" in source
