import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from adapters.dto import GraphEdgeDTO, GraphNodeDTO, GraphSubgraphDTO
from adapters.neo4j_adapter import Neo4jKnowledgeAdapter
from adapters.neo4j_storage_adapter import Neo4jStorageAdapter

from shared.contracts import GraphLink, GraphNode


@pytest.fixture
def knowledge_adapter() -> Neo4jKnowledgeAdapter:
    driver = MagicMock()
    adapter = Neo4jKnowledgeAdapter(driver)
    adapter.build_subgraph_by_evidence = AsyncMock(
        return_value=GraphSubgraphDTO(
            nodes=[GraphNodeDTO(id="claim-1", label="stmt", node_type="Claim", properties={})],
            edges=[GraphEdgeDTO(id="e1", source="claim-1", target="span-1", edge_type="DESCRIBED_IN")],
            claim_ids=["claim-1"],
            source_span_ids=["span-1"],
        )
    )
    return adapter


@pytest.mark.asyncio
async def test_storage_adapter_build_subgraph_maps_contract(knowledge_adapter: Neo4jKnowledgeAdapter) -> None:
    storage = Neo4jStorageAdapter(knowledge_adapter)
    result = await storage.build_subgraph(
        ["claim-1"], ["entity-1"], ["span-1"], ["public", "internal"]
    )
    assert result.nodes == [GraphNode(id="claim-1", label="stmt", type="Claim")]
    assert result.links == [GraphLink(source="claim-1", target="span-1", type="DESCRIBED_IN")]
    knowledge_adapter.build_subgraph_by_evidence.assert_awaited_once_with(
        claim_ids=["claim-1"],
        entity_ids=["entity-1"],
        source_span_ids=["span-1"],
        access_levels=["public", "internal"],
    )


def test_subgraph_endpoint_uses_storage_adapter() -> None:
    from app.api.graph import SubgraphRequest, build_subgraph

    class ReadyAdapter:
        is_ready = True

        async def build_subgraph(self, claim_ids, entity_ids, source_span_ids, access_levels):
            assert claim_ids == ["claim-1"]
            return __import__("shared.contracts", fromlist=["GraphSubgraph"]).GraphSubgraph(
                nodes=[GraphNode(id="entity-1", label="Ni", type="Material")],
                links=[],
            )

    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(storage_adapter=ReadyAdapter())))
    result = asyncio.run(
        build_subgraph(
            SubgraphRequest(
                claim_ids=["claim-1"],
                entity_ids=["entity-1"],
                source_span_ids=["span-1"],
                access_levels=["public"],
            ),
            request,
        )
    )
    assert result.nodes[0].id == "entity-1"
