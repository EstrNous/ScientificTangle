from unittest.mock import AsyncMock

import httpx
from fastapi.testclient import TestClient

from app.main import app
from shared.contracts import (
    KnowledgeIngestionResponse,
    NormalizedDocument,
    SourceSpan,
    StorageWriteResult,
    TableBlock,
)

COLLECTION_NAME = "st_evidence_v1"


def test_indexing_returns_explicit_qdrant_mock_counts() -> None:
    table = TableBlock(
        id="table-1",
        document_id="document-1",
        page=1,
        headers=["parameter", "value"],
        rows=[["recovery", "82 %"]],
    )
    document = NormalizedDocument(
        id="document-1",
        source_type="docx",
        title="report.docx",
        content="Nickel recovery 82 %",
        source_spans=[
            SourceSpan(
                document_id="document-1",
                page=1,
                start_offset=0,
                end_offset=20,
                text="Nickel recovery 82 %",
                source_type="text",
            )
        ],
        table_blocks=[table],
    )
    knowledge_result = KnowledgeIngestionResponse(
        document_id=document.id,
        graph_write=StorageWriteResult(
            backend="neo4j",
            document_ids=[document.id],
            warnings=["neo4j_adapter_pending"],
        ),
    )

    async def mock_get(url: str, **kwargs):
        if url.endswith(f"/collections/{COLLECTION_NAME}"):
            return httpx.Response(
                200,
                json={"result": {"status": "green"}},
                request=httpx.Request("GET", url),
            )
        return httpx.Response(404, request=httpx.Request("GET", url))

    async def mock_put(url: str, **kwargs):
        if f"/collections/{COLLECTION_NAME}" in url:
            return httpx.Response(
                200,
                json={"result": {"status": "completed"}},
                request=httpx.Request("PUT", url),
            )
        return httpx.Response(404, request=httpx.Request("PUT", url))

    async def mock_post(url: str, **kwargs):
        if url.endswith("/embeddings"):
            return httpx.Response(
                200,
                json={
                    "embeddings": [{"vector": [0.0] * 256}],
                    "warnings": [],
                },
                request=httpx.Request("POST", url),
            )
        return httpx.Response(404, request=httpx.Request("POST", url))

    with TestClient(app) as client:
        client.app.state.http_client.get = AsyncMock(side_effect=mock_get)
        client.app.state.http_client.put = AsyncMock(side_effect=mock_put)
        client.app.state.http_client.post = AsyncMock(side_effect=mock_post)
        response = client.post(
            "/v1/documents/index",
            json={
                "documents": [document.model_dump(mode="json")],
                "knowledge_results": [knowledge_result.model_dump(mode="json")],
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["vector_write"]["backend"] == "qdrant"
        assert body["vector_write"]["mode"] == "mock"
        assert body["vector_write"]["records_count"] == 1
        assert body["vector_write"]["document_ids"] == [document.id]
