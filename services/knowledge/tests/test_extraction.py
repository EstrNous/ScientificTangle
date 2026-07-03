from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app

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
            mode="real",
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


def test_extract_document_returns_adapter_pending(client: TestClient) -> None:
    document = NormalizedDocument(
        id="document-1",
        source_type="docx",
        title="report.docx",
        content="Nickel recovery 82 %",
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

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            request = SimpleNamespace(
                app=SimpleNamespace(
                    state=SimpleNamespace(
                        http_client=client,
                        storage_adapter=FakeStorageAdapter(),
                    )
                )
            )
            return await extract_document(
                KnowledgeIngestionRequest(document=document),
                request,
            )

    result = asyncio.run(execute())

    assert result.graph_write.mode == "real"
    assert result.graph_write.records_count == 1

def test_health_smoke(client: TestClient) -> None:
    assert client.get("/health").status_code == 200
