import httpx

from shared.contracts import GraphPayload, SearchResultsPayload

from .analytics_service import GraphService as KnowledgeGraphService


class GraphService:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._delegate = KnowledgeGraphService(client)

    async def get_graph(self) -> GraphPayload:
        return await self._delegate.get_graph()

    async def get_catalog(self) -> SearchResultsPayload:
        return await self._delegate.get_catalog()
