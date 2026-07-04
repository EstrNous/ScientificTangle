from scripts.seed_inventory import (
    compute_fixture_expectations,
    validate_offline_counts,
    StoreStatus,
)


def test_fixture_expectations_cover_offline_chain() -> None:
    expectations = compute_fixture_expectations()
    assert expectations["indexed_documents_min"] >= 5
    assert expectations["source_span_lookup_min"] >= 4
    assert expectations["export_jobs_min"] >= 1
    assert expectations["audit_csv_exports_min"] >= 1
    assert expectations["user_interests_min"] >= 1


def test_validate_offline_counts_passes_when_minimums_met() -> None:
    expectations = compute_fixture_expectations()
    postgresql = StoreStatus(
        status="ok",
        counts={
            "users": expectations["users_min"],
            "indexed_documents": expectations["indexed_documents_min"],
            "source_span_lookup": expectations["source_span_lookup_min"],
            "review_decisions": expectations["review_decisions_min"],
            "document_cascade_refs": expectations["document_cascade_refs_min"],
            "export_jobs": expectations["export_jobs_min"],
            "export_artifacts": expectations["export_artifacts_min"],
            "audit_events": expectations["audit_events_min"],
            "notifications": expectations["notification_events_min"],
            "audit_csv_exports": expectations["audit_csv_exports_min"],
            "user_interests": expectations["user_interests_min"],
        },
    )
    result = validate_offline_counts(postgresql, expectations)
    assert result["status"] == "pass"
    assert not result["failures"]


def test_validate_offline_counts_fails_on_missing_documents() -> None:
    expectations = compute_fixture_expectations()
    postgresql = StoreStatus(status="ok", counts={"indexed_documents": 0})
    result = validate_offline_counts(postgresql, expectations)
    assert result["status"] == "fail"
    assert any("indexed_documents" in failure for failure in result["failures"])
