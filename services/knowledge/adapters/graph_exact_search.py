from __future__ import annotations

from typing import Any

from neo4j import AsyncDriver

from . import queries
from .dto import GraphExactFallbackState, GraphExactSearchResultDTO
from .graph_query_spec import GraphQuerySpec, GraphSearchPattern, compile_graph_query_spec
from .operations import records_to_exact_bundle


def _query_params(spec: GraphQuerySpec) -> dict[str, Any]:
    return {
        "entity_ids": spec.entity_ids,
        "entity_hints": spec.entity_hints,
        "access_levels": spec.access_levels,
        "geo_name": spec.geo_name,
        "numeric_min": spec.numeric_min,
        "numeric_max": spec.numeric_max,
        "published_after": spec.published_after,
        "published_before": spec.published_before,
        "group_a_key": spec.comparison_group_a,
        "group_b_key": spec.comparison_group_b,
        "limit": spec.limit,
    }


def _missing_data_gaps(records: list[Any]) -> list[str]:
    gaps: list[str] = []
    for record in records:
        process = record.get("e")
        material = record.get("related_entity")
        gap_type = str(record.get("gap_type") or "missing_data")
        if process is None or material is None:
            continue
        process_id = str(dict(process).get("entity_id", ""))
        material_id = str(dict(material).get("entity_id", ""))
        if process_id and material_id:
            gaps.append(f"{gap_type}:{process_id}:{material_id}")
    return list(dict.fromkeys(gaps))


def _resolve_fallback_state(
    source_span_ids: list[str],
    claim_ids: list[str],
    conflicts: list[str],
    patterns_executed: list[str],
    used_fallback: bool,
) -> GraphExactFallbackState:
    if conflicts:
        return "contradiction"
    if not claim_ids and not source_span_ids:
        return "no_evidence"
    if claim_ids and not source_span_ids:
        return "partial"
    if used_fallback and patterns_executed:
        return "partial"
    return "none"


async def run_graph_pattern(
    driver: AsyncDriver,
    pattern: GraphSearchPattern,
    spec: GraphQuerySpec,
) -> tuple[list[Any], list[str]]:
    query = queries.GRAPH_PATTERN_QUERIES[pattern]
    params = _query_params(spec)
    async with driver.session() as session:
        result = await session.run(query, **params)
        records = [record async for record in result]
    if pattern == "missing_data":
        return records, _missing_data_gaps(records)
    source_span_ids, claim_ids, measurement_ids, evidence, conflicts = records_to_exact_bundle(records)
    _ = measurement_ids
    _ = evidence
    return records, conflicts if pattern == "conflicts" else []


async def execute_graph_exact_search(
    driver: AsyncDriver,
    spec: GraphQuerySpec,
    *,
    used_fallback: bool = False,
) -> GraphExactSearchResultDTO:
    all_records: list[Any] = []
    patterns_executed: list[str] = []
    gap_descriptions: list[str] = []
    conflict_pairs: list[str] = []

    for pattern in spec.patterns:
        if pattern == "missing_data" and not spec.entity_hints and not spec.entity_ids:
            continue
        if pattern == "comparison" and (not spec.comparison_group_a or not spec.comparison_group_b):
            continue
        records, side_effects = await run_graph_pattern(driver, pattern, spec)
        if not records:
            continue
        patterns_executed.append(pattern)
        if pattern == "missing_data":
            gap_descriptions.extend(side_effects)
            continue
        all_records.extend(records)
        if pattern == "conflicts":
            conflict_pairs.extend(side_effects)

    source_span_ids, claim_ids, measurement_ids, evidence, record_conflicts = records_to_exact_bundle(all_records)
    conflicts = list(dict.fromkeys([*conflict_pairs, *record_conflicts]))
    fallback_state = _resolve_fallback_state(
        source_span_ids,
        claim_ids,
        conflicts,
        patterns_executed,
        used_fallback,
    )
    return GraphExactSearchResultDTO(
        source_span_ids=source_span_ids,
        claim_ids=claim_ids,
        measurement_ids=measurement_ids,
        evidence=evidence[: spec.limit],
        conflicts=conflicts,
        gaps=gap_descriptions,
        patterns_executed=patterns_executed,
        fallback_state=fallback_state,
        used_fallback=used_fallback,
        spec_patterns=list(spec.patterns),
    )


async def graph_exact_search_with_fallback(
    driver: AsyncDriver,
    spec: GraphQuerySpec,
    resolve_aliases: Any,
) -> GraphExactSearchResultDTO:
    if not spec.entity_ids and spec.entity_hints:
        resolved: list[str] = []
        for hint in spec.entity_hints:
            resolved.extend(await resolve_aliases(hint))
        spec = spec.model_copy(update={"entity_ids": list(dict.fromkeys(resolved))})

    primary = await execute_graph_exact_search(driver, spec)
    if primary.claim_ids or primary.source_span_ids:
        return primary

    expanded_entity_ids: list[str] = []
    for entity_id in spec.entity_ids[:3]:
        neighbor_ids = await resolve_aliases(entity_id)
        expanded_entity_ids.extend(neighbor_ids)
    expanded_entity_ids = list(dict.fromkeys([*spec.entity_ids, *expanded_entity_ids]))[:10]
    if not expanded_entity_ids:
        return primary.model_copy(update={"fallback_state": "no_evidence"})

    fallback_spec = spec.model_copy(
        update={
            "entity_ids": expanded_entity_ids,
            "patterns": ["entity_property", "entity_process_measurement"],
        }
    )
    fallback_result = await execute_graph_exact_search(driver, fallback_spec, used_fallback=True)
    if fallback_result.claim_ids or fallback_result.source_span_ids:
        return fallback_result
    return primary.model_copy(update={"fallback_state": "no_evidence", "used_fallback": True})


def build_graph_query_spec(
    query_ir: Any,
    access_levels: list[str] | None = None,
    entity_ids: list[str] | None = None,
) -> GraphQuerySpec:
    return compile_graph_query_spec(query_ir, access_levels=access_levels, entity_ids=entity_ids)
