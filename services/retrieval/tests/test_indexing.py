import asyncio
from types import SimpleNamespace

from fastapi import Response

from app.api.indexing import index_documents
from app.api.health import ready
from app.storage import PendingRetrievalStorageAdapter
from shared.contracts import NormalizedDocument, RetrievalIndexRequest, StorageWriteResult


class FakeStorageAdapter:
    is_ready = True

    async def index(self, request: RetrievalIndexRequest) -> StorageWriteResult:
        return StorageWriteResult(
            backend="qdrant",
            mode="real",
            document_ids=[document.id for document in request.documents],
            records_count=sum(len(document.source_spans) for document in request.documents),
        )


def test_indexing_uses_real_qdrant_adapter() -> None:
    request = RetrievalIndexRequest(
        documents=[
            NormalizedDocument(
                id="document-1",
                source_type="docx",
                title="report.docx",
                content="Nickel recovery 82 %",
            )
        ]
    )
    app_request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(storage_adapter=FakeStorageAdapter()))
    )

    result = asyncio.run(index_documents(request, app_request))

    assert result.vector_write.mode == "real"
    assert result.vector_write.document_ids == ["document-1"]


def test_readiness_is_closed_for_pending_adapter() -> None:
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(storage_adapter=PendingRetrievalStorageAdapter())
        )
    )
    response = Response()

    result = asyncio.run(ready(request, response))

    assert response.status_code == 503
    assert result["ready"] is False
