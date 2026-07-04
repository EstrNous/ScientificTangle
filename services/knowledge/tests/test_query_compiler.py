from adapters.query_compiler import compile_query_ir

from shared.contracts import QueryIR


def test_compile_query_ir_includes_entity_resolution() -> None:
    query_ir = QueryIR(raw_query="nickel recovery", entities=["nickel"], limit=10)
    plan = compile_query_ir(query_ir, access_levels=["public"])
    operations = [step.operation for step in plan.steps]
    assert "resolve_entities" in operations
    assert "rank_claims" in operations
    assert plan.access_levels == ["public"]
    assert plan.limit == 10
