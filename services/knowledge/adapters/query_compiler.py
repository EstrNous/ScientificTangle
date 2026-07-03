from __future__ import annotations

from shared.contracts import QueryIR

from .dto import QueryPlan, QueryPlanStep

DEFAULT_ACCESS_LEVELS = ["public", "internal"]


def compile_query_ir(query_ir: QueryIR, access_levels: list[str] | None = None) -> QueryPlan:
    levels = access_levels or list(DEFAULT_ACCESS_LEVELS)
    steps: list[QueryPlanStep] = []
    if query_ir.entities:
        steps.append(QueryPlanStep(operation="resolve_entities", parameters={"mentions": query_ir.entities}))
    if query_ir.geo_filter:
        steps.append(
            QueryPlanStep(
                operation="geo_filter",
                parameters={"location_name": query_ir.geo_filter.location_name},
            )
        )
    if query_ir.numeric_filter:
        steps.append(
            QueryPlanStep(
                operation="numeric_filter",
                parameters=query_ir.numeric_filter.model_dump(mode="json"),
            )
        )
    if query_ir.source_type_filter:
        steps.append(
            QueryPlanStep(
                operation="source_type_filter",
                parameters={"source_types": query_ir.source_type_filter},
            )
        )
    time_constraints = query_ir.filters.get("time_constraints", {})
    if isinstance(time_constraints, dict) and time_constraints:
        steps.append(QueryPlanStep(operation="time_filter", parameters=time_constraints))
    steps.append(QueryPlanStep(operation="traverse_claims", parameters={"intent": query_ir.intent}))
    steps.append(QueryPlanStep(operation="rank_claims", parameters={"limit": query_ir.limit}))
    return QueryPlan(
        steps=steps,
        access_levels=levels,
        entity_hints=list(query_ir.entities),
        limit=query_ir.limit,
    )
