import asyncio
from types import SimpleNamespace

import httpx

from app.api.extraction import extract_document
from shared.contracts import KnowledgeIngestionRequest, NormalizedDocument, SourceSpan


def test_extraction_returns_explicit_neo4j_mock_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "confirmed": [{"artifact_type": "claim"}],
                "candidates": [{"artifact_type": "entity"}],
                "warnings": [],
                "mode": "deterministic_degraded",
            },
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
    )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            app_request = SimpleNamespace(
                app=SimpleNamespace(state=SimpleNamespace(http_client=client))
            )
            result = await extract_document(
                KnowledgeIngestionRequest(document=document),
                app_request,
            )
            assert result.graph_write.backend == "neo4j"
            assert result.graph_write.mode == "mock"
            assert result.graph_write.records_count == 2
            assert result.warnings == ["neo4j_adapter_pending"]

    asyncio.run(run())
