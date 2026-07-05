
import httpx

from shared.contracts import (
    AccessPolicy,
    RetrievalIndexRequest,
    SearchResult,
    SearchResultPayload,
    SourcePayload,
    SourceSpan,
    StorageWriteResult,
    UserRole,
)

from .core.config import settings
from .storage import StorageAdapterNotReady, payload_access_allowed

COLLECTION_NAME = "st_evidence_v1"
VECTOR_SIZE = 256


def qdrant_url(path: str) -> str:
    return f"{settings.qdrant_url.rstrip('/')}{path}"


def payload_allowed(payload: dict, access_roles: list[str]) -> bool:
    return payload_access_allowed(payload, access_roles)


def payload_to_span(payload: dict) -> SourceSpan:
    table_block_id = str(payload.get("table_block_id") or "") or None
    table_row_id = str(payload.get("table_row_id") or "") or None
    if table_row_id and not table_block_id:
        table_block_id = table_row_id
    return SourceSpan(
        document_id=str(payload["document_id"]),
        page=int(payload.get("page") or 1),
        start_offset=int(payload.get("start_offset") or 0),
        end_offset=int(payload.get("end_offset") or len(str(payload.get("text", "")))),
        text=str(payload.get("text", "")),
        table_block_id=table_block_id,
        source_type=(
            payload.get("source_type")
            if payload.get("source_type") in {"text", "table", "figure", "caption"}
            else "text"
        ),
    )


def payload_to_source(payload: dict) -> SourcePayload:
    span = payload_to_span(payload)
    highlight_start = int(payload.get("highlight_start", span.start_offset) or 0)
    highlight_end = int(payload.get("highlight_end", span.end_offset) or len(span.text))
    relative_start = max(0, highlight_start - span.start_offset)
    relative_end = max(relative_start, highlight_end - span.start_offset)
    highlight_text = span.text[relative_start:relative_end] if span.text else ""
    return SourcePayload(
        source_span=span.model_copy(update={"id": str(payload.get("source_span_id", span.id))}),
        document_title=str(payload.get("document_title", "")),
        source_type=str(payload.get("document_source_type", "")),
        metadata=dict(payload.get("document_metadata") or {}),
        access_policy=AccessPolicy(
            level=payload.get("access_level", "internal"),
            allowed_roles=list(payload.get("allowed_roles") or []),
        ),
        highlight_start=highlight_start,
        highlight_end=highlight_end,
        highlight_text=highlight_text,
        highlight_fragments=[highlight_text] if highlight_text else [],
    )


def payload_to_search_result(payload: dict, score: float) -> SearchResult:
    source = payload_to_source(payload)
    return SearchResult(
        source=source,
        relevance_score=score,
        claim_ids=list(payload.get("claim_ids") or []),
        entity_ids=list(payload.get("graph_entity_ids") or []),
    )


class QdrantRetrievalStorageAdapter:
    is_ready = True

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def index(self, request: RetrievalIndexRequest) -> StorageWriteResult:
        from .indexing_ops import write_index

        return await write_index(self._client, request)

    async def search(
        self,
        question: str,
        filters: dict,
        access_roles: list[str],
        limit: int,
    ) -> SearchResultPayload:
        warnings: list[str] = []
        if not question.strip():
            return SearchResultPayload(items=[], total_found=0, warnings=["empty_question"])
        vector = await self._embed(question, "query")
        request_payload = {
            "vector": vector,
            "limit": max(limit * 3, limit),
            "with_payload": True,
        }
        query_filter = build_filter(filters, access_roles)
        if query_filter:
            request_payload["filter"] = query_filter
        response = await self._client.post(
            qdrant_url(f"/collections/{COLLECTION_NAME}/points/search"),
            json=request_payload,
        )
        if response.status_code == 404:
            return SearchResultPayload(items=[], total_found=0, warnings=["collection_not_found"])
        response.raise_for_status()
        items: list[SearchResult] = []
        for point in response.json().get("result", []):
            payload = point.get("payload") or {}
            items.append(payload_to_search_result(payload, float(point.get("score") or 0.0)))
            if len(items) >= limit:
                break
        return SearchResultPayload(items=items, total_found=len(items), warnings=warnings)

    async def search_lexical(
        self,
        tokens: list[str],
        filters: dict,
        access_roles: list[str],
        limit: int,
        table_only: bool = False,
    ) -> SearchResultPayload:
        if not tokens:
            return SearchResultPayload()
        query_filter = build_filter(filters, access_roles)
        query_filter.setdefault("must", []).append(
            {"key": "lexical_tokens", "match": {"any": tokens}}
        )
        if table_only:
            query_filter["must"].append({"key": "item_type", "match": {"value": "table_row"}})
        response = await self._client.post(
            qdrant_url(f"/collections/{COLLECTION_NAME}/points/scroll"),
            json={"filter": query_filter, "limit": max(limit * 3, limit), "with_payload": True},
        )
        if response.status_code == 404:
            return SearchResultPayload(warnings=["collection_not_found"])
        response.raise_for_status()
        points = response.json().get("result", {}).get("points", [])
        token_set = set(tokens)
        ranked = []
        for point in points:
            payload = point.get("payload") or {}
            matched = len(token_set & set(payload.get("lexical_tokens") or []))
            if matched:
                ranked.append(payload_to_search_result(payload, matched / max(len(token_set), 1)))
        ranked.sort(key=lambda item: item.relevance_score, reverse=True)
        return SearchResultPayload(items=ranked[:limit], total_found=len(ranked[:limit]))

    async def get_source(
        self,
        source_span_id: str,
        access_roles: list[str],
    ) -> SourcePayload | None:
        response = await self._client.post(
            qdrant_url(f"/collections/{COLLECTION_NAME}/points/scroll"),
            json={
                "filter": {
                    "must": [
                        {"key": "source_span_id", "match": {"value": source_span_id}},
                    ]
                },
                "limit": 1,
                "with_payload": True,
            },
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        points = response.json().get("result", {}).get("points", [])
        if not points:
            return None
        payload = points[0].get("payload") or {}
        return payload_to_source(payload)

    async def _embed(self, text: str, input_type: str) -> list[float]:
        response = await self._client.post(
            f"{settings.model_url.rstrip('/')}/v1/embeddings",
            json={"texts": [text], "dimensions": VECTOR_SIZE, "input_type": input_type},
        )
        response.raise_for_status()
        embeddings = response.json().get("embeddings", [])
        if not embeddings:
            raise httpx.HTTPError("empty_embeddings_response")
        return list(embeddings[0]["vector"])


def build_filter(filters: dict, access_roles: list[str]) -> dict:
    must: list[dict] = []
    roles = set(access_roles)
    if UserRole.ADMIN.value not in roles:
        access_should = [{"key": "access_level", "match": {"value": "public"}}]
        if access_roles:
            internal_roles = {
                UserRole.RESEARCHER.value,
                UserRole.ANALYST.value,
                UserRole.MANAGER.value,
            }
            if roles & internal_roles:
                access_should.extend(
                    [
                        {
                            "must": [
                                {"key": "access_level", "match": {"value": "internal"}},
                                {"is_empty": {"key": "allowed_roles"}},
                            ],
                        },
                        {
                            "must": [
                                {"key": "access_level", "match": {"value": "internal"}},
                                {"key": "allowed_roles", "match": {"any": access_roles}},
                            ],
                        },
                    ]
                )
            access_should.append({"key": "allowed_roles", "match": {"any": access_roles}})
        must.append({"should": access_should})
    source_types = list(filters.get("source_type_constraints") or filters.get("source_types") or [])
    if source_types:
        must.append({"key": "document_source_type", "match": {"any": source_types}})
    dictionary_version_id = str(filters.get("dictionary_version_id") or "")
    if dictionary_version_id:
        must.append({"key": "dictionary_version_id", "match": {"value": dictionary_version_id}})
    geo = [str(value).lower() for value in filters.get("geo_constraints") or []]
    if geo:
        must.append({"should": [
            {"key": "geo_bucket", "match": {"any": geo}},
            {"key": "geo_country", "match": {"any": geo}},
        ]})
    numeric = [item for item in filters.get("numeric_constraints", []) if isinstance(item, dict)]
    for constraint in numeric:
        unit = str(constraint.get("unit", "")).lower()
        if unit:
            must.append({"key": "units", "match": {"value": unit}})
        minimum = constraint.get("range_min", constraint.get("value"))
        maximum = constraint.get("range_max", constraint.get("value"))
        if maximum is not None:
            must.append({"key": "numeric_min", "range": {"lte": float(maximum)}})
        if minimum is not None:
            must.append({"key": "numeric_max", "range": {"gte": float(minimum)}})
    time_constraints = filters.get("time_constraints") or {}
    if isinstance(time_constraints, dict):
        if time_constraints.get("start_year") is not None:
            must.append({"key": "published_year", "range": {"gte": int(time_constraints["start_year"])}})
        if time_constraints.get("end_year") is not None:
            must.append({"key": "published_year", "range": {"lte": int(time_constraints["end_year"])}})
    return {"must": must} if must else {}
