from app.qdrant_adapter import payload_allowed, payload_to_search_result, payload_to_span


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
