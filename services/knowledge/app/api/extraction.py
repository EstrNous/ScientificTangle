import httpx
from fastapi import APIRouter, HTTPException, Request

from shared.contracts import (
    KnowledgeIngestionRequest,
    KnowledgeIngestionResponse,
)

from ..core.config import settings
from ..storage import KnowledgeStorageAdapter, StorageAdapterNotReady

router = APIRouter(prefix="/v1/documents", tags=["knowledge"])


@router.post("/extract", response_model=KnowledgeIngestionResponse)
async def extract_document(
    request: KnowledgeIngestionRequest,
    app_request: Request,
) -> KnowledgeIngestionResponse:
    client: httpx.AsyncClient = app_request.app.state.http_client
    response = await client.post(
        f"{settings.model_url.rstrip('/')}/v1/extraction/structured",
        json={"document": request.document.model_dump(mode="json")},
    )
    response.raise_for_status()
    extraction = response.json()
    adapter: KnowledgeStorageAdapter = app_request.app.state.storage_adapter
    try:
        graph_write = await adapter.write_extraction(request.document, extraction)
    except StorageAdapterNotReady as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return KnowledgeIngestionResponse(
        document_id=request.document.id,
        extraction=extraction,
        graph_write=graph_write,
        warnings=graph_write.warnings,
    )
