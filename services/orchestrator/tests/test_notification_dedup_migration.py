def test_notification_dedup_migration_revision_chain() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    source = (
        root
        / "infra"
        / "postgres"
        / "notification_db"
        / "storage"
        / "versions"
        / "0005_add_notification_dedup_index.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "0005"' in source
    assert 'down_revision: str | None = "0004"' in source
    assert '"uq_notifications_user_type_reference_id"' in source
