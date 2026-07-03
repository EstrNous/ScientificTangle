import asyncio
from types import SimpleNamespace

import httpx

from app.api.extraction import extract_document
from shared.contracts import (
    KnowledgeIngestionRequest,
    NormalizedDocument,
    StorageWriteResult,
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

    document = NormalizedDocument(
        id="document-1",
        source_type="docx",
        title="report.docx",
        content="Nickel recovery 82 %",
    )

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
