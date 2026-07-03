from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from shared.contracts import GraphSubgraph

from ..storage import KnowledgeStorageAdapter, StorageAdapterNotReady

router = APIRouter(prefix="/v1/graph", tags=["knowledge-graph"])


class SubgraphRequest(BaseModel):
    claim_ids: list[str] = Field(default_factory=list)
    entity_ids: list[str] = Field(default_factory=list)
    source_span_ids: list[str] = Field(default_factory=list)


@router.post("/subgraph", response_model=GraphSubgraph)
async def build_subgraph(
    payload: SubgraphRequest,
    request: Request,
) -> GraphSubgraph:
    adapter: KnowledgeStorageAdapter = request.app.state.storage_adapter
    try:
        return await adapter.build_subgraph(
            payload.claim_ids,
            payload.entity_ids,
            payload.source_span_ids,
        )
    except StorageAdapterNotReady as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
