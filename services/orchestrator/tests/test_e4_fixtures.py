from infra.postgres.orchestrator_db.access_audit import (
    build_access_denied_details,
    build_export_audit_details,
    build_search_audit_details,
    build_source_viewed_details,
    validate_access_audit_details,
)
from infra.postgres.orchestrator_db.e4_fixtures import (
    load_e4_fixture,
    validate_e4_fixture,
    validate_qdrant_payload_fixture,
)


def test_e4_fixture_loads_and_validates() -> None:
    payload = load_e4_fixture()
    assert validate_e4_fixture(payload) == []
    assert payload["access_expectations"]["external_partner"]["forbidden_source_span_ids"]
    assert any(
        document["access_level"] == "restricted"
        for document in payload["indexed_documents"]
    )


def test_e4_fixture_flags_missing_partner_user() -> None:
    payload = load_e4_fixture()
    payload["users"] = []
    errors = validate_e4_fixture(payload)
    assert any("external_partner" in error for error in errors)


def test_e4_qdrant_payload_requires_filter_fields() -> None:
    payload = load_e4_fixture()
    sample = dict(payload["qdrant_payloads"][0])
    sample.pop("dictionary_version_id")
    errors = validate_qdrant_payload_fixture(sample)
    assert any("dictionary_version_id" in error for error in errors)


def test_access_audit_detail_builders_cover_e4_actions() -> None:
    denied = build_access_denied_details(
        role="external_partner",
        source_span_id="e4span-confidential-cost-001",
        document_id="e4-doc-confidential",
        reason="access_policy",
    )
    viewed = build_source_viewed_details(
        source_span_id="e4span-public-injection-001",
        role="external_partner",
        status="success",
        document_id="e4-doc-public",
    )
    search = build_search_audit_details(
        query="никель Россия 2024",
        role="researcher",
        status="success",
        result_count=2,
        filters={"geo_constraints": ["Россия"]},
    )
    exported = build_export_audit_details(
        query_run_id="e4-query-run-001",
        export_format="markdown",
        role="researcher",
        status="completed",
    )

    assert validate_access_audit_details("access_denied", denied) == []
    assert validate_access_audit_details("source_viewed", viewed) == []
    assert validate_access_audit_details("search", search) == []
    assert validate_access_audit_details("document_exported", exported) == []
