import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

DEFAULT_ARTIFACT_MANIFEST_PATH = "eval/pinned_demo_artifact.json"
DEFAULT_SUITES_PATH = "eval/regression_suites.json"

QUALITY_THRESHOLDS = {
    "citation_coverage": (0.8, True),
    "unsupported_claim_rate": (0.1, False),
    "answer_completeness": (0.8, True),
    "query_trace_completeness": (1.0, True),
    "access_leak_rate": (0.0, False),
    "latency_ms_p95": (5000.0, False),
}


def evaluate_demo_quality(
    report: dict[str, Any] | None,
    artifact_manifest: dict[str, Any],
    suites: dict[str, Any],
    root: Path,
) -> dict[str, Any]:
    checks = [
        manifest_integrity_check(artifact_manifest, root),
        suite_integrity_check(suites),
    ]
    if report is None:
        checks.append(
            {
                "id": "live_eval_report",
                "status": "blocked",
                "details": "live eval report is not available; real model runs are disabled",
            }
        )
    else:
        checks.extend(report_quality_checks(report))
    overall_status = "pass"
    if any(item["status"] == "fail" for item in checks):
        overall_status = "fail"
    elif any(item["status"] == "blocked" for item in checks):
        overall_status = "blocked"
    elif any(item["status"] == "warn" for item in checks):
        overall_status = "warn"
    return {
        "schema_version": "demo_quality_gate.v1",
        "overall_status": overall_status,
        "checks": checks,
        "known_limits": known_limits(report),
    }


def manifest_integrity_check(manifest: dict[str, Any], root: Path) -> dict[str, Any]:
    mismatches = []
    for item in manifest.get("inputs", []):
        path = root / item["path"]
        expected = item.get("sha256")
        actual = sha256_file(path) if path.exists() else None
        if actual != expected:
            mismatches.append({"path": item["path"], "expected": expected, "actual": actual})
    return {
        "id": "pinned_input_integrity",
        "status": "pass" if not mismatches else "fail",
        "details": "all pinned input sha256 values match" if not mismatches else mismatches,
    }


def suite_integrity_check(suites: dict[str, Any]) -> dict[str, Any]:
    required = {"official_questions", "hybrid_retrieval", "access_filtering", "unsupported_claims", "answer_completeness"}
    actual = set(suites.get("suites", {}))
    missing = sorted(required - actual)
    return {
        "id": "regression_suite_inventory",
        "status": "pass" if not missing else "fail",
        "details": "all required suites are declared" if not missing else {"missing": missing},
    }


def report_quality_checks(report: dict[str, Any]) -> list[dict[str, Any]]:
    checks = []
    checks.append(
        {
            "id": "answered_questions",
            "status": "pass" if report.get("answered_200") == report.get("total_questions") else "fail",
            "details": {
                "answered_200": report.get("answered_200"),
                "total_questions": report.get("total_questions"),
            },
        }
    )
    checks.append(
        {
            "id": "question_blockers",
            "status": "pass" if not report.get("dashboard_data", {}).get("blocker_question_ids") else "fail",
            "details": report.get("dashboard_data", {}).get("blocker_question_ids", []),
        }
    )
    metrics = report.get("metrics", {})
    for metric, (threshold, higher_is_better) in QUALITY_THRESHOLDS.items():
        checks.append(metric_check(metric, metrics.get(metric), threshold, higher_is_better))
    return checks


def metric_check(metric: str, value: Any, threshold: float, higher_is_better: bool) -> dict[str, Any]:
    if not isinstance(value, (int, float)):
        return {"id": metric, "status": "blocked", "details": "metric is absent from report"}
    passed = value >= threshold if higher_is_better else value <= threshold
    return {
        "id": metric,
        "status": "pass" if passed else "fail",
        "details": {"value": value, "threshold": threshold},
    }


def known_limits(report: dict[str, Any] | None) -> list[str]:
    limits = [
        "live model answers are not pinned and must not be committed as demo facts",
        "full raw corpus source spans require normalization before they can become reviewed expected_source_span_ids",
        "access_filtering fixture covers a narrow forbidden span smoke",
    ]
    if report is None:
        limits.append("quality status is blocked until a permitted seeded-stack eval report is available")
    return limits


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    target = Path(path)
    if not target.exists():
        return None
    return json.loads(target.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report")
    parser.add_argument("--artifact-manifest", default=DEFAULT_ARTIFACT_MANIFEST_PATH)
    parser.add_argument("--suites", default=DEFAULT_SUITES_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path.cwd()
    result = evaluate_demo_quality(
        load_json(args.report),
        load_json(args.artifact_manifest) or {},
        load_json(args.suites) or {},
        root,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
