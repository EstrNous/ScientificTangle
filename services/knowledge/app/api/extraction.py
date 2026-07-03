import httpx
from fastapi import APIRouter, Request

from shared.contracts import (
    KnowledgeIngestionRequest,
    KnowledgeIngestionResponse,
    StorageWriteResult,
)

from ..core.config import settings

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
    records_count = len(extraction.get("confirmed", [])) + len(
        extraction.get("candidates", [])
    )
    warning = "neo4j_adapter_pending"
    return KnowledgeIngestionResponse(
        document_id=request.document.id,
        extraction=extraction,
        graph_write=StorageWriteResult(
            backend="neo4j",
            document_ids=[request.document.id],
            records_count=records_count,
            warnings=[warning],
        ),
        warnings=[warning],
    )
