from __future__ import annotations

from typing import Any

ACCESS_AUDIT_ACTIONS = frozenset(
    {
        "access_denied",
        "source_viewed",
        "search",
        "document_exported",
    }
)

REQUIRED_DETAIL_FIELDS: dict[str, tuple[str, ...]] = {
    "access_denied": ("role", "status"),
    "source_viewed": ("source_span_id", "role", "status"),
    "search": ("query", "role", "status"),
    "document_exported": ("query_run_id", "format", "role", "status"),
}


def build_access_denied_details(
    *,
    role: str,
    status: str = "denied",
    source_span_id: str | None = None,
    document_id: str | None = None,
    reason: str | None = None,
    query_run_id: str | None = None,
    export_format: str | None = None,
) -> dict[str, Any]:
    details: dict[str, Any] = {"role": role, "status": status}
    if source_span_id is not None:
        details["source_span_id"] = source_span_id
    if document_id is not None:
        details["document_id"] = document_id
    if reason is not None:
        details["reason"] = reason
    if query_run_id is not None:
        details["query_run_id"] = query_run_id
    if export_format is not None:
        details["format"] = export_format
    return details


def build_source_viewed_details(
    *,
    source_span_id: str,
    role: str,
    status: str,
    document_id: str | None = None,
) -> dict[str, Any]:
    details: dict[str, Any] = {
        "source_span_id": source_span_id,
        "role": role,
        "status": status,
    }
    if document_id is not None:
        details["document_id"] = document_id
    return details


def build_search_audit_details(
    *,
    query: str,
    role: str,
    status: str,
    result_count: int | None = None,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    details: dict[str, Any] = {"query": query, "role": role, "status": status}
    if result_count is not None:
        details["result_count"] = result_count
    if filters is not None:
        details["filters"] = filters
    return details


def build_export_audit_details(
    *,
    query_run_id: str,
    export_format: str,
    role: str,
    status: str,
) -> dict[str, Any]:
    return {
        "query_run_id": query_run_id,
        "format": export_format,
        "role": role,
        "status": status,
    }


def validate_access_audit_details(action: str, details: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if action not in ACCESS_AUDIT_ACTIONS:
        errors.append(f"unsupported access audit action: {action}")
        return errors
    required = REQUIRED_DETAIL_FIELDS[action]
    for field in required:
        value = details.get(field)
        if value is None or value == "":
            errors.append(f"{action} audit details missing '{field}'")
    return errors
