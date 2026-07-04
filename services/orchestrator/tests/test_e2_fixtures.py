from infra.postgres.orchestrator_db.e2_fixtures import load_e2_fixture, validate_e2_fixture
from infra.postgres.orchestrator_db.review_storage import table_row_id_from_block


def test_e2_fixture_loads_and_validates() -> None:
    payload = load_e2_fixture()
    assert validate_e2_fixture(payload) == []
    assert payload["source_span_lookup"]
    assert payload["document_cascade_refs"]
    assert payload["neo4j_candidates"]


def test_e2_fixture_flags_invalid_highlight_range() -> None:
    payload = load_e2_fixture()
    payload["source_span_lookup"][0]["highlight_start"] = 500
    payload["source_span_lookup"][0]["highlight_end"] = 10
    errors = validate_e2_fixture(payload)
    assert any("invalid highlight range" in error for error in errors)


def test_table_row_id_from_block() -> None:
    assert table_row_id_from_block("tbl-1:row:2") == "tbl-1:row:2"
    assert table_row_id_from_block("tbl-1") is None
    assert table_row_id_from_block(None) is None
