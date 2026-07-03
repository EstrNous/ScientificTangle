from shared.contracts import GraphPayload, SearchResultsPayload


class GraphService:
    async def get_graph(self) -> GraphPayload:
        return GraphPayload()

    async def search(self) -> SearchResultsPayload:
        return SearchResultsPayload()
