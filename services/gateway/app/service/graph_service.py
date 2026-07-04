import httpx

from shared.contracts import GraphPayload, SearchResultsPayload

from ..core.config import settings
from .analytics_service import GraphService as KnowledgeGraphService


class GraphService:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._delegate = KnowledgeGraphService(client or httpx.AsyncClient(timeout=30.0))

    async def get_graph(self) -> GraphPayload:
        return await self._delegate.get_graph()

    async def get_catalog(self) -> SearchResultsPayload:
        return await self._delegate.get_catalog()
