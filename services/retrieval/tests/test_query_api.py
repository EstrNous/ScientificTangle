from unittest.mock import AsyncMock

import httpx
from app.main import app
from fastapi.testclient import TestClient

from shared.contracts import (
    AccessPolicy,
    QueryIR,
    SearchResult,
    SearchResultPayload,
    SourcePayload,
    SourceSpan,
)


class FakeStorageAdapter:
    is_ready = True

    async def search(self, question, filters, access_roles, limit):
        span = SourceSpan(
            document_id="d1",
            page=1,
            start_offset=0,
            end_offset=10,
            text="nickel 82 %",
            source_type="text",
        )
        return SearchResultPayload(
            items=[
                SearchResult(
                    source=SourcePayload(
                        source_span=span,
                        document_title="T",
                        source_type="article",
                        access_policy=AccessPolicy(level="internal"),
                    ),
                    relevance_score=0.9,
                )
            ]
        )


def test_query_endpoint_with_mock_model() -> None:
    query_ir = QueryIR(
        raw_query="nickel",
        filters={},
        entities=[],
        intent="fact_lookup",
    )

    async def mock_post(url, **kwargs):
        if url.endswith("/v1/query-ir"):
            return httpx.Response(
                200,
                json={"query_ir": query_ir.model_dump(mode="json")},
                request=httpx.Request("POST", url),
            )
        if url.endswith("/v1/rerank"):
            return httpx.Response(
                200,
                json={"scored_items": [], "warnings": []},
                request=httpx.Request("POST", url),
            )
        return httpx.Response(404, request=httpx.Request("POST", url))

    with TestClient(app) as client:
        client.app.state.http_client.post = AsyncMock(side_effect=mock_post)
        client.app.state.storage_adapter = FakeStorageAdapter()
        response = client.post(
            "/v1/query",
            json={
                "question": "nickel",
                "access_roles": ["researcher"],
                "limit": 5,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["query_ir"]["raw_query"] == "nickel"


def test_health_smoke() -> None:
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/metrics").status_code == 200
