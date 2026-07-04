from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from app.main import app
from fastapi.testclient import TestClient

from adapters.neo4j_adapter import Neo4jKnowledgeAdapter
from app.main import app
from shared.utils.source_span import compute_source_span_id
from app.api.extraction import extract_document
from shared.contracts import (
    KnowledgeIngestionRequest,
    NormalizedDocument,
    StorageWriteResult,
    SourceSpan
)


class FakeStorageAdapter:
    is_ready = True

    async def write_extraction(self, document, extraction):
        return StorageWriteResult(
            backend="neo4j",
            mode="live",
            document_ids=[document.id],
            records_count=len(extraction.get("confirmed", [])),
        )


def test_extraction_uses_real_neo4j_adapter() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"confirmed": [{"artifact_type": "claim"}], "candidates": []},
        )


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def test_extract_document_writes_to_neo4j_when_adapter_available(client: TestClient) -> None:
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
    )
    span_id = compute_source_span_id(document.source_spans[0])
    mock_response = httpx.Response(
        200,
        json={
            "confirmed": [
                {
                    "id": "a1",
                    "kind": "material",
                    "value": "Ni",
                    "confidence": 0.9,
                    "status": "confirmed",
                    "source_span_ids": [span_id],
                    "source_spans": [document.source_spans[0].model_dump(mode="json")],
                }
            ],
            "candidates": [],
        },
        request=httpx.Request("POST", "http://model/v1/extraction/structured"),
    )
    adapter = MagicMock(spec=Neo4jKnowledgeAdapter)
    adapter.write_bundle = AsyncMock(return_value=True)
    client.app.state.http_client.post = AsyncMock(return_value=mock_response)
    client.app.state.neo4j_adapter = adapter
    response = client.post("/v1/documents/extract", json={"document": document.model_dump(mode="json")})
    assert response.status_code == 200
    payload = response.json()
    assert payload["graph_write"]["mode"] == "live"
    assert payload["graph_write"]["confirmed_count"] == 1
    adapter.write_bundle.assert_awaited_once()


def test_health_smoke(client: TestClient) -> None:
    assert client.get("/health").status_code == 200
