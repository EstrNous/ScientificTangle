from scripts.query_reliability import build_reliability_report, classify_query_outcome


def test_reliability_report_aggregates_scenarios() -> None:
    report = build_reliability_report(
        [
            {"id": "legacy-default", "category": "feature_flag", "status": "pass"},
            {"id": "graph-fallback", "category": "fallback", "status": "pass"},
            {"id": "retrieval-timeout", "category": "timeout", "status": "pass"},
        ]
    )
    assert report["schema_version"] == "ml_reliability_report.v1"
    assert report["total"] == 3
    assert report["passed"] == 3
    assert report["failed"] == 0
    assert report["ok"] is True
    assert report["categories"] == ["fallback", "feature_flag", "timeout"]


def test_classify_query_outcome_detects_fallback_and_legacy() -> None:
    assert (
        classify_query_outcome(
            status_code=200,
            pipeline_mode="top1_scientific",
            warnings=["graph_exact_fallback:knowledge_timeout"],
        )
        == "degraded_fallback"
    )
    assert (
        classify_query_outcome(
            status_code=200,
            pipeline_mode="legacy",
            warnings=[],
        )
        == "legacy_ok"
    )
    assert (
        classify_query_outcome(
            status_code=504,
            pipeline_mode=None,
            warnings=[],
        )
        == "failed"
    )
