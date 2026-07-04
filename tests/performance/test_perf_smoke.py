from scripts.perf_smoke import build_report


def test_perf_smoke_report_contains_latency_percentiles() -> None:
    report = build_report(
        [
            {"question_id": "official-001", "status_code": 200, "latency_ms": 100, "has_evidence": True},
            {"question_id": "official-002", "status_code": 200, "latency_ms": 200, "has_evidence": True},
            {"question_id": "official-003", "status_code": 200, "latency_ms": 300, "has_evidence": False},
        ]
    )

    assert report["schema_version"] == "ml_perf_report.v1"
    assert report["ok"] == 3
    assert report["with_evidence"] == 2
    assert report["latency_ms_p50"] == 200
    assert report["latency_ms_p95"] == 300
