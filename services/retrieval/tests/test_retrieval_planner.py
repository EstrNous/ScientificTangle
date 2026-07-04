from app.retrieval_planner import build_retrieval_plan

from shared.contracts import GeoContext, QueryIR, Quantity


def selected_profiles(plan) -> list[str]:
    return [entry.profile for entry in plan.trace if entry.selected]


def test_semantic_query_selects_semantic_fallback() -> None:
    query_ir = QueryIR(
        raw_query="Какие методы обессоливания воды применяются в промышленности?",
        intent="find_methods",
    )

    plan = build_retrieval_plan(query_ir)

    assert plan.query_class == "semantic"
    assert "semantic" in plan.retriever_profiles
    assert "numeric" not in plan.retriever_profiles
    assert plan.degraded_reasons == []


def test_numeric_query_selects_numeric_and_table_profiles() -> None:
    query_ir = QueryIR(
        raw_query="Какая извлекаемость никеля составляет 82 процентов по отчётам",
        filters={
            "numeric_constraints": [{"value": 82, "unit": "%", "operator": "eq"}],
        },
    )

    plan = build_retrieval_plan(query_ir)

    assert plan.query_class == "numeric"
    assert {"semantic", "table", "numeric"} <= set(plan.retriever_profiles)
    numeric_trace = next(item for item in plan.trace if item.profile == "numeric")
    assert numeric_trace.reason == "numeric_constraints_present"
    assert numeric_trace.filter_keys == ["numeric_constraints"]


def test_geo_query_selects_geo_profile() -> None:
    query_ir = QueryIR(
        raw_query="Практика добычи в России",
        filters={"geo_constraints": ["Россия"]},
        geo_filter=GeoContext(location_name="Россия"),
    )

    plan = build_retrieval_plan(query_ir)

    assert plan.query_class == "geo"
    assert "geo" in plan.retriever_profiles
    assert plan.filters["geo_constraints"] == ["Россия"]


def test_temporal_query_selects_time_profile() -> None:
    query_ir = QueryIR(
        raw_query="Публикации за 2021-2024",
        filters={"time_constraints": {"start_year": 2021, "end_year": 2024}},
    )

    plan = build_retrieval_plan(query_ir)

    assert plan.query_class == "temporal"
    assert "time" in plan.retriever_profiles


def test_comparative_query_with_numeric_constraints() -> None:
    query_ir = QueryIR(
        raw_query="Сравнение извлекаемости никеля: Россия vs зарубежная практика, 82 %",
        filters={
            "numeric_constraints": [{"value": 82, "unit": "%", "operator": "eq"}],
            "geo_constraints": ["Россия"],
        },
    )

    plan = build_retrieval_plan(query_ir)

    assert plan.query_class == "comparative"
    assert "graph" in plan.retriever_profiles
    assert "numeric" in plan.retriever_profiles


def test_mixed_query_when_multiple_constraint_families_present() -> None:
    query_ir = QueryIR(
        raw_query="Никель в России за 2021-2024, извлекаемость 82 %",
        filters={
            "numeric_constraints": [{"value": 82, "unit": "%", "operator": "eq"}],
            "geo_constraints": ["Россия"],
            "time_constraints": {"start_year": 2021, "end_year": 2024},
        },
    )

    plan = build_retrieval_plan(query_ir)

    assert plan.query_class == "mixed"
    assert {"semantic", "table", "numeric", "geo", "time"} <= set(plan.retriever_profiles)


def test_graph_centric_query_selects_graph_channel_without_cypher() -> None:
    query_ir = QueryIR(
        raw_query="Какие claims связаны с сущностью никель и есть ли противоречия?",
        entities=["никель"],
    )

    plan = build_retrieval_plan(query_ir)

    assert plan.query_class == "graph_centric"
    graph_trace = next(item for item in plan.trace if item.profile == "graph")
    assert graph_trace.selected is True
    assert graph_trace.reason == "graph_candidate_channel"


def test_normalizes_source_type_constraints_from_legacy_source_types() -> None:
    query_ir = QueryIR(
        raw_query="Табличные данные по публикациям",
        filters={
            "source_types": ["publication"],
            "source_type_constraints": ["table"],
        },
    )

    plan = build_retrieval_plan(query_ir)

    assert plan.filters["source_type_constraints"] == ["table", "publication"]
    assert plan.filters["source_types"] == ["publication"]
    assert "table" in plan.retriever_profiles


def test_numeric_filter_field_is_merged_into_planner_filters() -> None:
    quantity = Quantity(value=1.2, unit="m/s", operator="eq")
    query_ir = QueryIR(
        raw_query="Скорость потока 1.2 м/с",
        numeric_filter=quantity,
    )

    plan = build_retrieval_plan(query_ir)

    assert plan.query_class == "numeric"
    assert plan.filters["numeric_constraints"][0]["unit"] == "m/s"


def test_lexical_profile_for_short_entity_query() -> None:
    query_ir = QueryIR(
        raw_query="Ni recovery",
        entities=["Ni"],
    )

    plan = build_retrieval_plan(query_ir)

    assert "lexical" in plan.retriever_profiles
    lexical_trace = next(item for item in plan.trace if item.profile == "lexical")
    assert lexical_trace.reason == "lexical_entity_or_phrase_hint"


def test_time_constraints_without_interval_adds_degraded_reason() -> None:
    query_ir = QueryIR(
        raw_query="Публикации за последние годы",
        filters={"time_constraints": {"label": "recent"}},
    )

    plan = build_retrieval_plan(query_ir)

    assert "time_constraints_without_resolvable_interval" in plan.degraded_reasons
    assert "time" in plan.retriever_profiles


def test_plan_trace_is_deterministic_for_same_query_ir() -> None:
    query_ir = QueryIR(
        raw_query="Россия 2023 никель 82 %",
        filters={
            "numeric_constraints": [{"value": 82, "unit": "%"}],
            "geo_constraints": ["Россия"],
            "time_constraints": {"start_year": 2023, "end_year": 2023},
        },
    )

    first = build_retrieval_plan(query_ir)
    second = build_retrieval_plan(query_ir)

    assert first.model_dump() == second.model_dump()
