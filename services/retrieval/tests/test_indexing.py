from unittest.mock import AsyncMock

import httpx
from fastapi.testclient import TestClient

from app.api.query import source_span_id
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
    span = SourceSpan(
        document_id="document-1",
        page=1,
        start_offset=0,
        end_offset=20,
        text="Nickel recovery 82 %",
        source_type="text",
    )
    span_id = source_span_id(span)
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
        source_spans=[span],
        table_blocks=[table],
    )
    knowledge_result = KnowledgeIngestionResponse(
        document_id=document.id,
        extraction={
            "confirmed": [
                {
                    "id": "claim-1",
                    "kind": "claim",
                    "source_span_ids": [span_id],
                },
                {
                    "id": "entity-1",
                    "kind": "entity",
                    "source_span_ids": [span_id],
                },
                {
                    "id": "candidate-ignored",
                    "kind": "claim",
                    "source_span_ids": [],
                },
            ],
            "candidates": [],
        },
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
            texts = kwargs["json"]["texts"]
            return httpx.Response(
                200,
                json={
                    "embeddings": [{"vector": [0.0] * 256} for _ in texts],
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
        assert body["vector_write"]["mode"] == "live"
        assert body["vector_write"]["records_count"] == 2
        assert body["vector_write"]["document_ids"] == [document.id]

        put_calls = client.app.state.http_client.put.await_args_list
        points_payload = put_calls[-1].kwargs["json"]["points"]
        text_point = next(point for point in points_payload if point["payload"]["item_type"] == "source_span")
        table_point = next(point for point in points_payload if point["payload"]["item_type"] == "table_row")
        assert text_point["payload"]["claim_ids"] == ["claim-1"]
        assert text_point["payload"]["graph_entity_ids"] == ["entity-1"]
        assert table_point["payload"]["claim_ids"] == []
