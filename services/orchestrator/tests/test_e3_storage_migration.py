from pathlib import Path


def test_e3_storage_migration_revision_chain() -> None:
    source = (
        Path(__file__).parents[1]
        / "storage"
        / "versions"
        / "0010_add_workflow_state_storage.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "0010"' in source
    assert 'down_revision: str | None = "0009"' in source
    assert '"cascade_status"' in source
    assert '"cascade_steps"' in source
    assert '"ix_notifications_user_created_id"' not in source


def test_e3_storage_migration_defines_expected_indexes() -> None:
    source = (
        Path(__file__).parents[1]
        / "storage"
        / "versions"
        / "0010_add_workflow_state_storage.py"
    ).read_text(encoding="utf-8")
    assert '"ix_document_cascade_refs_cascade_status"' in source
    assert '"ix_audit_events_created_id"' in source
    assert '"ix_audit_events_action_created_id"' in source
    assert '"ix_review_decisions_status_created_id"' in source


def test_e3_notification_storage_migration_revision_chain() -> None:
    root = Path(__file__).resolve().parents[3]
    source = (
        root
        / "infra"
        / "postgres"
        / "notification_db"
        / "storage"
        / "versions"
        / "0003_add_workflow_notification_indexes.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "0003"' in source
    assert 'down_revision: str | None = "0002"' in source
    assert '"ix_notifications_user_created_id"' in source
    assert '"ix_notification_match_results_user_created_id"' in source
