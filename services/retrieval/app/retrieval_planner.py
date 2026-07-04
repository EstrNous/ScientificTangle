import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from shared.contracts import QueryIR

QueryClass = Literal[
    "semantic",
    "numeric",
    "geo",
    "temporal",
    "comparative",
    "graph_centric",
    "mixed",
]

RetrieverProfile = Literal[
    "semantic",
    "lexical",
    "table",
    "numeric",
    "geo",
    "time",
    "graph",
]

COMPARATIVE_MARKERS = (
    "лучше",
    "хуже",
    "максимум",
    "минимум",
    "больше",
    "меньше",
    "vs",
    "versus",
    "между",
    "сравнен",
    "compare",
    "compared",
    "по сравнению",
    "выше",
    "ниже",
)

GRAPH_MARKERS = (
    "связ",
    "граф",
    "claim",
    "противореч",
    "сосед",
    "цепочк",
    "отношен",
    "entity",
    "сущност",
)

TABLE_SOURCE_HINTS = {"table", "spreadsheet", "xlsx", "csv", "docx"}

ABBREVIATION_PATTERN = re.compile(r"\b[A-ZА-Я]{2,6}\b")
FORMULA_PATTERN = re.compile(r"[A-Z][a-z]?\d*|[A-Z]{2,}")


class RetrievalTraceEntry(BaseModel):
    profile: RetrieverProfile
    selected: bool
    reason: str
    filter_keys: list[str] = Field(default_factory=list)


class RetrievalPlan(BaseModel):
    query_class: QueryClass
    retriever_profiles: list[RetrieverProfile]
    filters: dict[str, Any]
    trace: list[RetrievalTraceEntry]
    degraded_reasons: list[str] = Field(default_factory=list)


def build_retrieval_plan(query_ir: QueryIR) -> RetrievalPlan:
    normalized_filters, degraded_reasons = normalize_planner_filters(query_ir)
    query_class = classify_query_class(query_ir, normalized_filters)
    trace = build_profile_trace(query_ir, normalized_filters, query_class)
    selected_profiles = [entry.profile for entry in trace if entry.selected]
    return RetrievalPlan(
        query_class=query_class,
        retriever_profiles=selected_profiles,
        filters=normalized_filters,
        trace=trace,
        degraded_reasons=degraded_reasons,
    )


def normalize_planner_filters(query_ir: QueryIR) -> tuple[dict[str, Any], list[str]]:
    filters = dict(query_ir.filters or {})
    degraded_reasons: list[str] = []

    legacy_source_types = [
        str(value)
        for value in filters.get("source_types", [])
        if value is not None and str(value).strip()
    ]
    source_type_constraints = [
        str(value)
        for value in filters.get("source_type_constraints", [])
        if value is not None and str(value).strip()
    ]
    merged_source_types = list(dict.fromkeys([*source_type_constraints, *legacy_source_types]))
    if merged_source_types:
        filters["source_type_constraints"] = merged_source_types
    if legacy_source_types:
        filters["source_types"] = legacy_source_types

    if query_ir.geo_filter is not None and query_ir.geo_filter.location_name:
        geo_constraints = [
            str(value)
            for value in filters.get("geo_constraints", [])
            if value is not None and str(value).strip()
        ]
        location_name = query_ir.geo_filter.location_name
        if location_name not in geo_constraints:
            geo_constraints.append(location_name)
        filters["geo_constraints"] = geo_constraints

    if query_ir.numeric_filter is not None:
        numeric_constraints = [
            item
            for item in filters.get("numeric_constraints", [])
            if isinstance(item, dict)
        ]
        numeric_dump = query_ir.numeric_filter.model_dump(mode="json")
        if not any(item == numeric_dump for item in numeric_constraints):
            numeric_constraints.append(numeric_dump)
        filters["numeric_constraints"] = numeric_constraints

    if query_ir.source_type_filter:
        source_types = [
            str(value)
            for value in filters.get("source_type_constraints", [])
            if value is not None and str(value).strip()
        ]
        for value in query_ir.source_type_filter:
            if value and value not in source_types:
                source_types.append(value)
        filters["source_type_constraints"] = source_types

    time_constraints = filters.get("time_constraints", {})
    if isinstance(time_constraints, dict) and time_constraints:
        if not any(
            time_constraints.get(key) is not None
            for key in ("start_year", "end_year", "relative_years", "from", "to")
        ):
            degraded_reasons.append("time_constraints_without_resolvable_interval")

    return filters, degraded_reasons


def classify_query_class(query_ir: QueryIR, filters: dict[str, Any]) -> QueryClass:
    lowered_query = query_ir.raw_query.lower()
    has_numeric = has_numeric_constraints(filters, query_ir)
    has_geo = has_geo_constraints(filters, query_ir)
    has_time = has_time_constraints(filters)
    has_graph = has_graph_signals(query_ir, lowered_query)
    has_comparative = has_comparative_markers(lowered_query)
    strict_families = sum(
        1 for present in (has_numeric, has_geo, has_time, has_graph) if present
    )

    if has_numeric and has_comparative:
        return "comparative"
    if has_numeric and not has_geo and not has_time and not has_graph and not has_comparative:
        return "numeric"
    if has_geo and has_time and (has_numeric or has_graph):
        return "mixed"
    if strict_families >= 2:
        return "mixed"
    if has_geo and not has_time and not has_numeric:
        return "geo"
    if has_time and not has_geo and not has_numeric:
        return "temporal"
    if has_graph:
        return "graph_centric"
    return "semantic"


def build_profile_trace(
    query_ir: QueryIR,
    filters: dict[str, Any],
    query_class: QueryClass,
) -> list[RetrievalTraceEntry]:
    has_numeric = has_numeric_constraints(filters, query_ir)
    has_geo = has_geo_constraints(filters, query_ir)
    has_time = has_time_constraints(filters)
    has_table_hint = has_table_source_hint(filters)
    lexical_hint = has_lexical_hint(query_ir)
    has_graph = query_class in {"graph_centric", "comparative", "mixed"} or has_graph_signals(
        query_ir,
        query_ir.raw_query.lower(),
    )

    semantic_selected = query_class != "graph_centric" or has_numeric or has_geo or has_time
    lexical_selected = lexical_hint
    table_selected = has_table_hint or query_class in {"numeric", "comparative", "mixed"}
    numeric_selected = has_numeric
    geo_selected = has_geo
    time_selected = has_time
    graph_selected = has_graph

    return [
        RetrievalTraceEntry(
            profile="semantic",
            selected=semantic_selected,
            reason="semantic_fallback" if semantic_selected else "graph_only_lookup",
            filter_keys=planner_filter_keys(filters, semantic_selected),
        ),
        RetrievalTraceEntry(
            profile="lexical",
            selected=lexical_selected,
            reason="lexical_entity_or_phrase_hint" if lexical_selected else "no_lexical_hint",
            filter_keys=["entities"] if lexical_selected else [],
        ),
        RetrievalTraceEntry(
            profile="table",
            selected=table_selected,
            reason="table_or_numeric_source_hint" if table_selected else "no_table_hint",
            filter_keys=["source_type_constraints"] if table_selected and has_table_hint else [],
        ),
        RetrievalTraceEntry(
            profile="numeric",
            selected=numeric_selected,
            reason="numeric_constraints_present" if numeric_selected else "no_numeric_constraints",
            filter_keys=["numeric_constraints"] if numeric_selected else [],
        ),
        RetrievalTraceEntry(
            profile="geo",
            selected=geo_selected,
            reason="geo_constraints_present" if geo_selected else "no_geo_constraints",
            filter_keys=["geo_constraints"] if geo_selected else [],
        ),
        RetrievalTraceEntry(
            profile="time",
            selected=time_selected,
            reason="time_constraints_present" if time_selected else "no_time_constraints",
            filter_keys=["time_constraints"] if time_selected else [],
        ),
        RetrievalTraceEntry(
            profile="graph",
            selected=graph_selected,
            reason="graph_candidate_channel" if graph_selected else "graph_not_requested",
            filter_keys=["entities"] if graph_selected else [],
        ),
    ]


def planner_filter_keys(filters: dict[str, Any], selected: bool) -> list[str]:
    if not selected:
        return []
    keys = []
    for key in (
        "numeric_constraints",
        "geo_constraints",
        "time_constraints",
        "source_type_constraints",
    ):
        if filters.get(key):
            keys.append(key)
    return keys


def has_numeric_constraints(filters: dict[str, Any], query_ir: QueryIR) -> bool:
    numeric_constraints = filters.get("numeric_constraints", [])
    return bool(numeric_constraints) or query_ir.numeric_filter is not None


def has_geo_constraints(filters: dict[str, Any], query_ir: QueryIR) -> bool:
    geo_constraints = filters.get("geo_constraints", [])
    return bool(geo_constraints) or query_ir.geo_filter is not None


def has_time_constraints(filters: dict[str, Any]) -> bool:
    time_constraints = filters.get("time_constraints", {})
    if not isinstance(time_constraints, dict):
        return False
    return bool(time_constraints)


def has_comparative_markers(lowered_query: str) -> bool:
    return any(marker in lowered_query for marker in COMPARATIVE_MARKERS)


def has_graph_signals(query_ir: QueryIR, lowered_query: str) -> bool:
    if query_ir.entities and any(marker in lowered_query for marker in GRAPH_MARKERS):
        return True
    return any(marker in lowered_query for marker in GRAPH_MARKERS)


def has_table_source_hint(filters: dict[str, Any]) -> bool:
    source_types = {
        str(value).lower()
        for value in filters.get("source_type_constraints", [])
        if value is not None
    }
    source_types.update(
        str(value).lower()
        for value in filters.get("source_types", [])
        if value is not None
    )
    return bool(source_types & TABLE_SOURCE_HINTS)


def has_lexical_hint(query_ir: QueryIR) -> bool:
    if query_ir.entities:
        return True
    tokens = [token for token in query_ir.raw_query.split() if token.strip()]
    if len(tokens) <= 4 and tokens:
        return True
    if ABBREVIATION_PATTERN.search(query_ir.raw_query):
        return True
    return bool(FORMULA_PATTERN.search(query_ir.raw_query))
