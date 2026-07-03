import hashlib
import re
from typing import Any
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from shared.contracts import (
    EvidenceBundle,
    EvidenceItem,
    KnowledgeIngestionResponse,
    NormalizedDocument,
    QueryIR,
    RetrievalIndexRequest,
    RetrievalIndexResponse,
    SearchResultPayload,
    SourcePayload,
    SourceSpan,
    StorageWriteResult,
    TableBlock,
)

from shared.utils.source_span import compute_source_span_id as source_span_id
from ..core.config import settings
from ..storage import RetrievalStorageAdapter, StorageAdapterNotReady, access_allowed

router = APIRouter(prefix="/v1", tags=["retrieval"])

COLLECTION_NAME = "st_evidence_v1"
VECTOR_SIZE = 256
TOKEN_PATTERN = re.compile(r"[\w%/.-]+", re.UNICODE)
NUMBER_PATTERN = re.compile(r"[-+]?\d+(?:[,.]\d+)?")
UNIT_PATTERN = re.compile(r"%|мг/л|mg/l|мг/дм3|мг/дм³|м/с|m/s|кг/т|kg/t", re.IGNORECASE)


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
class IndexDocumentsRequest(RetrievalIndexRequest):
    claim_ids: list[str] = Field(default_factory=list)
    graph_entity_ids: list[str] = Field(default_factory=list)


def collect_index_links(request: RetrievalIndexRequest) -> tuple[list[str], list[str]]:
    claim_ids = list(getattr(request, "claim_ids", []) or [])
    graph_entity_ids = list(getattr(request, "graph_entity_ids", []) or [])
    for result in request.knowledge_results:
        claim_ids.extend(result.graph_write.claim_ids)
        graph_entity_ids.extend(result.graph_write.graph_entity_ids)
    return list(dict.fromkeys(item for item in claim_ids if item)), list(
        dict.fromkeys(item for item in graph_entity_ids if item)
    )


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
    return ResetIndexResponse(
        collection=COLLECTION_NAME,
        deleted=deleted,
        bootstrapped=bootstrapped,
    )


ENTITY_ARTIFACT_KINDS = {"entity", "alias", "material", "substance", "process", "equipment", "property", "geography", "expert", "source"}
CLAIM_ARTIFACT_KINDS = {"claim", "measurement", "relation", "recommendation", "conclusion", "date"}


def knowledge_index_metadata(
    knowledge_results: list[KnowledgeIngestionResponse],
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    claim_ids_by_span: dict[str, list[str]] = {}
    graph_entity_ids_by_span: dict[str, list[str]] = {}
    for result in knowledge_results:
        extraction = result.extraction if isinstance(result.extraction, dict) else {}
        for artifact in extraction.get("confirmed", []):
            if not isinstance(artifact, dict) or not artifact.get("id"):
                continue
            artifact_id = str(artifact["id"])
            kind = str(artifact.get("kind", ""))
            source_span_ids = [str(span_id) for span_id in artifact.get("source_span_ids", []) if span_id]
            for span_id in source_span_ids:
                if kind in ENTITY_ARTIFACT_KINDS:
                    graph_entity_ids_by_span.setdefault(span_id, []).append(artifact_id)
                if kind in CLAIM_ARTIFACT_KINDS:
                    claim_ids_by_span.setdefault(span_id, []).append(artifact_id)
    return dedupe_mapping(claim_ids_by_span), dedupe_mapping(graph_entity_ids_by_span)


def dedupe_mapping(mapping: dict[str, list[str]]) -> dict[str, list[str]]:
    return {key: list(dict.fromkeys(value)) for key, value in mapping.items()}


@router.post("/documents/index", response_model=RetrievalIndexResponse)
async def index_documents(
    request: RetrievalIndexRequest,
    app_request: Request,
) -> RetrievalIndexResponse:
    client: httpx.AsyncClient = app_request.app.state.http_client
    bootstrap = await ensure_collection(client)
    claim_ids, graph_entity_ids = collect_index_links(request)
    points = build_points(request.documents, claim_ids, graph_entity_ids)
    warnings = [*bootstrap.warnings]
    document_ids = [document.id for document in request.documents]
    if not points:
        return RetrievalIndexResponse(
            vector_write=StorageWriteResult(
                backend="qdrant",
                mode="live",
                document_ids=document_ids,
                records_count=0,
                claim_ids=claim_ids,
                graph_entity_ids=graph_entity_ids,
            ),
            warnings=warnings,
        )
    vectors_response = await build_embeddings(
        client,
        [point["payload"]["text"] for point in points],
        "document",
    )
    for point, vector in zip(points, vectors_response["vectors"], strict=True):
        point["vector"] = vector
    warnings.extend(vectors_response["warnings"])
    response = await client.put(
        qdrant_url(f"/collections/{COLLECTION_NAME}/points"),
        params={"wait": "true"},
        json={"points": points},
    )
    response.raise_for_status()
    return RetrievalIndexResponse(
        vector_write=StorageWriteResult(
            backend="qdrant",
            document_ids=[document.id for document in request.documents],
            records_count=len(points),
            claim_ids=claim_ids,
            graph_entity_ids=graph_entity_ids,
        ),
        warnings=warnings,
    )


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
            warnings.append(
                f"Failed to create Qdrant payload index {field_name}: {index_response.text}"
            )
    return BootstrapIndexResponse(
        collection=COLLECTION_NAME,
        created=created,
        indexes=indexed_fields,
        warnings=warnings,
    )


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


def build_points(
    documents: list[NormalizedDocument],
    claim_ids_by_span: dict[str, list[str]],
    graph_entity_ids_by_span: dict[str, list[str]],
) -> list[dict[str, Any]]:
    points = []
    seen_ids: set[str] = set()
    for document in documents:
        for span in [*document.source_spans, *table_row_spans(document)]:
            span_id = source_span_id(span)
            if span_id in seen_ids:
                continue
            seen_ids.add(span_id)
            payload = build_payload(
                document,
                span,
                span_id,
                claim_ids_by_span.get(span_id, []),
                graph_entity_ids_by_span.get(span_id, []),
            )
            points.append({"id": point_id(span_id), "payload": payload})
    return points


def table_row_spans(document: NormalizedDocument) -> list[SourceSpan]:
    spans = []
    for table in document.table_blocks:
        for row_index, row in enumerate(table.rows):
            text = table_row_text(table, row)
            spans.append(
                SourceSpan(
                    document_id=table.document_id,
                    page=table.page,
                    start_offset=row_index,
                    end_offset=row_index + len(text),
                    text=text,
                    table_block_id=f"{table.id}:row:{row_index}",
                    source_type="table",
                )
            )
    return spans


def table_row_text(table: TableBlock, row: list[str]) -> str:
    pairs = []
    for index, value in enumerate(row):
        header = table.headers[index] if index < len(table.headers) else f"col_{index + 1}"
        pairs.append(f"{header}: {value}")
    prefix = f"{table.caption}. " if table.caption else ""
    return prefix + "; ".join(pairs)


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


async def build_embeddings(
    client: httpx.AsyncClient,
    texts: list[str],
    input_type: str,
) -> dict[str, Any]:
    response = await client.post(
        f"{settings.model_url.rstrip('/')}/v1/embeddings",
        json={
            "texts": texts,
            "dimensions": VECTOR_SIZE,
            "input_type": input_type,
        },
    )
    response.raise_for_status()
    payload = response.json()
    vectors = [item["vector"] for item in payload.get("embeddings", [])]
    if len(vectors) != len(texts):
        raise httpx.HTTPError("Model embeddings response size mismatch")
    return {"vectors": vectors, "warnings": payload.get("warnings", [])}


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


def collect_evidence_items(
    query_ir: QueryIR,
    documents: list[NormalizedDocument],
    access_roles: list[str],
) -> list[EvidenceItem]:
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
                    relevance_score=evidence_score(
                        query_tokens,
                        text_tokens,
                        query_ir.filters,
                        span.text,
                    ),
                    extraction_method="semantic",
                )
            )
    return items


def payload_allowed(payload: dict[str, Any], access_roles: list[str]) -> bool:
    if "admin" in access_roles:
        return True
    if payload.get("access_level") == "public":
        return True
    allowed_roles = {str(role) for role in payload.get("allowed_roles", [])}
    return not allowed_roles or bool(allowed_roles & set(access_roles))


def retrieval_match(
    query_tokens: set[str],
    filters: dict[str, Any],
    text: str,
    payload: dict[str, Any],
) -> bool:
    text_tokens = normalized_tokens(text)
    if query_tokens & text_tokens:
        return True
    if constraints_match(filters, text):
        return True
    units = {str(unit).lower() for unit in payload.get("units", [])}
    for constraint in filters.get("numeric_constraints", []):
        if isinstance(constraint, dict) and str(constraint.get("unit", "")).lower() in units:
            return True
    geo_constraints = {
        str(value).lower()
        for value in filters.get("geo_constraints", [])
    }
    payload_geo = {
        str(payload.get("geo_bucket", "")).lower(),
        str(payload.get("geo_country", "")).lower(),
    }
    return bool(geo_constraints & payload_geo)


def constraints_match(filters: dict[str, Any], text: str) -> bool:
    lowered = text.lower()
    geo = [str(value).lower() for value in filters.get("geo_constraints", [])]
    if geo and any(value in lowered for value in geo):
        return True
    numeric = filters.get("numeric_constraints", [])
    return bool(numeric and any(char.isdigit() for char in text))


def evidence_score(
    query_tokens: set[str],
    text_tokens: set[str],
    filters: dict[str, Any],
    text: str,
) -> float:
    overlap = len(query_tokens & text_tokens) / max(len(query_tokens), 1)
    constraint_bonus = 0.25 if constraints_match(filters, text) else 0.0
    return min(1.0, round(overlap + constraint_bonus, 6))


def normalized_tokens(text: str) -> set[str]:
    return {
        token.strip(".,;:()[]{}").lower()
        for token in TOKEN_PATTERN.findall(text)
        if len(token.strip(".,;:()[]{}")) >= 2
    }


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
    aliases = {
        "мг/л": "mg/l",
        "мг/дм3": "mg/dm3",
        "мг/дм³": "mg/dm3",
        "м/с": "m/s",
        "кг/т": "kg/t",
    }
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
        source_type=(
            payload.get("source_type")
            if payload.get("source_type") in {"text", "table", "figure", "caption"}
            else "text"
        ),
    )


def source_span_id(span: SourceSpan) -> str:
    raw = (
        f"{span.document_id}:{span.page}:{span.start_offset}:"
        f"{span.end_offset}:{span.table_block_id or ''}"
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def point_id(span_id: str) -> str:
    return str(UUID(hex=hashlib.sha256(span_id.encode("utf-8")).hexdigest()[:32]))


def qdrant_url(path: str) -> str:
    return f"{settings.qdrant_url.rstrip('/')}{path}"
