from unittest.mock import AsyncMock, MagicMock

import pytest
from adapters.dto import ClaimsBundleDTO, EvidenceRecordDTO, ExperimentDTO
from adapters.neo4j_adapter import Neo4jKnowledgeAdapter
from adapters.operations import subgraph_dto_to_contract, write_bundle_tx

from shared.contracts import GraphLink, GraphNode, QueryIR


@pytest.mark.asyncio
async def test_build_subgraph_by_evidence_runs_query() -> None:
    driver = MagicMock()
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    record = {
        "c": {"claim_id": "claim-1", "statement": "test"},
        "s": {"source_span_id": "span-1", "raw_text": "text"},
        "d": {"document_id": "doc-1", "title": "Doc"},
        "e": {"entity_id": "ent-1", "canonical_name": "Ni"},
        "m": None,
        "g": None,
        "o": None,
    }

    async def async_iter(_):
        class Record:
            def get(self, key, default=None):
                return record.get(key, default)

        yield Record()

    result_mock = MagicMock()
    result_mock.__aiter__ = async_iter
    session.run = AsyncMock(return_value=result_mock)
    driver.session.return_value = session

    adapter = Neo4jKnowledgeAdapter(driver)
    subgraph = await adapter.build_subgraph_by_evidence(
        ["claim-1"], [], [], ["public", "internal"]
    )
    assert "claim-1" in subgraph.claim_ids
    assert any(node.id == "claim-1" for node in subgraph.nodes)


@pytest.mark.asyncio
async def test_neighborhood_fallback_expands_entities() -> None:
    adapter = Neo4jKnowledgeAdapter(MagicMock())
    adapter.retrieve_evidence = AsyncMock(
        side_effect=[
            [],
            [EvidenceRecordDTO(claim_id="c1", statement="s", confidence=0.5, status="verified")],
        ]
    )
    adapter.resolve_aliases = AsyncMock(return_value=["ent-1"])
    adapter.expand_neighbors = AsyncMock(
        return_value=MagicMock(
            nodes=[
                MagicMock(id="ent-1", node_type="Entity"),
                MagicMock(id="ent-2", node_type="Entity"),
            ]
        )
    )
    result = await adapter.neighborhood_fallback(QueryIR(raw_query="никель", entities=["никель"]))
    assert result.used_fallback is True
    assert result.evidence


def test_subgraph_dto_to_contract() -> None:
    from adapters.dto import GraphEdgeDTO, GraphNodeDTO, GraphSubgraphDTO

    contract = subgraph_dto_to_contract(
        GraphSubgraphDTO(
            nodes=[GraphNodeDTO(id="n1", label="L", node_type="Entity", properties={})],
            edges=[GraphEdgeDTO(id="e1", source="n1", target="n2", edge_type="RELATED_TO")],
        )
    )
    assert contract.nodes == [GraphNode(id="n1", label="L", type="Entity")]
    assert contract.links == [GraphLink(source="n1", target="n2", type="RELATED_TO")]


@pytest.mark.asyncio
async def test_write_bundle_tx_writes_experiment_and_contradicts() -> None:
    tx = AsyncMock()
    bundle = ClaimsBundleDTO(
        experiments=[ExperimentDTO(experiment_id="exp-1", description="lab", performed_at="2026-01-01T00:00:00+00:00")]
    )
    written = await write_bundle_tx(tx, bundle)
    assert written == 1
    assert tx.run.await_count == 2
