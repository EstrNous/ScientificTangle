from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from app.main import app
from fastapi.testclient import TestClient

from adapters.neo4j_adapter import Neo4jKnowledgeAdapter
from app.main import app
from shared.contracts import NormalizedDocument, SourceSpan
from shared.utils.source_span import compute_source_span_id


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def test_extract_document_writes_to_neo4j_when_adapter_available(client: TestClient) -> None:
    document = NormalizedDocument(
        id="d1",
        source_type="article",
        title="T",
        content="Ni",
        source_spans=[
            SourceSpan(
                document_id="d1",
                page=1,
                start_offset=0,
                end_offset=2,
                text="Ni",
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
