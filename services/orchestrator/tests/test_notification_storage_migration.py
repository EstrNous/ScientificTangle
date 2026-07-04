from pathlib import Path


def test_notification_storage_migration_revision_chain() -> None:
    root = Path(__file__).resolve().parents[3]
    source = (
        root
        / "infra"
        / "postgres"
        / "notification_db"
        / "storage"
        / "versions"
        / "0002_add_core_notification_storage.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "0002"' in source
    assert 'down_revision: str | None = "0001"' in source
    assert '"reference_type"' in source
    assert '"extracted_entities"' in source
    assert '"notification_match_results"' in source
    assert '"ix_notifications_user_created"' in source
