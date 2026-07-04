from adapters.graph_query_spec import compile_graph_query_spec, select_graph_patterns

from shared.contracts import GeoContext, QueryIR, Quantity


def test_select_graph_patterns_for_geo_query() -> None:
    query_ir = QueryIR(
        raw_query="recovery in chile",
        entities=["copper"],
        geo_filter=GeoContext(location_name="Chile"),
    )
    patterns = select_graph_patterns(query_ir)
    assert "geo_indicator" in patterns
    assert "entity_property" in patterns


def test_select_graph_patterns_for_comparative_query() -> None:
    query_ir = QueryIR(
        raw_query="compare nickel vs copper recovery",
        entities=["nickel", "copper"],
        intent="comparison",
    )
    patterns = select_graph_patterns(query_ir)
    assert "comparison" in patterns


def test_compile_graph_query_spec_preserves_filters() -> None:
    query_ir = QueryIR(
        raw_query="nickel leaching",
        entities=["nickel"],
        numeric_filter=Quantity(value=90.0, unit="%", range_min=80.0, range_max=95.0),
        filters={"time_constraints": {"from": "2020-01-01", "to": "2024-12-31"}},
        limit=15,
    )
    spec = compile_graph_query_spec(query_ir, access_levels=["public"], entity_ids=["ent-ni"])
    assert spec.entity_ids == ["ent-ni"]
    assert spec.entity_hints == ["nickel"]
    assert spec.numeric_min == 80.0
    assert spec.numeric_max == 95.0
    assert spec.published_after == "2020-01-01"
    assert spec.published_before == "2024-12-31"
    assert spec.limit == 15
    assert "entity_process_measurement" in spec.patterns
