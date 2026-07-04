from infra.postgres.orchestrator_db.e4_fixtures import QDRANT_FILTER_FIELDS, load_e4_fixture
from app.api.query import payload_indexes


def test_e4_fixture_qdrant_payloads_cover_filter_fields() -> None:
    payload = load_e4_fixture()
    for item in payload["qdrant_payloads"]:
        missing = QDRANT_FILTER_FIELDS - set(item)
        assert not missing, f"{item.get('point_id')} missing {sorted(missing)}"


def test_e4_fixture_table_payload_has_row_id_for_filters() -> None:
    payload = load_e4_fixture()
    table_payloads = [
        item for item in payload["qdrant_payloads"] if item["source_type"] == "table"
    ]
    assert table_payloads
    assert all(item["table_row_id"] for item in table_payloads)


def test_payload_indexes_include_dictionary_version_and_highlight_fields() -> None:
    indexes = payload_indexes()
    assert indexes["dictionary_version_id"] == "keyword"
    assert indexes["highlight_start"] == "integer"
    assert indexes["highlight_end"] == "integer"
    assert "dictionary_version_id" in indexes
