from typing import Protocol

from shared.contracts import GraphSubgraph, NormalizedDocument, StorageWriteResult


class StorageAdapterNotReady(RuntimeError):
    pass


class KnowledgeStorageAdapter(Protocol):
    @property
    def is_ready(self) -> bool: ...

    async def write_extraction(
        self,
        document: NormalizedDocument,
        extraction: dict,
    ) -> StorageWriteResult: ...

    async def build_subgraph(
        self,
        claim_ids: list[str],
        entity_ids: list[str],
        source_span_ids: list[str],
        access_levels: list[str],
    ) -> GraphSubgraph: ...


class PendingKnowledgeStorageAdapter:
    is_ready = False

    async def write_extraction(
        self,
        document: NormalizedDocument,
        extraction: dict,
    ) -> StorageWriteResult:
        raise StorageAdapterNotReady("neo4j_adapter_pending")

    async def build_subgraph(
        self,
        claim_ids: list[str],
        entity_ids: list[str],
        source_span_ids: list[str],
        access_levels: list[str],
    ) -> GraphSubgraph:
        raise StorageAdapterNotReady("neo4j_adapter_pending")
