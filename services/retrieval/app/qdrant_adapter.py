
import httpx

from shared.contracts import (
    AccessPolicy,
    RetrievalIndexRequest,
    SearchResult,
    SearchResultPayload,
    SourcePayload,
    SourceSpan,
    StorageWriteResult,
)

from .core.config import settings

COLLECTION_NAME = "st_evidence_v1"
VECTOR_SIZE = 256


def qdrant_url(path: str) -> str:
    return f"{settings.qdrant_url.rstrip('/')}{path}"


def payload_allowed(payload: dict, access_roles: list[str]) -> bool:
    if "admin" in access_roles:
        return True
    if payload.get("access_level") == "public":
        return True
    allowed_roles = {str(role) for role in payload.get("allowed_roles", [])}
    if payload.get("access_level") == "internal":
        internal = {"researcher", "analyst", "manager", "director"}
        if allowed_roles:
            internal &= allowed_roles
        return bool(set(access_roles) & internal)
    return bool(allowed_roles and allowed_roles & set(access_roles))


def payload_to_span(payload: dict) -> SourceSpan:
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


def payload_to_source(payload: dict) -> SourcePayload:
    span = payload_to_span(payload)
    return SourcePayload(
        source_span=span.model_copy(update={"id": str(payload.get("source_span_id", span.id))}),
        document_title=str(payload.get("document_title", "")),
        source_type=str(payload.get("document_source_type", "")),
        metadata=dict(payload.get("document_metadata") or {}),
        access_policy=AccessPolicy(
            level=payload.get("access_level", "internal"),
            allowed_roles=list(payload.get("allowed_roles") or []),
        ),
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
        return StorageWriteResult(backend="qdrant", mode="live")

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
        response = await self._client.post(
            qdrant_url(f"/collections/{COLLECTION_NAME}/points/search"),
            json={
                "vector": vector,
                "limit": max(limit * 3, limit),
                "with_payload": True,
            },
        )
        if response.status_code == 404:
            return SearchResultPayload(items=[], total_found=0, warnings=["collection_not_found"])
        response.raise_for_status()
        items: list[SearchResult] = []
        for point in response.json().get("result", []):
            payload = point.get("payload") or {}
            if not payload_allowed(payload, access_roles):
                continue
            items.append(payload_to_search_result(payload, float(point.get("score") or 0.0)))
            if len(items) >= limit:
                break
        return SearchResultPayload(items=items, total_found=len(items), warnings=warnings)

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
        if not payload_allowed(payload, access_roles):
            return None
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
