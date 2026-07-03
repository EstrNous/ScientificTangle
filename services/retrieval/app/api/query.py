import hashlib
import re
from typing import Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from shared.contracts import AccessPolicy, EvidenceBundle, EvidenceItem, NormalizedDocument, QueryIR, SourceSpan
from shared.utils.source_span import compute_source_span_id as source_span_id

from ..core.config import settings

router = APIRouter(prefix="/v1", tags=["retrieval"])

COLLECTION_NAME = "st_evidence_v1"
VECTOR_SIZE = 256
SEARCH_PREFETCH_MULTIPLIER = 5
TOKEN_PATTERN = re.compile(r"[\w%/.-]+", re.UNICODE)
NUMBER_PATTERN = re.compile(r"[-+]?\d+(?:[,.]\d+)?")
UNIT_PATTERN = re.compile(r"%|мг/л|mg/l|мг/дм3|мг/дм³|м/с|m/s|кг/т|kg/t", re.IGNORECASE)


class RetrievalQueryRequest(BaseModel):
    query: str = Field(min_length=1)
    documents: list[NormalizedDocument] = Field(default_factory=list)
    access_roles: list[str] = Field(default_factory=list)
    limit: int = Field(default=20, ge=1, le=100)


class RetrievalQueryResponse(BaseModel):
    query_ir: QueryIR
    evidence_bundle: EvidenceBundle
    warnings: list[str] = Field(default_factory=list)


class IndexDocumentsRequest(BaseModel):
    documents: list[NormalizedDocument] = Field(min_length=1)
    claim_ids: list[str] = Field(default_factory=list)
    graph_entity_ids: list[str] = Field(default_factory=list)


class IndexDocumentsResponse(BaseModel):
    collection: str
    documents_count: int
    points_count: int
    warnings: list[str] = Field(default_factory=list)


class BootstrapIndexResponse(BaseModel):
    collection: str
    created: bool
    indexes: list[str]
    warnings: list[str] = Field(default_factory=list)


class ResetIndexResponse(BaseModel):
    collection: str
    deleted: bool
    bootstrapped: BootstrapIndexResponse


@router.post("/index/bootstrap", response_model=BootstrapIndexResponse)
async def bootstrap_index(app_request: Request) -> BootstrapIndexResponse:
    client: httpx.AsyncClient = app_request.app.state.http_client
    return await ensure_collection(client)


@router.post("/index/reset", response_model=ResetIndexResponse)
async def reset_index(app_request: Request) -> ResetIndexResponse:
    client: httpx.AsyncClient = app_request.app.state.http_client
    deleted = True
    try:
        response = await client.delete(qdrant_url(f"/collections/{COLLECTION_NAME}"))
        if response.status_code not in (200, 404):
            response.raise_for_status()
    except httpx.HTTPStatusError:
        raise
    except httpx.HTTPError:
        deleted = False
    bootstrapped = await ensure_collection(client)
    return ResetIndexResponse(collection=COLLECTION_NAME, deleted=deleted, bootstrapped=bootstrapped)


@router.post("/documents/index", response_model=IndexDocumentsResponse)
async def index_documents(request: IndexDocumentsRequest, app_request: Request) -> IndexDocumentsResponse:
    client: httpx.AsyncClient = app_request.app.state.http_client
    bootstrap = await ensure_collection(client)
    points = build_points(request.documents, request.claim_ids, request.graph_entity_ids)
    warnings = [*bootstrap.warnings]
    if not points:
        return IndexDocumentsResponse(collection=COLLECTION_NAME, documents_count=len(request.documents), points_count=0, warnings=warnings)
    vectors_response = await build_embeddings(client, [point["payload"]["text"] for point in points], "document")
    for point, vector in zip(points, vectors_response["vectors"], strict=True):
        point["vector"] = vector
    warnings.extend(vectors_response["warnings"])
    response = await client.put(
        qdrant_url(f"/collections/{COLLECTION_NAME}/points"),
        params={"wait": "true"},
        json={"points": points},
    )
    response.raise_for_status()
    return IndexDocumentsResponse(
        collection=COLLECTION_NAME,
        documents_count=len(request.documents),
        points_count=len(points),
        warnings=warnings,
    )


@router.post("/query", response_model=RetrievalQueryResponse)
async def run_query(request: RetrievalQueryRequest, app_request: Request) -> RetrievalQueryResponse:
    client: httpx.AsyncClient = app_request.app.state.http_client
    query_ir_response = await client.post(
        f"{settings.model_url.rstrip('/')}/v1/query-ir",
        json={"raw_query": request.query, "limit": request.limit},
    )
    query_ir_response.raise_for_status()
    query_ir_payload = query_ir_response.json()
    query_ir = QueryIR.model_validate(query_ir_payload["query_ir"])
    warnings = [*query_ir_payload.get("warnings", [])]
    if request.documents:
        evidence_items = collect_evidence_items(query_ir, request.documents, request.access_roles)
    else:
        evidence_items, qdrant_warnings = await collect_qdrant_evidence_items(client, query_ir, request.access_roles, request.limit)
        warnings.extend(qdrant_warnings)
    ranked_items, rerank_warnings = await rerank_items(client, query_ir, evidence_items, request.limit)
    warnings.extend(rerank_warnings)
    if evidence_items and not ranked_items:
        ranked_items = sorted(evidence_items, key=lambda item: item.relevance_score, reverse=True)[: request.limit]
    evidence_bundle = EvidenceBundle(
        query_ir=query_ir,
        evidence_items=ranked_items,
        total_found=len(ranked_items),
        has_gaps=not ranked_items,
        gaps=[] if ranked_items else ["missing_evidence"],
    )
    return RetrievalQueryResponse(query_ir=query_ir, evidence_bundle=evidence_bundle, warnings=warnings)


async def ensure_collection(client: httpx.AsyncClient) -> BootstrapIndexResponse:
    created = False
    warnings: list[str] = []
    response = await client.get(qdrant_url(f"/collections/{COLLECTION_NAME}"))
    if response.status_code == 404:
        create_response = await client.put(
            qdrant_url(f"/collections/{COLLECTION_NAME}"),
            json={"vectors": {"size": VECTOR_SIZE, "distance": "Cosine"}},
        )
        create_response.raise_for_status()
        created = True
    else:
        response.raise_for_status()
    indexed_fields = []
    for field_name, field_schema in payload_indexes().items():
        index_response = await client.put(
            qdrant_url(f"/collections/{COLLECTION_NAME}/index"),
            json={"field_name": field_name, "field_schema": field_schema},
        )
        if index_response.status_code in (200, 409) or "already exists" in index_response.text.lower():
            indexed_fields.append(field_name)
        else:
            warnings.append(f"Failed to create Qdrant payload index {field_name}: {index_response.text}")
    return BootstrapIndexResponse(collection=COLLECTION_NAME, created=created, indexes=indexed_fields, warnings=warnings)


def payload_indexes() -> dict[str, str]:
    return {
        "item_type": "keyword",
        "document_id": "keyword",
        "source_span_id": "keyword",
        "source_type": "keyword",
        "access_level": "keyword",
        "allowed_roles": "keyword",
        "table_block_id": "keyword",
        "units": "keyword",
        "geo_bucket": "keyword",
        "geo_country": "keyword",
        "claim_ids": "keyword",
        "graph_entity_ids": "keyword",
        "numeric_min": "float",
        "numeric_max": "float",
    }


def build_points(documents: list[NormalizedDocument], claim_ids: list[str], graph_entity_ids: list[str]) -> list[dict[str, Any]]:
    points = []
    for document in documents:
        for span in document.source_spans:
            span_id = source_span_id(span)
            payload = build_payload(document, span, span_id, claim_ids, graph_entity_ids)
            points.append({"id": point_id(span_id), "payload": payload})
    return points


def build_payload(
    document: NormalizedDocument,
    span: SourceSpan,
    span_id: str,
    claim_ids: list[str],
    graph_entity_ids: list[str],
) -> dict[str, Any]:
    numeric_values = extract_numbers(span.text)
    units = extract_units(span.text)
    geo_bucket, geo_country = extract_geo(span.text)
    return {
        "schema_version": "qdrant_evidence.v1",
        "item_type": "table_row" if span.source_type == "table" else "source_span",
        "text": span.text,
        "lexical_tokens": sorted(normalized_tokens(span.text)),
        "document_id": span.document_id,
        "document_title": document.title,
        "source_span_id": span_id,
        "page": span.page,
        "start_offset": span.start_offset,
        "end_offset": span.end_offset,
        "table_block_id": span.table_block_id or "",
        "source_type": span.source_type,
        "document_source_type": document.source_type,
        "access_level": document.access_policy.level,
        "allowed_roles": document.access_policy.allowed_roles,
        "numeric_values": numeric_values,
        "numeric_min": min(numeric_values) if numeric_values else None,
        "numeric_max": max(numeric_values) if numeric_values else None,
        "units": units,
        "geo_bucket": geo_bucket,
        "geo_country": geo_country,
        "claim_ids": claim_ids,
        "graph_entity_ids": graph_entity_ids,
        "document_metadata": document.metadata,
    }


async def collect_qdrant_evidence_items(
    client: httpx.AsyncClient,
    query_ir: QueryIR,
    access_roles: list[str],
    limit: int,
) -> tuple[list[EvidenceItem], list[str]]:
    warnings: list[str] = []
    try:
        await ensure_collection(client)
        embeddings = await build_embeddings(client, [query_ir.raw_query], "query")
        warnings.extend(embeddings["warnings"])
        response = await client.post(
            qdrant_url(f"/collections/{COLLECTION_NAME}/points/search"),
            json={
                "vector": embeddings["vectors"][0],
                "limit": max(limit * SEARCH_PREFETCH_MULTIPLIER, limit),
                "with_payload": True,
                "with_vector": False,
            },
        )
        response.raise_for_status()
    except httpx.HTTPError as error:
        return [], [f"Qdrant retrieval failed: {error}"]
    results = response.json().get("result", [])
    items = []
    query_tokens = normalized_tokens(query_ir.raw_query)
    for result in results:
        payload = result.get("payload", {})
        if not payload_allowed(payload, access_roles):
            continue
        text = str(payload.get("text", ""))
        if not retrieval_match(query_tokens, query_ir.filters, text, payload):
            continue
        span = payload_to_span(payload)
        score = evidence_score(query_tokens, normalized_tokens(text), query_ir.filters, text)
        qdrant_score = float(result.get("score") or 0.0)
        items.append(
            EvidenceItem(
                source_span=span,
                relevance_score=min(1.0, round(max(score, qdrant_score), 6)),
                claim_ids=[str(item) for item in payload.get("claim_ids", [])],
                extraction_method="table" if payload.get("item_type") == "table_row" else "semantic",
            )
        )
        if len(items) >= limit:
            break
    if not items:
        fallback_items, fallback_warnings = await scroll_qdrant_evidence_items(
            client,
            query_ir,
            access_roles,
            limit,
        )
        warnings.extend(fallback_warnings)
        return fallback_items, warnings
    return items, warnings


async def scroll_qdrant_evidence_items(
    client: httpx.AsyncClient,
    query_ir: QueryIR,
    access_roles: list[str],
    limit: int,
) -> tuple[list[EvidenceItem], list[str]]:
    warnings: list[str] = []
    try:
        response = await client.post(
            qdrant_url(f"/collections/{COLLECTION_NAME}/points/scroll"),
            json={"limit": max(limit * 10, 50), "with_payload": True, "with_vector": False},
        )
        response.raise_for_status()
    except httpx.HTTPError as error:
        return [], [f"Qdrant lexical fallback failed: {error}"]
    query_tokens = normalized_tokens(query_ir.raw_query)
    items = []
    points = response.json().get("result", {}).get("points", [])
    for point in points:
        payload = point.get("payload", {})
        if not payload_allowed(payload, access_roles):
            continue
        text = str(payload.get("text", ""))
        if not retrieval_match(query_tokens, query_ir.filters, text, payload):
            continue
        items.append(
            EvidenceItem(
                source_span=payload_to_span(payload),
                relevance_score=evidence_score(query_tokens, normalized_tokens(text), query_ir.filters, text),
                claim_ids=[str(item) for item in payload.get("claim_ids", [])],
                extraction_method="table" if payload.get("item_type") == "table_row" else "semantic",
            )
        )
    items.sort(key=lambda item: item.relevance_score, reverse=True)
    return items[:limit], warnings


async def build_embeddings(client: httpx.AsyncClient, texts: list[str], input_type: str) -> dict[str, Any]:
    response = await client.post(
        f"{settings.model_url.rstrip('/')}/v1/embeddings",
        json={"texts": texts, "dimensions": VECTOR_SIZE, "input_type": input_type},
    )
    response.raise_for_status()
    payload = response.json()
    vectors = [item["vector"] for item in payload.get("embeddings", [])]
    if len(vectors) != len(texts):
        raise httpx.HTTPError("Model embeddings response size mismatch")
    return {"vectors": vectors, "warnings": payload.get("warnings", [])}


async def rerank_items(client: httpx.AsyncClient, query_ir: QueryIR, evidence_items: list[EvidenceItem], limit: int) -> tuple[list[EvidenceItem], list[str]]:
    response = await client.post(
        f"{settings.model_url.rstrip('/')}/v1/rerank",
        json={
            "query_ir": query_ir.model_dump(mode="json"),
            "evidence_items": [item.model_dump(mode="json") for item in evidence_items],
            "limit": limit,
        },
    )
    response.raise_for_status()
    payload = response.json()
    ranked_items = [
        EvidenceItem.model_validate(item["evidence_item"])
        for item in payload.get("scored_items", [])
        if isinstance(item, dict) and item.get("evidence_item")
    ]
    return ranked_items, payload.get("warnings", [])


def collect_evidence_items(query_ir: QueryIR, documents: list[NormalizedDocument], access_roles: list[str]) -> list[EvidenceItem]:
    query_tokens = normalized_tokens(query_ir.raw_query)
    items = []
    for document in documents:
        if not access_allowed(document.access_policy, access_roles):
            continue
        for span in document.source_spans:
            text_tokens = normalized_tokens(span.text)
            if not retrieval_match(query_tokens, query_ir.filters, span.text, {}):
                continue
            items.append(
                EvidenceItem(
                    source_span=span,
                    relevance_score=evidence_score(query_tokens, text_tokens, query_ir.filters, span.text),
                    extraction_method="semantic",
                )
            )
    return items


def access_allowed(policy: AccessPolicy, access_roles: list[str]) -> bool:
    if "admin" in access_roles:
        return True
    if policy.level == "public" or not policy.allowed_roles:
        return True
    return bool(set(policy.allowed_roles) & set(access_roles))


def payload_allowed(payload: dict[str, Any], access_roles: list[str]) -> bool:
    if "admin" in access_roles:
        return True
    if payload.get("access_level") == "public":
        return True
    allowed_roles = {str(role) for role in payload.get("allowed_roles", [])}
    return not allowed_roles or bool(allowed_roles & set(access_roles))


def retrieval_match(query_tokens: set[str], filters: dict[str, Any], text: str, payload: dict[str, Any]) -> bool:
    text_tokens = normalized_tokens(text)
    if query_tokens & text_tokens:
        return True
    if constraints_match(filters, text):
        return True
    units = {str(unit).lower() for unit in payload.get("units", [])}
    for constraint in filters.get("numeric_constraints", []):
        if isinstance(constraint, dict) and str(constraint.get("unit", "")).lower() in units:
            return True
    geo_constraints = {str(value).lower() for value in filters.get("geo_constraints", [])}
    payload_geo = {str(payload.get("geo_bucket", "")).lower(), str(payload.get("geo_country", "")).lower()}
    return bool(geo_constraints & payload_geo)


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
    return {token.strip(".,;:()[]{}").lower() for token in TOKEN_PATTERN.findall(text) if len(token.strip(".,;:()[]{}")) >= 2}


def extract_numbers(text: str) -> list[float]:
    values = []
    for match in NUMBER_PATTERN.finditer(text):
        try:
            values.append(float(match.group(0).replace(",", ".")))
        except ValueError:
            continue
    return values


def extract_units(text: str) -> list[str]:
    return sorted({normalize_unit(match.group(0)) for match in UNIT_PATTERN.finditer(text)})


def normalize_unit(unit: str) -> str:
    lowered = unit.lower()
    aliases = {"мг/л": "mg/l", "мг/дм3": "mg/dm3", "мг/дм³": "mg/dm3", "м/с": "m/s", "кг/т": "kg/t"}
    return aliases.get(lowered, lowered)


def extract_geo(text: str) -> tuple[str, str]:
    lowered = text.lower()
    if any(token in lowered for token in ("россия", "норильск", "кольск", "отечествен")):
        return "domestic", "Россия"
    if any(token in lowered for token in ("зарубеж", "колумб", "канада", "австрал", "миров")):
        return "foreign", "зарубежная практика"
    return "unknown", ""


def payload_to_span(payload: dict[str, Any]) -> SourceSpan:
    return SourceSpan(
        document_id=str(payload["document_id"]),
        page=int(payload.get("page") or 1),
        start_offset=int(payload.get("start_offset") or 0),
        end_offset=int(payload.get("end_offset") or len(str(payload.get("text", "")))),
        text=str(payload.get("text", "")),
        table_block_id=str(payload.get("table_block_id") or "") or None,
        source_type=payload.get("source_type") if payload.get("source_type") in {"text", "table", "figure", "caption"} else "text",
    )


def point_id(span_id: str) -> str:
    return str(UUID(hex=hashlib.sha256(span_id.encode("utf-8")).hexdigest()[:32]))


def qdrant_url(path: str) -> str:
    return f"{settings.qdrant_url.rstrip('/')}{path}"
