import argparse
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx

from shared.utils.source_span import compute_source_span_id_from_parts


DEFAULT_EVAL_SERVICE_URL = "http://localhost:8000/api/query"
DEFAULT_GOLD_QUESTIONS_PATH = "eval/gold_questions.json"
DEFAULT_REPORT_BASE = "eval/reports/latest"


async def run_evaluation(
    service_url: str,
    gold_questions_path: str,
    documents_path: str | None,
    ingestion_normalize_url: str | None,
    auth_token: str | None,
    output_base: str,
) -> None:
    gold = load_gold_questions(gold_questions_path)
    results = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for question in gold:
            started_at = time.perf_counter()
            try:
                response = await client.post(
                    service_url,
                    json={"question": question["text"]},
                    headers=auth_headers(auth_token),
                )
                elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
                data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                result = evaluate_response(question, response.status_code, data, elapsed_ms)
                result["input_documents_count"] = 0
            except httpx.HTTPError as exc:
                elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
                result = evaluate_response(question, 0, {"error": str(exc)}, elapsed_ms)
                result["input_documents_count"] = 0
            results.append(result)

    report = build_report(results)
    write_reports(report, Path(output_base))
    print(json.dumps(report, ensure_ascii=False, indent=2))


def load_gold_questions(path: str) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [*data.get("questions", []), *data.get("corpus_regression_questions", [])]


async def load_eval_documents(client: httpx.AsyncClient, documents_path: str | None, ingestion_normalize_url: str | None) -> list[dict[str, Any]]:
    if not documents_path:
        return []
    data = json.loads(Path(documents_path).read_text(encoding="utf-8"))
    if "normalized_documents" in data:
        return data["normalized_documents"]
    raw_documents = data.get("documents", [])
    if not ingestion_normalize_url:
        raise ValueError("Raw eval documents require --ingestion-normalize-url")
    documents = []
    for item in raw_documents:
        response = await client.post(ingestion_normalize_url, json=item)
        response.raise_for_status()
        payload = response.json()
        documents.append(payload["document"])
    return documents


def auth_headers(auth_token: str | None) -> dict[str, str]:
    if not auth_token:
        return {}
    return {"Authorization": f"Bearer {auth_token}"}


def resolve_auth_token(auth_token: str | None, auth_token_env: str | None) -> str | None:
    if auth_token:
        return auth_token
    if auth_token_env:
        return os.getenv(auth_token_env)
    return None


def evaluate_response(question: dict[str, Any], status_code: int, data: dict[str, Any], latency_ms: float) -> dict[str, Any]:
    evidence_items = data.get("evidence_bundle", {}).get("evidence_items", [])
    query_ir = data.get("query_ir") or data.get("answer", {}).get("query_ir") or {}
    unsupported_warnings = data.get("unsupported_warnings", [])
    candidates = data.get("candidates", []) or data.get("candidate_items", [])
    return {
        "question_id": question["id"],
        "split": question.get("split", "unknown"),
        "status_code": status_code,
        "latency_ms": latency_ms,
        "citation_coverage": citation_coverage(question, evidence_items),
        "numeric_correctness": numeric_correctness(question, data),
        "query_ir_constraint_recall": query_ir_constraint_recall(question, query_ir),
        "evidence_recall_at_k": evidence_recall_at_k(question, evidence_items),
        "unsupported_claim_rate": unsupported_claim_rate(data, unsupported_warnings),
        "entity_linking_f1": entity_linking_f1(question, query_ir),
        "candidate_quality_review_rate": candidate_quality_review_rate(candidates, unsupported_warnings),
        "answer_completeness": answer_completeness(question, data),
        "geo_correctness": geo_correctness(question, data, query_ir),
        "conflict_detection_accuracy": conflict_detection_accuracy(question, data),
        "gap_precision": gap_precision(question, data),
        "query_trace_completeness": query_trace_completeness(data),
        "has_evidence": bool(evidence_items),
        "error": data.get("error"),
    }


def citation_coverage(question: dict[str, Any], evidence_items: list[dict[str, Any]]) -> float | None:
    expected_span_ids = set(question.get("expected_source_span_ids", []))
    if not expected_span_ids:
        return 1.0 if evidence_items else 0.0
    actual_span_ids = collect_source_span_ids(evidence_items)
    return len(expected_span_ids & actual_span_ids) / len(expected_span_ids)


def numeric_correctness(question: dict[str, Any], data: dict[str, Any]) -> float | None:
    expected = question.get("expected_numeric_constraints", [])
    if not expected:
        return None
    text = json.dumps(data, ensure_ascii=False).lower()
    matched = 0
    for constraint in expected:
        unit = str(constraint.get("unit", "")).lower()
        value = constraint.get("value")
        range_min = constraint.get("range_min")
        range_max = constraint.get("range_max")
        unit_ok = not unit or unit in text
        value_ok = True
        if value is not None:
            value_ok = str(value).lower() in text
        if range_min is not None and range_max is not None:
            value_ok = str(range_min).lower() in text and str(range_max).lower() in text
        if unit_ok and value_ok:
            matched += 1
    return matched / len(expected)


def query_ir_constraint_recall(question: dict[str, Any], query_ir: dict[str, Any]) -> float | None:
    expected_units = {str(item.get("unit", "")).lower() for item in question.get("expected_numeric_constraints", []) if item.get("unit")}
    expected_geo = {str(item).lower() for item in question.get("expected_geo_constraints", [])}
    expected_time = question.get("expected_time_constraints", {})
    filters = query_ir.get("filters", {})
    actual_units = {
        str(item.get("unit", "")).lower()
        for item in filters.get("numeric_constraints", [])
        if isinstance(item, dict) and item.get("unit")
    }
    actual_geo = {str(item).lower() for item in filters.get("geo_constraints", [])}
    checks = []
    if expected_units:
        checks.append(len(expected_units & actual_units) / len(expected_units))
    if expected_geo:
        checks.append(len(expected_geo & actual_geo) / len(expected_geo))
    if expected_time:
        checks.append(1.0 if all(query_ir_time_value(filters, key) == value for key, value in expected_time.items()) else 0.0)
    if not checks:
        return None
    return sum(checks) / len(checks)


def evidence_recall_at_k(question: dict[str, Any], evidence_items: list[dict[str, Any]], k: int = 10) -> float | None:
    expected_span_ids = set(question.get("expected_source_span_ids", []))
    if not expected_span_ids:
        return None
    actual_span_ids = collect_source_span_ids(evidence_items[:k])
    return len(expected_span_ids & actual_span_ids) / len(expected_span_ids)


def unsupported_claim_rate(data: dict[str, Any], unsupported_warnings: list[dict[str, Any]]) -> float:
    answer_text = data.get("answer_text") or data.get("answer", {}).get("answer_text", "")
    rough_claim_count = max(1, answer_text.count(".") + answer_text.count(";"))
    return len(unsupported_warnings) / rough_claim_count


def entity_linking_f1(question: dict[str, Any], query_ir: dict[str, Any]) -> float | None:
    expected = {str(item).lower() for item in question.get("expected_entities", [])}
    if not expected:
        return None
    actual = {str(item).lower() for item in query_ir.get("entities", [])}
    if not actual:
        return 0.0
    true_positive = len(expected & actual)
    precision = true_positive / len(actual)
    recall = true_positive / len(expected)
    if precision + recall == 0:
        return 0.0
    return (2 * precision * recall) / (precision + recall)


def candidate_quality_review_rate(candidates: list[dict[str, Any]], unsupported_warnings: list[dict[str, Any]]) -> float | None:
    if not candidates:
        return None
    review_needed = sum(1 for item in candidates if item.get("reason_codes")) + len(unsupported_warnings)
    return min(1.0, review_needed / len(candidates))


def answer_completeness(question: dict[str, Any], data: dict[str, Any]) -> float | None:
    outline = [str(item).lower() for item in question.get("answer_outline", [])]
    if not outline:
        return None
    answer_text = (data.get("answer_text") or data.get("answer", {}).get("answer_text", "")).lower()
    if not answer_text:
        return 0.0
    return sum(1 for item in outline if item in answer_text) / len(outline)


def geo_correctness(question: dict[str, Any], data: dict[str, Any], query_ir: dict[str, Any]) -> float | None:
    expected = {str(item).lower() for item in question.get("expected_geo_constraints", [])}
    if not expected:
        return None
    text = json.dumps(data, ensure_ascii=False).lower()
    filters = query_ir.get("filters", {})
    actual = {str(item).lower() for item in filters.get("geo_constraints", [])}
    actual.update(item for item in expected if item in text)
    return len(expected & actual) / len(expected)


def conflict_detection_accuracy(question: dict[str, Any], data: dict[str, Any]) -> float | None:
    expected = question.get("expected_conflicts")
    if expected is None:
        return None
    actual = bool(data.get("has_conflicts") or data.get("evidence_bundle", {}).get("has_conflicts") or data.get("conflicts"))
    return 1.0 if bool(expected) == actual else 0.0


def gap_precision(question: dict[str, Any], data: dict[str, Any]) -> float | None:
    expected = question.get("expected_gaps")
    gaps = data.get("gaps") or data.get("evidence_bundle", {}).get("gaps") or []
    if expected is None and not gaps:
        return None
    if not gaps:
        return 0.0 if expected else None
    if not expected:
        return 0.0
    expected_text = " ".join(str(item).lower() for item in expected)
    matched = sum(1 for gap in gaps if any(token in expected_text for token in str(gap).lower().split()))
    return matched / len(gaps)


def query_trace_completeness(data: dict[str, Any]) -> float:
    expected_keys = ("query_ir", "evidence_bundle", "confidence")
    return sum(1 for key in expected_keys if key in data or key in data.get("answer", {})) / len(expected_keys)


def collect_source_span_ids(evidence_items: list[dict[str, Any]]) -> set[str]:
    ids = set()
    for item in evidence_items:
        span = item.get("source_span", {})
        if span.get("id"):
            ids.add(str(span["id"]))
        metadata = span.get("metadata", {})
        if isinstance(metadata, dict) and metadata.get("source_span_id"):
            ids.add(str(metadata["source_span_id"]))
        stable_id = stable_source_span_id(span)
        if stable_id:
            ids.add(stable_id)
    return ids


def stable_source_span_id(span: dict[str, Any]) -> str | None:
    required = ("document_id", "page", "start_offset", "end_offset")
    if not all(key in span for key in required):
        return None
    return compute_source_span_id_from_parts(
        str(span["document_id"]),
        int(span["page"]),
        int(span["start_offset"]),
        int(span["end_offset"]),
        str(span.get("table_block_id") or "") or None,
    )


def query_ir_time_value(filters: dict[str, Any], key: str) -> Any:
    time_constraints = filters.get("time_constraints", {})
    if isinstance(time_constraints, dict):
        return time_constraints.get(key)
    return None


def build_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = {
        "citation_coverage": average_metric(results, "citation_coverage"),
        "numeric_correctness": average_metric(results, "numeric_correctness"),
        "query_ir_constraint_recall": average_metric(results, "query_ir_constraint_recall"),
        "evidence_recall_at_k": average_metric(results, "evidence_recall_at_k"),
        "unsupported_claim_rate": average_metric(results, "unsupported_claim_rate"),
        "entity_linking_f1": average_metric(results, "entity_linking_f1"),
        "candidate_quality_review_rate": average_metric(results, "candidate_quality_review_rate"),
        "answer_completeness": average_metric(results, "answer_completeness"),
        "geo_correctness": average_metric(results, "geo_correctness"),
        "conflict_detection_accuracy": average_metric(results, "conflict_detection_accuracy"),
        "gap_precision": average_metric(results, "gap_precision"),
        "query_trace_completeness": average_metric(results, "query_trace_completeness"),
        "latency_ms_avg": average_metric(results, "latency_ms"),
        "latency_ms_p50": percentile_metric(results, "latency_ms", 0.5),
        "latency_ms_p95": percentile_metric(results, "latency_ms", 0.95),
    }
    return {
        "total_questions": len(results),
        "answered_200": sum(1 for item in results if item["status_code"] == 200),
        "with_evidence": sum(1 for item in results if item["has_evidence"]),
        "metrics": metrics,
        "dashboard_data": build_dashboard_data(results, metrics),
        "results": results,
    }


def build_dashboard_data(results: list[dict[str, Any]], metrics: dict[str, Any]) -> dict[str, Any]:
    official = [item for item in results if item.get("question_id", "").startswith("official-")]
    blockers = [
        item["question_id"]
        for item in results
        if item["status_code"] != 200 or not item["has_evidence"] or item.get("unsupported_claim_rate", 0) > 0.25
    ]
    return {
        "official_questions_total": len(official),
        "official_questions_200": sum(1 for item in official if item["status_code"] == 200),
        "official_questions_with_evidence": sum(1 for item in official if item["has_evidence"]),
        "blocker_question_ids": blockers,
        "metric_status": {
            "citation_coverage": threshold_status(metrics.get("citation_coverage"), 0.8, higher_is_better=True),
            "numeric_correctness": threshold_status(metrics.get("numeric_correctness"), 0.9, higher_is_better=True),
            "unsupported_claim_rate": threshold_status(metrics.get("unsupported_claim_rate"), 0.1, higher_is_better=False),
            "query_ir_constraint_recall": threshold_status(metrics.get("query_ir_constraint_recall"), 0.9, higher_is_better=True),
            "latency_ms_p95": threshold_status(metrics.get("latency_ms_p95"), 5000, higher_is_better=False),
        },
        "summary_rows": [
            {
                "question_id": item["question_id"],
                "status_code": item["status_code"],
                "has_evidence": item["has_evidence"],
                "latency_ms": item["latency_ms"],
                "input_documents_count": item.get("input_documents_count", 0),
            }
            for item in results
        ],
    }


def threshold_status(value: float | None, threshold: float, higher_is_better: bool) -> str:
    if value is None:
        return "unknown"
    if higher_is_better:
        return "pass" if value >= threshold else "warn"
    return "pass" if value <= threshold else "warn"


def average_metric(results: list[dict[str, Any]], key: str) -> float | None:
    values = [item[key] for item in results if item.get(key) is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def percentile_metric(results: list[dict[str, Any]], key: str, percentile: float) -> float | None:
    values = sorted(item[key] for item in results if item.get(key) is not None)
    if not values:
        return None
    index = min(len(values) - 1, max(0, round((len(values) - 1) * percentile)))
    return round(values[index], 6)


def write_reports(report: dict[str, Any], output_base: Path) -> None:
    output_base.parent.mkdir(parents=True, exist_ok=True)
    output_base.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    output_base.with_suffix(".md").write_text(render_markdown_report(report), encoding="utf-8")


def render_markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Evaluation report",
        "",
        f"- Total questions: {report['total_questions']}",
        f"- Answered 200: {report['answered_200']}",
        f"- With evidence: {report['with_evidence']}",
        "",
        "## Metrics",
        "",
    ]
    for key, value in report["metrics"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Dashboard data", ""])
    dashboard = report["dashboard_data"]
    lines.append(f"- official_questions_total: {dashboard['official_questions_total']}")
    lines.append(f"- official_questions_200: {dashboard['official_questions_200']}")
    lines.append(f"- official_questions_with_evidence: {dashboard['official_questions_with_evidence']}")
    lines.append(f"- blocker_question_ids: {', '.join(dashboard['blocker_question_ids']) if dashboard['blocker_question_ids'] else 'none'}")
    lines.extend(["", "## Questions", ""])
    for item in report["results"]:
        lines.append(f"- {item['question_id']}: status={item['status_code']}, evidence={item['has_evidence']}, latency_ms={item['latency_ms']}")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--service-url", default=DEFAULT_EVAL_SERVICE_URL)
    parser.add_argument("--gold", default=DEFAULT_GOLD_QUESTIONS_PATH)
    parser.add_argument("--documents")
    parser.add_argument("--ingestion-normalize-url")
    parser.add_argument("--auth-token")
    parser.add_argument("--auth-token-env", default="EVAL_AUTH_TOKEN")
    parser.add_argument("--output-base", default=DEFAULT_REPORT_BASE)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(
        run_evaluation(
            args.service_url,
            args.gold,
            args.documents,
            args.ingestion_normalize_url,
            resolve_auth_token(args.auth_token, args.auth_token_env),
            args.output_base,
        )
    )
