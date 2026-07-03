from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from shared.contracts import NormalizedDocument, SourceSpan


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def test_extract_document_returns_adapter_pending(client: TestClient) -> None:
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
    mock_response = httpx.Response(
        200,
        json={"confirmed": [{"text": "Ni"}], "candidates": []},
        request=httpx.Request("POST", "http://model/v1/extraction/structured"),
    )
    client.app.state.http_client.post = AsyncMock(return_value=mock_response)
    response = client.post("/v1/documents/extract", json={"document": document.model_dump(mode="json")})
    assert response.status_code == 200
    payload = response.json()
    assert payload["graph_write"]["mode"] == "mock"
    assert payload["graph_write"]["records_count"] == 1


def test_health_smoke(client: TestClient) -> None:
    assert client.get("/health").status_code == 200
