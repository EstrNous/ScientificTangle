from __future__ import annotations

from shared.contracts import GraphSubgraph, NormalizedDocument, StorageWriteResult

from .neo4j_adapter import Neo4jKnowledgeAdapter
from .operations import subgraph_dto_to_contract


class Neo4jStorageAdapter:
    is_ready = True

    def __init__(self, knowledge_adapter: Neo4jKnowledgeAdapter) -> None:
        self._knowledge = knowledge_adapter

    async def write_extraction(
        self,
        document: NormalizedDocument,
        extraction: dict,
    ) -> StorageWriteResult:
        _ = document, extraction
        return StorageWriteResult(mode="adapter_pending", backend="neo4j")

    async def build_subgraph(
        self,
        claim_ids: list[str],
        entity_ids: list[str],
        source_span_ids: list[str],
    ) -> GraphSubgraph:
        subgraph = await self._knowledge.build_subgraph_by_evidence(
            claim_ids=claim_ids,
            entity_ids=entity_ids,
            source_span_ids=source_span_ids,
        )
        return subgraph_dto_to_contract(subgraph)
