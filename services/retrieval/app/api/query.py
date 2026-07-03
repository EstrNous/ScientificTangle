from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from shared.contracts import (
    EvidenceBundle,
    EvidenceItem,
    QueryIR,
    SearchResultPayload,
    SourcePayload,
)

from ..core.config import settings
from ..storage import RetrievalStorageAdapter, StorageAdapterNotReady, access_allowed

router = APIRouter(prefix="/v1", tags=["retrieval"])


class RetrievalQueryRequest(BaseModel):
    question: str = Field(min_length=1)
    filters: dict[str, Any] = Field(default_factory=dict)
    access_roles: list[str] = Field(default_factory=list)
    limit: int = Field(default=20, ge=1, le=100)


class RetrievalQueryResponse(BaseModel):
    query_ir: QueryIR
    evidence_bundle: EvidenceBundle
    retrieval_trace: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class RetrievalSearchRequest(BaseModel):
    question: str = ""
    filters: dict[str, Any] = Field(default_factory=dict)
    access_roles: list[str] = Field(default_factory=list)
    limit: int = Field(default=20, ge=1, le=100)


class SourceResolveRequest(BaseModel):
    access_roles: list[str] = Field(default_factory=list)


@router.post("/query", response_model=RetrievalQueryResponse)
async def run_query(
    request: RetrievalQueryRequest,
    app_request: Request,
) -> RetrievalQueryResponse:
    client: httpx.AsyncClient = app_request.app.state.http_client
    adapter: RetrievalStorageAdapter = app_request.app.state.storage_adapter
    query_ir_response = await client.post(
        f"{settings.model_url.rstrip('/')}/v1/query-ir",
        json={"raw_query": request.question, "limit": request.limit},
    )
    query_ir_response.raise_for_status()
    query_ir = QueryIR.model_validate(query_ir_response.json()["query_ir"])
    query_ir.filters = {**query_ir.filters, **request.filters}
    query_ir.limit = request.limit
    try:
        results = await adapter.search(
            request.question,
            query_ir.filters,
            request.access_roles,
            request.limit,
        )
    except StorageAdapterNotReady as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    allowed = [
        item
        for item in results.items
        if access_allowed(item.source.access_policy, request.access_roles)
    ]
    evidence_items = [
        EvidenceItem(
            source_span=item.source.source_span,
            relevance_score=item.relevance_score,
            claim_ids=item.claim_ids,
            entity_ids=item.entity_ids,
            extraction_method="semantic",
        )
        for item in allowed
    ]
    rerank_response = await client.post(
        f"{settings.model_url.rstrip('/')}/v1/rerank",
        json={
            "query_ir": query_ir.model_dump(mode="json"),
            "evidence_items": [item.model_dump(mode="json") for item in evidence_items],
            "limit": request.limit,
        },
    )
    rerank_response.raise_for_status()
    allowed_ids = {item.source_span.id for item in evidence_items}
    ranked_items = [
        EvidenceItem.model_validate(item["evidence_item"])
        for item in rerank_response.json().get("scored_items", [])
        if isinstance(item, dict)
        and item.get("evidence_item")
        and item["evidence_item"].get("source_span", {}).get("id") in allowed_ids
    ]
    evidence_bundle = EvidenceBundle(
        query_ir=query_ir,
        evidence_items=ranked_items,
        total_found=len(ranked_items),
        has_gaps=not ranked_items,
        gaps=[] if ranked_items else ["missing_evidence"],
    )
    return RetrievalQueryResponse(
        query_ir=query_ir,
        evidence_bundle=evidence_bundle,
        retrieval_trace={
            "storage": "qdrant",
            "retrieved": len(results.items),
            "accessible": len(evidence_items),
            "reranked": len(ranked_items),
        },
        warnings=[*query_ir_response.json().get("warnings", []), *results.warnings],
    )


@router.post("/search", response_model=SearchResultPayload)
async def search(
    request: RetrievalSearchRequest,
    app_request: Request,
) -> SearchResultPayload:
    adapter: RetrievalStorageAdapter = app_request.app.state.storage_adapter
    try:
        result = await adapter.search(
            request.question,
            request.filters,
            request.access_roles,
            request.limit,
        )
    except StorageAdapterNotReady as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    items = [
        item
        for item in result.items
        if access_allowed(item.source.access_policy, request.access_roles)
    ][: request.limit]
    return SearchResultPayload(
        items=items,
        total_found=len(items),
        warnings=result.warnings,
    )


@router.post("/sources/{source_span_id}/resolve", response_model=SourcePayload)
async def resolve_source(
    source_span_id: str,
    request: SourceResolveRequest,
    app_request: Request,
) -> SourcePayload:
    adapter: RetrievalStorageAdapter = app_request.app.state.storage_adapter
    try:
        source = await adapter.get_source(source_span_id, request.access_roles)
    except StorageAdapterNotReady as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if source is None or not access_allowed(source.access_policy, request.access_roles):
        raise HTTPException(status_code=404, detail="source_not_found")
    return source
