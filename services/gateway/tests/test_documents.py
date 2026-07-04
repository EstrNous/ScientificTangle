import asyncio
from datetime import UTC, datetime
from io import BytesIO
from uuid import uuid4

import httpx
import pytest
from app.service.service import GatewayService, GatewayServiceError
from fastapi import UploadFile


def task_payload() -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(uuid4()),
        "status": "pending",
        "report": {
            "stage": "uploaded",
            "sources": [
                {
                    "object_key": "uploads/user/task/file.txt",
                    "original_filename": "file.txt",
                    "content_type": "text/plain",
                    "size_bytes": 4,
                    "sha256": "a" * 64,
                }
            ],
            "warnings": [],
        },
        "error_message": None,
        "created_at": now,
        "updated_at": now,
    }


def test_upload_forwards_authentication_and_request_id() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers["Authorization"]
        captured["request_id"] = request.headers["X-Request-ID"]
        captured["path"] = request.url.path
        return httpx.Response(202, json=task_payload())

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = GatewayService(client, "http://orchestrator", 1024)
            result = await service.upload_documents(
                [UploadFile(file=BytesIO(b"data"), filename="file.txt")],
                "Bearer token",
                "request-1",
            )
            assert result.status.value == "pending"

    asyncio.run(run())
    assert captured == {
        "authorization": "Bearer token",
        "request_id": "request-1",
        "path": "/ingestion/tasks",
    }


@pytest.mark.parametrize(
    ("content", "limit", "code"),
    [(b"", 10, "empty_file"), (b"1234", 3, "upload_too_large")],
)
def test_upload_validation(content: bytes, limit: int, code: str) -> None:
    async def run() -> None:
        async with httpx.AsyncClient() as client:
            service = GatewayService(client, "http://orchestrator", limit)
            with pytest.raises(GatewayServiceError) as error:
                await service.upload_documents(
                    [UploadFile(file=BytesIO(content), filename="file.txt")],
                    "Bearer token",
                    "request-1",
                )
            assert error.value.code == code

    asyncio.run(run())


def test_delete_document_proxies_to_orchestrator() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        captured["authorization"] = request.headers["Authorization"]
        captured["request_id"] = request.headers["X-Request-ID"]
        return httpx.Response(
            200,
            json={
                "document_id": "doc-1",
                "status": "deleted",
                "deleted_source_spans": 2,
                "deleted_vectors": 2,
                "deleted_graph_nodes": 1,
                "warnings": [],
            },
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = GatewayService(client, "http://orchestrator", 1024)
            result = await service.delete_document("doc-1", "Bearer token", "request-1")
            assert result["status"] == "deleted"

    asyncio.run(run())
    assert captured == {
        "method": "DELETE",
        "path": "/documents/doc-1",
        "authorization": "Bearer token",
        "request_id": "request-1",
    }
