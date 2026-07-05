from collections.abc import AsyncIterator
from uuid import UUID

import httpx

from infra.postgres.orchestrator_db import QueryRunRepository
from shared.contracts import GraphSubgraph, QueryRunPayload, SearchResultPayload, SourcePayload
from shared.security import AuthenticatedPrincipal

from .service import OrchestratorService


class _UnusedIngestionRepository:
    pass


class QueryService:
    def __init__(
        self,
        client: httpx.AsyncClient,
        query_repository: QueryRunRepository | None = None,
        ingestion_url: str = "http://ingestion",
        knowledge_url: str = "http://knowledge",
        retrieval_url: str = "http://retrieval",
        model_url: str = "http://model",
        export_url: str = "http://export",
        enforce_active_dictionary: bool = False,
    ) -> None:
        self._service = OrchestratorService(
            _UnusedIngestionRepository(),
            client,
            ingestion_url,
            knowledge_url,
            retrieval_url,
            model_url,
            export_url,
            query_repository=query_repository,
            enforce_active_dictionary=enforce_active_dictionary,
        )

    async def run_query(
        self,
        principal: AuthenticatedPrincipal,
        question: str,
        filters: dict,
        request_id: str,
        limit: int,
    ) -> QueryRunPayload:
        return await self._service.run_query(principal, question, filters, request_id, limit)

    async def stream_query(
        self,
        principal: AuthenticatedPrincipal,
        question: str,
        filters: dict,
        request_id: str,
        limit: int,
    ) -> AsyncIterator[str]:
        async for chunk in self._service.stream_query(
            principal, question, filters, request_id, limit
        ):
            yield chunk

    async def get_run(self, run_id: UUID, principal: AuthenticatedPrincipal) -> QueryRunPayload:
        return await self._service.get_run(run_id, principal)

    async def get_source(
        self,
        source_span_id: str,
        principal: AuthenticatedPrincipal,
        request_id: str,
    ) -> SourcePayload:
        return await self._service.get_source(source_span_id, principal, request_id)

    async def get_subgraph(self, run_id: UUID, principal: AuthenticatedPrincipal) -> GraphSubgraph:
        return await self._service.get_subgraph(run_id, principal)

    async def search(
        self,
        principal: AuthenticatedPrincipal,
        question: str,
        filters: dict,
        limit: int,
        request_id: str,
    ) -> SearchResultPayload:
        return await self._service.search(principal, question, filters, limit, request_id)
