import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_GOLD_PATH = "eval/gold_questions.json"
DEFAULT_FIXTURES_PATH = "eval/reviewed_source_fixtures.json"
DEFAULT_ARTIFACT_MANIFEST_PATH = "eval/pinned_demo_artifact.json"
DEFAULT_SUITES_PATH = "eval/regression_suites.json"
DEFAULT_OUTPUT_BASE = "eval/reports/offline_readiness"

REQUIRED_E2E_SCENARIOS = {
    "query_created",
    "source_viewed",
    "document_exported",
}


def evaluate_offline_quality(
    gold: dict[str, Any],
    fixtures: dict[str, Any],
    artifact_manifest: dict[str, Any],
    suites: dict[str, Any],
    root: Path,
    report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    checks = [
        manifest_integrity_check(artifact_manifest, root),
        suite_integrity_check(suites),
        no_live_policy_check(fixtures),
        official_source_span_check(gold, fixtures),
        official_query_ir_constraint_check(gold),
        access_filtering_check(gold, suites),
        no_live_e2e_inventory_check(root),
        reviewed_data_blocker_check(fixtures),
        live_policy_block("live_answer_quality"),
        live_policy_block("live_latency_p95"),
    ]
    if report is not None:
        checks.extend(no_live_report_checks(report))
    status = overall_status(checks)
    return {
        "schema_version": "offline_quality_gate.v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "overall_status": status,
        "checks": checks,
        "summary": {
            "official_questions": len(official_questions(gold)),
            "corpus_regression_questions": len(gold.get("corpus_regression_questions", [])),
            "live_model_calls": "blocked_by_policy",
            "full_corpus_source_expectations": fixtures.get("external_dataset", {}).get("normalized_source_spans_status"),
        },
    }


def no_live_policy_check(fixtures: dict[str, Any]) -> dict[str, Any]:
    policy = fixtures.get("review_policy", {})
    status = "pass" if policy.get("live_model_calls") == "blocked_by_policy" else "fail"
    return {
        "id": "no_live_policy_declared",
        "status": status,
        "details": policy,
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
    required = {
        "official_questions",
        "hybrid_retrieval",
        "access_filtering",
        "unsupported_claims",
        "answer_completeness",
    }
    actual = set(suites.get("suites", {}))
    missing = sorted(required - actual)
    return {
        "id": "regression_suite_inventory",
        "status": "pass" if not missing else "fail",
        "details": "all required suites are declared" if not missing else {"missing": missing},
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def official_source_span_check(gold: dict[str, Any], fixtures: dict[str, Any]) -> dict[str, Any]:
    reviewed = {item.get("question_id"): item for item in fixtures.get("official_questions", [])}
    missing = []
    mismatched = []
    for question in official_questions(gold):
        ids = question.get("expected_source_span_ids", [])
        fixture = reviewed.get(question.get("id"))
        if not ids:
            missing.append(question.get("id"))
            continue
        if not fixture or fixture.get("expected_source_span_ids") != ids:
            mismatched.append(question.get("id"))
        review = question.get("expected_source_span_review", {})
        if review.get("status") != "reviewed":
            mismatched.append(question.get("id"))
    return {
        "id": "official_expected_source_spans",
        "status": "pass" if not missing and not mismatched else "fail",
        "details": {"missing": missing, "mismatched": sorted(set(mismatched))},
    }


def official_query_ir_constraint_check(gold: dict[str, Any]) -> dict[str, Any]:
    missing = []
    for question in official_questions(gold):
        has_constraints = bool(
            question.get("expected_entities")
            or question.get("expected_numeric_constraints")
            or question.get("expected_geo_constraints")
            or question.get("expected_time_constraints")
        )
        if not has_constraints:
            missing.append(question.get("id"))
    return {
        "id": "official_query_ir_constraints",
        "status": "pass" if not missing else "fail",
        "details": {"missing": missing},
    }


def access_filtering_check(gold: dict[str, Any], suites: dict[str, Any]) -> dict[str, Any]:
    questions = all_questions(gold)
    by_id = {question.get("id"): question for question in questions}
    suite_ids = suites.get("suites", {}).get("access_filtering", {}).get("question_ids", [])
    covered = [
        question_id
        for question_id in suite_ids
        if by_id.get(question_id, {}).get("expected_forbidden_source_span_ids")
    ]
    return {
        "id": "access_filtering_fixture",
        "status": "pass" if covered else "fail",
        "details": {"covered_question_ids": covered, "suite_question_ids": suite_ids},
    }


def no_live_e2e_inventory_check(root: Path) -> dict[str, Any]:
    path = root / "tests/e2e/test_official_questions_smoke.py"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    missing = sorted(item for item in REQUIRED_E2E_SCENARIOS if item not in text)
    has_source_resolve = "/source/" in text
    has_export = "/export" in text
    if not has_source_resolve:
        missing.append("source_resolve")
    if not has_export:
        missing.append("export")
    return {
        "id": "offline_e2e_scenario_inventory",
        "status": "pass" if not missing else "fail",
        "details": {"file": str(path.relative_to(root)), "missing": missing},
    }


def reviewed_data_blocker_check(fixtures: dict[str, Any]) -> dict[str, Any]:
    dataset = fixtures.get("external_dataset", {})
    blocked = dataset.get("normalized_source_spans_status") == "blocked_by_data"
    return {
        "id": "full_corpus_reviewed_source_expectations",
        "status": "blocked_by_data" if blocked else "pass",
        "details": {
            "status": dataset.get("normalized_source_spans_status"),
            "reason_codes": dataset.get("reason_codes", []),
        },
    }


def live_policy_block(check_id: str) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": "blocked_by_policy",
        "details": "live model calls are forbidden in E6 no-live quality gate",
    }


def no_live_report_checks(report: dict[str, Any]) -> list[dict[str, Any]]:
    checks = report_quality_checks(report)
    for item in checks:
        if item["id"] == "latency_ms_p95":
            item["status"] = "blocked_by_policy"
            item["details"] = {
                "reason": "live latency claims are forbidden in E6",
                "observed_offline_value": item.get("details", {}).get("value"),
            }
    return checks


def report_quality_checks(report: dict[str, Any]) -> list[dict[str, Any]]:
    checks = [
        {
            "id": "answered_questions",
            "status": "pass" if report.get("answered_200") == report.get("total_questions") else "fail",
            "details": {
                "answered_200": report.get("answered_200"),
                "total_questions": report.get("total_questions"),
            },
        },
        {
            "id": "question_blockers",
            "status": "pass" if not report.get("dashboard_data", {}).get("blocker_question_ids") else "fail",
            "details": report.get("dashboard_data", {}).get("blocker_question_ids", []),
        },
    ]
    metrics = report.get("metrics", {})
    thresholds = {
        "citation_coverage": (0.8, True),
        "unsupported_claim_rate": (0.1, False),
        "answer_completeness": (0.8, True),
        "query_trace_completeness": (1.0, True),
        "access_leak_rate": (0.0, False),
        "latency_ms_p95": (5000.0, False),
    }
    for metric, (threshold, higher_is_better) in thresholds.items():
        checks.append(metric_check(metric, metrics.get(metric), threshold, higher_is_better))
    return checks


def metric_check(metric: str, value: Any, threshold: float, higher_is_better: bool) -> dict[str, Any]:
    if not isinstance(value, (int, float)):
        return {"id": metric, "status": "blocked_by_data", "details": "metric is absent from report"}
    passed = value >= threshold if higher_is_better else value <= threshold
    return {
        "id": metric,
        "status": "pass" if passed else "fail",
        "details": {"value": value, "threshold": threshold},
    }


def official_questions(gold: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in gold.get("questions", []) if item.get("split") == "mvp" or str(item.get("id", "")).startswith("official-")]


def all_questions(gold: dict[str, Any]) -> list[dict[str, Any]]:
    return [*gold.get("questions", []), *gold.get("corpus_regression_questions", [])]


def overall_status(checks: list[dict[str, Any]]) -> str:
    statuses = {item["status"] for item in checks}
    if "fail" in statuses:
        return "fail"
    if "warn" in statuses or "blocked_by_data" in statuses:
        return "warn"
    return "pass"


def load_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_outputs(result: dict[str, Any], output_base: str) -> None:
    base = Path(output_base)
    base.parent.mkdir(parents=True, exist_ok=True)
    base.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    base.with_suffix(".md").write_text(render_markdown(result), encoding="utf-8")


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Offline quality readiness report",
        "",
        f"- Schema version: {result['schema_version']}",
        f"- Generated at: {result['generated_at']}",
        f"- Overall status: {result['overall_status']}",
        f"- Official questions: {result['summary']['official_questions']}",
        f"- Corpus regression questions: {result['summary']['corpus_regression_questions']}",
        f"- Live model calls: {result['summary']['live_model_calls']}",
        "",
        "## Checks",
        "",
    ]
    for check in result["checks"]:
        lines.append(f"- {check['id']}: {check['status']}")
    lines.extend(
        [
            "",
            "## Deferred",
            "",
            "- live_answer_quality: blocked_by_policy",
            "- live_latency_p95: blocked_by_policy",
            f"- full_corpus_source_expectations: {result['summary']['full_corpus_source_expectations']}",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", default=DEFAULT_GOLD_PATH)
    parser.add_argument("--fixtures", default=DEFAULT_FIXTURES_PATH)
    parser.add_argument("--artifact-manifest", default=DEFAULT_ARTIFACT_MANIFEST_PATH)
    parser.add_argument("--suites", default=DEFAULT_SUITES_PATH)
    parser.add_argument("--report")
    parser.add_argument("--output-base", default=DEFAULT_OUTPUT_BASE)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = evaluate_offline_quality(
        load_json(args.gold),
        load_json(args.fixtures),
        load_json(args.artifact_manifest),
        load_json(args.suites),
        Path.cwd(),
        load_json(args.report) if args.report else None,
    )
    write_outputs(result, args.output_base)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
