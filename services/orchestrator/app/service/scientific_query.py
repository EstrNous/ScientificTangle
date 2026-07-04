import re
from typing import Any

from shared.contracts import EvidenceBundle, EvidenceItem, QueryIR, SourceSpan, UserRole

NUMBER_PATTERN = re.compile(r"[-+]?\d+(?:[,.]\d+)?")


def scientific_query_enabled(settings_flag: bool, filters: dict[str, Any]) -> bool:
    if filters.get("top1_scientific_query") is True:
        return True
    if filters.get("top1_scientific_query") is False:
        return False
    return settings_flag


def access_levels_for_role(role: UserRole) -> list[str]:
    if role == UserRole.ADMIN:
        return ["public", "internal", "restricted"]
    return ["public", "internal"]


def planner_selects_graph(retrieval_trace: dict[str, Any]) -> bool:
    planner = retrieval_trace.get("planner")
    if not isinstance(planner, dict):
        return False
    trace = planner.get("trace")
    if not isinstance(trace, list):
        return False
    for item in trace:
        if not isinstance(item, dict):
            continue
        if item.get("profile") == "graph" and item.get("selected") is True:
            return True
    return False


def planner_selects_table(retrieval_trace: dict[str, Any]) -> bool:
    planner = retrieval_trace.get("planner")
    if not isinstance(planner, dict):
        return False
    trace = planner.get("trace")
    if not isinstance(trace, list):
        return False
    for item in trace:
        if not isinstance(item, dict):
            continue
        if item.get("profile") == "table" and item.get("selected") is True:
            return True
    return False


def source_span_from_graph_record(record: dict[str, Any]) -> SourceSpan | None:
    raw_span = record.get("source_span")
    if not isinstance(raw_span, dict):
        return None
    source_type = raw_span.get("source_type", "text")
    if source_type not in {"text", "table", "figure", "caption"}:
        source_type = "text"
    return SourceSpan(
        id=str(raw_span.get("source_span_id") or raw_span.get("id") or ""),
        document_id=str(raw_span.get("document_id") or record.get("document_id") or ""),
        page=int(raw_span.get("page_number") or raw_span.get("page") or 1),
        start_offset=int(raw_span.get("char_start") or raw_span.get("start_offset") or 0),
        end_offset=int(raw_span.get("char_end") or raw_span.get("end_offset") or 0),
        text=str(raw_span.get("raw_text") or raw_span.get("text") or record.get("statement") or ""),
        table_block_id=raw_span.get("table_block_id"),
        source_type=source_type,
    )


def merge_graph_exact_evidence(
    evidence_bundle: EvidenceBundle,
    graph_result: dict[str, Any],
) -> tuple[EvidenceBundle, dict[str, Any]]:
    existing_ids = {item.source_span.id for item in evidence_bundle.evidence_items}
    merged_items = list(evidence_bundle.evidence_items)
    added = 0
    for record in graph_result.get("evidence", []):
        if not isinstance(record, dict):
            continue
        span = source_span_from_graph_record(record)
        if span is None or not span.id or span.id in existing_ids:
            continue
        existing_ids.add(span.id)
        merged_items.append(
            EvidenceItem(
                source_span=span,
                relevance_score=max(float(record.get("confidence") or 0.0), 0.55),
                claim_ids=[str(record["claim_id"])] if record.get("claim_id") else [],
                entity_ids=[],
                extraction_method="exact",
            )
        )
        added += 1
    conflicts = [
        str(value)
        for value in graph_result.get("conflicts", [])
        if value
    ]
    gaps = [
        str(value)
        for value in graph_result.get("gaps", [])
        if value
    ]
    bundle_conflicts = list(dict.fromkeys([*evidence_bundle.conflicts, *conflicts]))
    bundle_gaps = list(dict.fromkeys([*evidence_bundle.gaps, *gaps]))
    fallback_state = str(graph_result.get("fallback_state") or "none")
    has_conflicts = bool(bundle_conflicts) or fallback_state == "contradiction"
    updated_bundle = evidence_bundle.model_copy(
        update={
            "evidence_items": merged_items,
            "total_found": len(merged_items),
            "has_gaps": evidence_bundle.has_gaps or bool(bundle_gaps) or fallback_state in {"no_evidence", "partial"},
            "has_conflicts": evidence_bundle.has_conflicts or has_conflicts,
            "gaps": bundle_gaps,
            "conflicts": bundle_conflicts,
        }
    )
    trace = {
        "fallback_state": fallback_state,
        "used_fallback": bool(graph_result.get("used_fallback")),
        "patterns_executed": list(graph_result.get("patterns_executed") or []),
        "added_evidence_items": added,
        "claim_ids": list(graph_result.get("claim_ids") or []),
        "source_span_ids": list(graph_result.get("source_span_ids") or []),
    }
    return updated_bundle, trace


def apply_table_extraction_method(evidence_bundle: EvidenceBundle) -> EvidenceBundle:
    items = []
    for item in evidence_bundle.evidence_items:
        if item.source_span.source_type == "table" and item.extraction_method == "semantic":
            items.append(item.model_copy(update={"extraction_method": "table"}))
        else:
            items.append(item)
    return evidence_bundle.model_copy(update={"evidence_items": items})


def build_verification_artifacts(evidence_bundle: EvidenceBundle) -> list[dict[str, Any]]:
    artifacts = []
    for item in evidence_bundle.evidence_items:
        artifacts.append(
            {
                "id": item.source_span.id,
                "kind": "claim",
                "value": item.source_span.text,
                "confidence": max(item.relevance_score, 0.1),
                "status": "confirmed",
                "source_span_ids": [item.source_span.id],
                "source_spans": [item.source_span.model_dump(mode="json")],
                "reason_codes": [],
                "metadata": {
                    "claim_ids": item.claim_ids,
                    "entity_ids": item.entity_ids,
                    "extraction_method": item.extraction_method,
                },
            }
        )
    return artifacts


def local_verification_reason_codes(query_ir: QueryIR, text: str) -> list[str]:
    lowered = text.lower()
    filters = query_ir.filters
    reason_codes: list[str] = []
    numeric_constraints = filters.get("numeric_constraints", [])
    if numeric_constraints and not extract_numbers(text):
        reason_codes.append("unit_mismatch")
    geo_constraints = [str(value).lower() for value in filters.get("geo_constraints", [])]
    if geo_constraints and not any(value in lowered for value in geo_constraints):
        reason_codes.append("geo_mismatch")
    time_constraints = filters.get("time_constraints")
    if isinstance(time_constraints, dict) and time_constraints and not re.search(r"\b(?:19|20)\d{2}\b", text):
        reason_codes.append("outside_time_range")
    return reason_codes


def extract_numbers(text: str) -> list[float]:
    values = []
    for match in NUMBER_PATTERN.finditer(text):
        try:
            values.append(float(match.group(0).replace(",", ".")))
        except ValueError:
            continue
    return values


def apply_conflict_signals(
    artifacts: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    conflict_ids: set[str] = set()
    for signal in conflicts:
        if not isinstance(signal, dict):
            continue
        for artifact_id in signal.get("artifact_ids", []):
            conflict_ids.add(str(artifact_id))
    updated = []
    for artifact in artifacts:
        reason_codes = list(artifact.get("reason_codes", []))
        if artifact["id"] in conflict_ids:
            reason_codes.append("conflicting_values")
        updated.append({**artifact, "reason_codes": list(dict.fromkeys(reason_codes))})
    return updated


def partition_verified_evidence(
    evidence_bundle: EvidenceBundle,
    artifacts: list[dict[str, Any]],
) -> tuple[EvidenceBundle, list[dict[str, Any]]]:
    if not artifacts:
        return evidence_bundle, []
    verified_ids = {
        artifact["id"]
        for artifact in artifacts
        if artifact.get("status") == "confirmed" and not artifact.get("reason_codes")
    }
    candidate_items = [
        artifact
        for artifact in artifacts
        if artifact.get("reason_codes") or artifact.get("status") != "confirmed"
    ]
    verified_items = [
        item for item in evidence_bundle.evidence_items if item.source_span.id in verified_ids
    ]
    updated_bundle = evidence_bundle.model_copy(
        update={
            "evidence_items": verified_items,
            "total_found": len(verified_items),
            "has_gaps": evidence_bundle.has_gaps or len(verified_items) < len(evidence_bundle.evidence_items),
        }
    )
    return updated_bundle, candidate_items


def graph_record_candidates(graph_result: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = []
    for record in graph_result.get("evidence", []):
        if not isinstance(record, dict):
            continue
        status = str(record.get("status") or "confirmed")
        if status == "confirmed":
            continue
        statement = str(record.get("statement") or "")
        if not statement:
            continue
        span = source_span_from_graph_record(record)
        source_span_ids = [span.id] if span and span.id else []
        candidates.append(
            {
                "id": str(record.get("claim_id") or f"graph-candidate-{len(candidates) + 1}"),
                "kind": "claim",
                "value": statement,
                "confidence": float(record.get("confidence") or 0.0),
                "status": "candidate",
                "source_span_ids": source_span_ids,
                "source_spans": [span.model_dump(mode="json")] if span else [],
                "reason_codes": ["unsupported_claim"] if status != "candidate" else ["schema_candidate"],
                "metadata": {"origin": "graph_exact"},
            }
        )
    return candidates


def merge_candidate_items(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            key = str(item.get("id") or item.get("value"))
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged
