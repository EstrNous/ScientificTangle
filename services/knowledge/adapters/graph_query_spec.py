from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from shared.contracts import QueryIR

from .query_compiler import DEFAULT_ACCESS_LEVELS

GraphSearchPattern = Literal[
    "entity_property",
    "entity_process_measurement",
    "geo_indicator",
    "period_observation",
    "comparison",
    "conflicts",
    "missing_data",
]

PROCESS_HINTS = {"process", "процесс", "leaching", "выщелачивание", "flotation", "флотация"}
MATERIAL_HINTS = {"material", "substance", "материал", "вещество", "nickel", "никель", "cu", "медь"}
COMPARATIVE_HINTS = {"compare", "comparison", "сравн", "versus", "vs", "против"}
CONFLICT_HINTS = {"conflict", "contradict", "противореч", "расхожден"}
MISSING_HINTS = {"missing", "gap", "отсутств", "пробел", "нет данных"}


class GraphQuerySpec(BaseModel):
    patterns: list[GraphSearchPattern] = Field(default_factory=list)
    entity_ids: list[str] = Field(default_factory=list)
    entity_hints: list[str] = Field(default_factory=list)
    access_levels: list[str] = Field(default_factory=lambda: list(DEFAULT_ACCESS_LEVELS))
    geo_name: str | None = None
    numeric_min: float | None = None
    numeric_max: float | None = None
    published_after: str | None = None
    published_before: str | None = None
    comparison_group_a: str | None = None
    comparison_group_b: str | None = None
    domain_profile: str = "mining-metallurgy"
    limit: int = 20


def _lowered_tokens(values: list[str]) -> set[str]:
    return {value.strip().lower() for value in values if value.strip()}


def _query_tokens(query_ir: QueryIR) -> set[str]:
    tokens = set(_lowered_tokens(query_ir.entities))
    for chunk in query_ir.raw_query.lower().replace(",", " ").split():
        if chunk:
            tokens.add(chunk)
    intent = query_ir.intent.strip().lower()
    if intent:
        tokens.add(intent)
        tokens.update(intent.split())
    return tokens


def _has_hint(tokens: set[str], hints: set[str]) -> bool:
    return any(hint in token or token in hint for token in tokens for hint in hints)


def _time_constraints(query_ir: QueryIR) -> dict[str, str]:
    raw = query_ir.filters.get("time_constraints", {}) if isinstance(query_ir.filters, dict) else {}
    return raw if isinstance(raw, dict) else {}


def _comparison_groups(query_ir: QueryIR) -> tuple[str | None, str | None]:
    filters = query_ir.filters if isinstance(query_ir.filters, dict) else {}
    group_a = filters.get("comparison_group_a") or filters.get("group_a")
    group_b = filters.get("comparison_group_b") or filters.get("group_b")
    if group_a and group_b:
        return str(group_a), str(group_b)
    entities = [entity for entity in query_ir.entities if entity.strip()]
    if len(entities) >= 2:
        return entities[0], entities[1]
    return None, None


def select_graph_patterns(query_ir: QueryIR) -> list[GraphSearchPattern]:
    tokens = _query_tokens(query_ir)
    patterns: list[GraphSearchPattern] = []
    time_constraints = _time_constraints(query_ir)
    group_a, group_b = _comparison_groups(query_ir)

    if query_ir.geo_filter and query_ir.geo_filter.location_name:
        patterns.append("geo_indicator")
    if time_constraints.get("from") or time_constraints.get("to"):
        patterns.append("period_observation")
    if group_a and group_b and (_has_hint(tokens, COMPARATIVE_HINTS) or len(query_ir.entities) >= 2):
        patterns.append("comparison")
    if query_ir.entities and (
        _has_hint(tokens, PROCESS_HINTS) or _has_hint(tokens, MATERIAL_HINTS) or query_ir.numeric_filter
    ):
        patterns.append("entity_process_measurement")
    if query_ir.entities:
        patterns.append("entity_property")
    if query_ir.entities and (_has_hint(tokens, CONFLICT_HINTS) or query_ir.numeric_filter):
        patterns.append("conflicts")
    if _has_hint(tokens, MISSING_HINTS) or _has_hint(tokens, PROCESS_HINTS):
        patterns.append("missing_data")

    if not patterns:
        if query_ir.geo_filter:
            patterns.append("geo_indicator")
        elif time_constraints:
            patterns.append("period_observation")
        else:
            patterns.append("entity_property")

    return list(dict.fromkeys(patterns))


def compile_graph_query_spec(
    query_ir: QueryIR,
    access_levels: list[str] | None = None,
    entity_ids: list[str] | None = None,
) -> GraphQuerySpec:
    levels = access_levels or list(DEFAULT_ACCESS_LEVELS)
    time_constraints = _time_constraints(query_ir)
    numeric = query_ir.numeric_filter
    group_a, group_b = _comparison_groups(query_ir)
    resolved_ids = list(dict.fromkeys(entity_ids or []))
    hints = list(dict.fromkeys(query_ir.entities))
    return GraphQuerySpec(
        patterns=select_graph_patterns(query_ir),
        entity_ids=resolved_ids,
        entity_hints=hints,
        access_levels=levels,
        geo_name=query_ir.geo_filter.location_name if query_ir.geo_filter else None,
        numeric_min=numeric.range_min if numeric else None,
        numeric_max=numeric.range_max if numeric else None,
        published_after=str(time_constraints.get("from")) if time_constraints.get("from") else None,
        published_before=str(time_constraints.get("to")) if time_constraints.get("to") else None,
        comparison_group_a=group_a,
        comparison_group_b=group_b,
        domain_profile=str(query_ir.filters.get("domain_profile", "mining-metallurgy"))
        if isinstance(query_ir.filters, dict)
        else "mining-metallurgy",
        limit=query_ir.limit,
    )
