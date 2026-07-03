from fastapi import APIRouter, HTTPException, Request

from shared.contracts import (
    RetrievalIndexRequest,
    RetrievalIndexResponse,
)

from ..storage import RetrievalStorageAdapter, StorageAdapterNotReady

router = APIRouter(prefix="/v1/documents", tags=["retrieval-indexing"])


@router.post("/index", response_model=RetrievalIndexResponse)
async def index_documents(
    request: RetrievalIndexRequest,
    app_request: Request,
) -> RetrievalIndexResponse:
    adapter: RetrievalStorageAdapter = app_request.app.state.storage_adapter
    try:
        result = await adapter.index(request)
    except StorageAdapterNotReady as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return RetrievalIndexResponse(vector_write=result, warnings=result.warnings)
