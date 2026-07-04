from datetime import UTC, datetime
from uuid import UUID, uuid4

from infra.postgres.common.cursor import decode_cursor, encode_cursor
from infra.postgres.orchestrator_db.e3_fixtures import load_e3_fixture, validate_e3_fixture


def test_e3_fixture_loads_and_validates() -> None:
    payload = load_e3_fixture()
    assert validate_e3_fixture(payload) == []
    assert payload["user_interests"]
    assert payload["notification_matches"]
    assert payload["document_deletion"]["document_id"] == "e3-delete-target"


def test_e3_fixture_flags_missing_document_id() -> None:
    payload = load_e3_fixture()
    payload["document_deletion"] = {}
    errors = validate_e3_fixture(payload)
    assert any("document_deletion requires document_id" in error for error in errors)


def test_cursor_roundtrip() -> None:
    created_at = datetime(2026, 7, 4, 10, 30, tzinfo=UTC)
    item_id = uuid4()
    cursor = encode_cursor(created_at, item_id)
    decoded_created_at, decoded_id = decode_cursor(cursor)
    assert decoded_id == item_id
    assert decoded_created_at.astimezone(UTC) == created_at
