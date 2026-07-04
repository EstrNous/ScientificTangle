from app.qdrant_adapter import (
    build_filter,
    payload_allowed,
    payload_to_search_result,
    payload_to_source,
    payload_to_span,
)


def test_payload_allowed_public_for_any_role() -> None:
    payload = {"access_level": "public"}
    assert payload_allowed(payload, ["guest"]) is True


def test_payload_allowed_internal_requires_matching_role() -> None:
    payload = {"access_level": "internal", "allowed_roles": ["researcher"]}
    assert payload_allowed(payload, ["researcher"]) is True
    assert payload_allowed(payload, ["guest"]) is False


def test_payload_allowed_admin_bypasses_restrictions() -> None:
    payload = {"access_level": "restricted", "allowed_roles": ["director"]}
    assert payload_allowed(payload, ["admin"]) is True


def test_payload_to_span_maps_required_fields() -> None:
    span = payload_to_span(
        {
            "document_id": "doc-1",
            "page": 2,
            "start_offset": 3,
            "end_offset": 8,
            "text": "nickel",
            "source_type": "text",
        }
    )
    assert span.document_id == "doc-1"
    assert span.page == 2
    assert span.text == "nickel"


def test_payload_to_search_result_preserves_score_and_claims() -> None:
    result = payload_to_search_result(
        {
            "document_id": "doc-1",
            "page": 1,
            "start_offset": 0,
            "end_offset": 5,
            "text": "Ni 82%",
            "document_title": "Report",
            "claim_ids": ["claim-1"],
            "graph_entity_ids": ["Ni"],
        },
        0.87,
    )
    assert result.relevance_score == 0.87
    assert result.claim_ids == ["claim-1"]
    assert result.source.document_title == "Report"


def test_payload_to_source_exposes_highlight_fields() -> None:
    source = payload_to_source(
        {
            "document_id": "doc-1",
            "document_title": "Report",
            "page": 1,
            "start_offset": 0,
            "end_offset": 22,
            "highlight_start": 0,
            "highlight_end": 9,
            "text": "Никель 82 % в таблице",
            "source_span_id": "span-1",
            "source_type": "text",
            "document_source_type": "report",
            "access_level": "internal",
        }
    )

    assert source.source_span.id == "span-1"
    assert source.source_span.document_id == "doc-1"
    assert source.source_span.start_offset == 0
    assert source.source_span.end_offset == 22
    assert source.highlight_start == 0
    assert source.highlight_end == 9
    assert source.highlight_text == "Никель 82"
    assert source.highlight_fragments == ["Никель 82"]


def test_build_filter_allows_internal_documents_without_role_pin() -> None:
    qdrant_filter = build_filter({}, ["researcher"])
    access_should = qdrant_filter["must"][0]["should"]

    assert {
        "must": [
            {"key": "access_level", "match": {"value": "internal"}},
            {"is_empty": {"key": "allowed_roles"}},
        ]
    } in access_should


def test_build_filter_combines_access_numeric_geo_time_and_dictionary_filters() -> None:
    qdrant_filter = build_filter(
        {
            "numeric_constraints": [{"value": 82, "unit": "%"}],
            "geo_constraints": ["Россия"],
            "time_constraints": {"start_year": 2021, "end_year": 2024},
            "source_type_constraints": ["report"],
            "dictionary_version_id": "dict-v1",
        },
        ["researcher"],
    )

    must = qdrant_filter["must"]
    assert {"key": "document_source_type", "match": {"any": ["report"]}} in must
    assert {"key": "dictionary_version_id", "match": {"value": "dict-v1"}} in must
    assert {"key": "units", "match": {"value": "%"}} in must
    assert {"key": "numeric_min", "range": {"lte": 82.0}} in must
    assert {"key": "numeric_max", "range": {"gte": 82.0}} in must
    assert {"key": "published_year", "range": {"gte": 2021}} in must
    assert {"key": "published_year", "range": {"lte": 2024}} in must
    assert {
        "should": [
            {"key": "geo_bucket", "match": {"any": ["россия"]}},
            {"key": "geo_country", "match": {"any": ["россия"]}},
        ]
    } in must
