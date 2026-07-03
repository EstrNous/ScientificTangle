from typing import Any

import httpx
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from shared.contracts import EvidenceBundle, EvidenceItem, NormalizedDocument, QueryIR

from ..core.config import settings

router = APIRouter(prefix="/v1", tags=["retrieval"])


class RetrievalQueryRequest(BaseModel):
    query: str = Field(min_length=1)
    documents: list[NormalizedDocument] = Field(default_factory=list)
    access_roles: list[str] = Field(default_factory=list)
    limit: int = Field(default=20, ge=1, le=100)


class RetrievalQueryResponse(BaseModel):
    query_ir: QueryIR
    evidence_bundle: EvidenceBundle
    warnings: list[str] = Field(default_factory=list)


@router.post("/query", response_model=RetrievalQueryResponse)
async def run_query(request: RetrievalQueryRequest, app_request: Request) -> RetrievalQueryResponse:
    client: httpx.AsyncClient = app_request.app.state.http_client
    query_ir_response = await client.post(
        f"{settings.model_url.rstrip('/')}/v1/query-ir",
        json={"raw_query": request.query, "limit": request.limit},
    )
    query_ir_response.raise_for_status()
    query_ir = QueryIR.model_validate(query_ir_response.json()["query_ir"])
    evidence_items = collect_evidence_items(query_ir, request.documents, request.access_roles)
    rerank_response = await client.post(
        f"{settings.model_url.rstrip('/')}/v1/rerank",
        json={
            "query_ir": query_ir.model_dump(mode="json"),
            "evidence_items": [item.model_dump(mode="json") for item in evidence_items],
            "limit": request.limit,
        },
    )
    rerank_response.raise_for_status()
    scored = rerank_response.json().get("scored_items", [])
    ranked_items = [
        EvidenceItem.model_validate(item["evidence_item"])
        for item in scored
        if isinstance(item, dict) and item.get("evidence_item")
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
        warnings=query_ir_response.json().get("warnings", []),
    )


def collect_evidence_items(query_ir: QueryIR, documents: list[NormalizedDocument], access_roles: list[str]) -> list[EvidenceItem]:
    query_tokens = normalized_tokens(query_ir.raw_query)
    items = []
    for document in documents:
        if not access_allowed(document, access_roles):
            continue
        for span in document.source_spans:
            text_tokens = normalized_tokens(span.text)
            if not (query_tokens & text_tokens) and not constraints_match(query_ir.filters, span.text):
                continue
            items.append(
                EvidenceItem(
                    source_span=span,
                    relevance_score=evidence_score(query_tokens, text_tokens, query_ir.filters, span.text),
                    extraction_method="semantic",
                )
            )
    return items


def access_allowed(document: NormalizedDocument, access_roles: list[str]) -> bool:
    policy = document.access_policy
    if policy.level == "public" or not policy.allowed_roles:
        return True
    return bool(set(policy.allowed_roles) & set(access_roles))


def constraints_match(filters: dict[str, Any], text: str) -> bool:
    lowered = text.lower()
    geo = [str(value).lower() for value in filters.get("geo_constraints", [])]
    if geo and any(value in lowered for value in geo):
        return True
    numeric = filters.get("numeric_constraints", [])
    return bool(numeric and any(char.isdigit() for char in text))


def evidence_score(query_tokens: set[str], text_tokens: set[str], filters: dict[str, Any], text: str) -> float:
    overlap = len(query_tokens & text_tokens) / max(len(query_tokens), 1)
    constraint_bonus = 0.25 if constraints_match(filters, text) else 0.0
    return min(1.0, round(overlap + constraint_bonus, 6))


def normalized_tokens(text: str) -> set[str]:
    return {token.strip(".,;:()[]{}").lower() for token in text.split() if len(token.strip(".,;:()[]{}")) >= 2}
