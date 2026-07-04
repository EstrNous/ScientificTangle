from unittest.mock import AsyncMock, MagicMock

import pytest
from adapters.graph_exact_search import execute_graph_exact_search, graph_exact_search_with_fallback
from adapters.graph_query_spec import GraphQuerySpec
from adapters.neo4j_adapter import Neo4jKnowledgeAdapter
from adapters.operations import records_to_exact_bundle

from shared.contracts import QueryIR


def test_records_to_exact_bundle_collects_ids() -> None:
    record = {
        "c": {"claim_id": "claim-1", "statement": "test", "confidence": 0.9, "status": "verified"},
        "s": {"source_span_id": "span-1", "document_id": "doc-1", "page_number": 1, "raw_text": "text", "char_start": 0, "char_end": 4},
        "d": {"document_id": "doc-1", "access_level": "public"},
        "m": {"measurement_id": "meas-1", "value": 90.0, "unit": "%"},
    }
    source_span_ids, claim_ids, measurement_ids, evidence, conflicts = records_to_exact_bundle([record])
    assert source_span_ids == ["span-1"]
    assert claim_ids == ["claim-1"]
    assert measurement_ids == ["meas-1"]
    assert len(evidence) == 1
    assert conflicts == []


@pytest.mark.asyncio
async def test_execute_graph_exact_search_marks_no_evidence() -> None:
    driver = MagicMock()
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    async def empty_iter(_):
        if False:
            yield None

    result_mock = MagicMock()
    result_mock.__aiter__ = empty_iter
    session.run = AsyncMock(return_value=result_mock)
    driver.session.return_value = session

    spec = GraphQuerySpec(patterns=["entity_property"], entity_hints=["nickel"])
    result = await execute_graph_exact_search(driver, spec)
    assert result.fallback_state == "no_evidence"
    assert result.claim_ids == []
    assert result.source_span_ids == []


@pytest.mark.asyncio
async def test_graph_exact_search_with_fallback_expands_entities() -> None:
    from adapters.dto import GraphExactSearchResultDTO

    empty = GraphExactSearchResultDTO(fallback_state="no_evidence", spec_patterns=["entity_property"])
    filled = GraphExactSearchResultDTO(
        claim_ids=["claim-2"],
        source_span_ids=["span-2"],
        fallback_state="partial",
        used_fallback=True,
        patterns_executed=["entity_property"],
    )
    driver = MagicMock()
    resolve_aliases = AsyncMock(side_effect=[["ent-1"], ["ent-2"]])
    spec = GraphQuerySpec(patterns=["entity_property"], entity_hints=["nickel"])

    with pytest.MonkeyPatch.context() as monkeypatch:
        calls: list[bool] = []

        async def fake_execute(_driver, _spec, *, used_fallback=False):
            calls.append(used_fallback)
            return filled if used_fallback else empty

        monkeypatch.setattr("adapters.graph_exact_search.execute_graph_exact_search", fake_execute)
        result = await graph_exact_search_with_fallback(driver, spec, resolve_aliases=resolve_aliases)

    assert calls == [False, True]
    assert result.used_fallback is True
    assert result.claim_ids == ["claim-2"]
    assert result.source_span_ids == ["span-2"]


@pytest.mark.asyncio
async def test_adapter_graph_exact_search_delegates() -> None:
    adapter = Neo4jKnowledgeAdapter(MagicMock())
    adapter.graph_exact_search = AsyncMock(return_value=MagicMock(claim_ids=["c1"], source_span_ids=["s1"]))
    result = await adapter.graph_exact_search(QueryIR(raw_query="nickel"))
    assert result.claim_ids == ["c1"]
