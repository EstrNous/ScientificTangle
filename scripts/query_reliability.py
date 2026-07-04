from datetime import UTC, datetime
from typing import Any


def build_reliability_report(scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    passed = sum(1 for item in scenarios if item.get("status") == "pass")
    failed = sum(1 for item in scenarios if item.get("status") == "fail")
    categories = sorted({str(item.get("category") or "unknown") for item in scenarios})
    return {
        "schema_version": "ml_reliability_report.v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "total": len(scenarios),
        "passed": passed,
        "failed": failed,
        "ok": failed == 0,
        "categories": categories,
        "scenarios": scenarios,
    }


def classify_query_outcome(
    *,
    status_code: int,
    pipeline_mode: str | None,
    warnings: list[str],
    terminal_phase: str | None = None,
) -> str:
    if status_code >= 500:
        return "failed"
    if terminal_phase == "error":
        return "stream_error"
    if any("fallback" in warning for warning in warnings):
        return "degraded_fallback"
    if terminal_phase == "degraded" or any(
        marker in warning
        for warning in warnings
        for marker in ("insufficient", "unsupported", "conflict")
    ):
        return "degraded"
    if pipeline_mode == "legacy":
        return "legacy_ok"
    if pipeline_mode == "top1_scientific":
        return "scientific_ok"
    return "ok"
