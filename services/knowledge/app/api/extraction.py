import httpx
from fastapi import APIRouter, Request

from adapters.mapper import artifacts_to_bundle
from adapters.neo4j_adapter import Neo4jKnowledgeAdapter
from shared.contracts import KnowledgeIngestionRequest, KnowledgeIngestionResponse, StorageWriteResult
from shared.utils.request_id import generate_request_id

from ..core.config import settings

router = APIRouter(prefix="/v1/documents", tags=["knowledge"])


@router.post("/extract", response_model=KnowledgeIngestionResponse)
async def extract_document(
    request: KnowledgeIngestionRequest,
    app_request: Request,
) -> KnowledgeIngestionResponse:
    request_id = getattr(app_request.state, "request_id", None) or generate_request_id()
    client: httpx.AsyncClient = app_request.app.state.http_client
    response = await client.post(
        f"{settings.model_url.rstrip('/')}/v1/extraction/structured",
        json={"document": request.document.model_dump(mode="json")},
    )
    response.raise_for_status()
    extraction = response.json()
    confirmed = extraction.get("confirmed", [])
    candidates = extraction.get("candidates", [])
    records_count = len(confirmed) + len(candidates)
    confirmed_count = len(confirmed)
    warnings: list[str] = []
    adapter: Neo4jKnowledgeAdapter | None = getattr(app_request.app.state, "neo4j_adapter", None)
    mode: str = "adapter_pending"
    if adapter is not None:
        bundle = artifacts_to_bundle(request.document, extraction)
        try:
            written = await adapter.write_bundle(bundle, request_id=request_id)
            if written:
                mode = "live"
            else:
                warnings.append("neo4j_write_empty")
        except Exception as exc:
            warnings.append(f"neo4j_write_failed:{exc}")
    else:
        warnings.append("neo4j_adapter_pending")
    return KnowledgeIngestionResponse(
        document_id=request.document.id,
        extraction=extraction,
        graph_write=StorageWriteResult(
            backend="neo4j",
            mode=mode,  # type: ignore[arg-type]
            document_ids=[request.document.id],
            records_count=records_count,
            confirmed_count=confirmed_count,
            warnings=warnings,
        ),
        warnings=warnings,
    )
