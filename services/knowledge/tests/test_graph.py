import asyncio
from types import SimpleNamespace

from app.api.graph import SubgraphRequest, build_subgraph

from shared.contracts import GraphNode, GraphSubgraph


class FakeStorageAdapter:
    is_ready = True

    async def build_subgraph(self, claim_ids, entity_ids, source_span_ids, access_levels):
        assert claim_ids == ["claim-1"]
        assert entity_ids == ["entity-1"]
        assert source_span_ids == ["span-1"]
        assert access_levels == ["public", "internal"]
        return GraphSubgraph(
            nodes=[GraphNode(id="entity-1", label="Никель", type="Material")],
            links=[],
        )


def test_subgraph_is_built_from_evidence_ids() -> None:
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(storage_adapter=FakeStorageAdapter()))
    )

    result = asyncio.run(
        build_subgraph(
            SubgraphRequest(
                claim_ids=["claim-1"],
                entity_ids=["entity-1"],
                source_span_ids=["span-1"],
                access_levels=["public", "internal"],
            ),
            request,
        )
    )

    assert [node.id for node in result.nodes] == ["entity-1"]
