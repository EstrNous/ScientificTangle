from datetime import UTC, datetime
from uuid import uuid4

from infra.postgres.orchestrator_db.e5_fixtures import (
    load_e5_fixture,
    validate_e5_fixture,
)
from infra.postgres.orchestrator_db.models import AuditEvent
from infra.postgres.orchestrator_db.product_events_storage import (
    AUDIT_CSV_COLUMNS,
    PRODUCT_AUDIT_ACTIONS,
    ProductEventsStorageRepository,
)


def test_e5_fixture_loads_and_validates() -> None:
    payload = load_e5_fixture()
    assert validate_e5_fixture(payload) == []
    assert payload["export_jobs"][0]["artifacts"]
    assert payload["audit_csv_export"]["row_count"] > 0


def test_e5_fixture_rejects_missing_artifact_storage_key() -> None:
    payload = load_e5_fixture()
    payload["export_jobs"][0]["artifacts"][0].pop("storage_key")
    errors = validate_e5_fixture(payload)
    assert any("storage_key" in error for error in errors)


def test_product_audit_actions_cover_fixture_events() -> None:
    payload = load_e5_fixture()
    fixture_actions = {event["action"] for event in payload["audit_events"]}
    assert fixture_actions <= PRODUCT_AUDIT_ACTIONS


def test_audit_events_to_csv_contains_header_and_rows() -> None:
    repo = ProductEventsStorageRepository(session=None)  # type: ignore[arg-type]
    created_at = datetime.now(UTC)
    events = [
        AuditEvent(
            id=uuid4(),
            user_id=uuid4(),
            action="document_exported",
            resource_type="export_job",
            resource_id="job-1",
            details={"format": "markdown", "query_run_id": "run-1", "role": "researcher", "status": "completed"},
            request_id="req-1",
            created_at=created_at,
        )
    ]
    csv_text = repo.audit_events_to_csv(events)
    header = ",".join(AUDIT_CSV_COLUMNS)
    assert csv_text.startswith(header)
    assert "document_exported" in csv_text
    assert "job-1" in csv_text
