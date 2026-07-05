from pathlib import Path


def test_e5_storage_migration_revision_chain() -> None:
    source = (
        Path(__file__).parents[1]
        / "storage"
        / "versions"
        / "0012_add_product_events_storage.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "0012"' in source
    assert 'down_revision: str | None = "0011"' in source
    assert '"audit_csv_exports"' in source
    assert '"bucket_name"' in source
    assert '"completed_at"' in source


def test_e5_storage_migration_defines_expected_indexes() -> None:
    source = (
        Path(__file__).parents[1]
        / "storage"
        / "versions"
        / "0012_add_product_events_storage.py"
    ).read_text(encoding="utf-8")
    assert '"ix_export_jobs_user_created_id"' in source
    assert '"ix_export_artifacts_expires_at"' in source
    assert '"ix_export_artifacts_bucket_storage_key"' in source
    assert '"ix_audit_csv_exports_user_created_id"' in source


def test_e5_notification_storage_migration_revision_chain() -> None:
    root = Path(__file__).resolve().parents[3]
    source = (
        root
        / "infra"
        / "postgres"
        / "notification_db"
        / "storage"
        / "versions"
        / "0004_add_product_notification_indexes.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "0004"' in source
    assert 'down_revision: str | None = "0003"' in source
    assert '"ix_notifications_user_type_created_id"' in source
    assert '"ix_notifications_user_unread_created"' in source
