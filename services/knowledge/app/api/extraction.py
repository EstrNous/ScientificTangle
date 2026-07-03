from typing import Any

import httpx
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from shared.contracts import NormalizedDocument

from ..core.config import settings

router = APIRouter(prefix="/v1/documents", tags=["knowledge"])


class KnowledgeExtractionRequest(BaseModel):
    document: NormalizedDocument


class KnowledgeExtractionResponse(BaseModel):
    document_id: str
    extraction: dict[str, Any]
    graph_write: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


@router.post("/extract", response_model=KnowledgeExtractionResponse)
async def extract_document(request: KnowledgeExtractionRequest, app_request: Request) -> KnowledgeExtractionResponse:
    client: httpx.AsyncClient = app_request.app.state.http_client
    warnings = []
    response = await client.post(
        f"{settings.model_url.rstrip('/')}/v1/extraction/structured",
        json={"document": request.document.model_dump(mode="json")},
    )
    response.raise_for_status()
    extraction = response.json()
    if not settings.neo4j_url:
        warnings.append("Neo4j URL is not configured")
    return KnowledgeExtractionResponse(
        document_id=request.document.id,
        extraction=extraction,
        graph_write={
            "mode": "adapter_pending",
            "confirmed_count": len(extraction.get("confirmed", [])),
            "candidate_count": len(extraction.get("candidates", [])),
        },
        warnings=warnings,
    )
