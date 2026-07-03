import asyncio
from datetime import UTC, datetime
from io import BytesIO
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import UploadFile

from app.service.service import OrchestratorService, OrchestratorServiceError
from infra.postgres.orchestrator_db import IngestionTask
from shared.contracts import IngestionReport, UserRole
from shared.security import AuthenticatedPrincipal


class FakeRepository:
    def __init__(self, task: IngestionTask | None = None) -> None:
        self.task = task
        self.failed_message: str | None = None
        self.transitions: list[str] = []

    async def create(self, user_id: UUID) -> IngestionTask:
        now = datetime.now(UTC)
        self.task = IngestionTask(
            id=uuid4(),
            user_id=user_id,
            status="pending",
            created_at=now,
            updated_at=now,
        )
        self.transitions.append("pending")
        return self.task

    async def get(self, task_id: UUID) -> IngestionTask | None:
        if self.task is not None and self.task.id == task_id:
            return self.task
        return None

    async def mark_processing(
        self,
        task: IngestionTask,
        report: IngestionReport,
    ) -> IngestionTask:
        task.status = "processing"
        task.report = report.model_dump(mode="json")
        self.transitions.append("processing")
        return task

    async def mark_completed(
        self,
        task: IngestionTask,
        report: IngestionReport,
    ) -> IngestionTask:
        task.status = "completed"
        task.report = report.model_dump(mode="json")
        self.transitions.append("completed")
        return task

    async def mark_failed(self, task: IngestionTask, message: str) -> IngestionTask:
        task.status = "failed"
        task.error_message = message
        self.failed_message = message
        self.transitions.append("failed")
        return task


def principal(role: UserRole = UserRole.RESEARCHER) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(user_id=uuid4(), role=role, token_id=uuid4())


def report_payload() -> dict[str, object]:
    return {
        "stage": "uploaded",
        "sources": [
            {
                "object_key": "uploads/user/task/file.docx",
                "original_filename": "file.docx",
                "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "size_bytes": 4,
                "sha256": "a" * 64,
            }
        ],
        "warnings": [],
    }


def document_payload() -> dict[str, object]:
    return {
        "id": "document-1",
        "source_type": "docx",
        "title": "file.docx",
        "content": "Nickel recovery 82 %",
        "source_spans": [
            {
                "document_id": "document-1",
                "page": 1,
                "start_offset": 0,
                "end_offset": 20,
                "text": "Nickel recovery 82 %",
                "source_type": "text",
            }
        ],
        "access_policy": {"level": "internal", "allowed_roles": []},
    }


def service(repository: FakeRepository, client: httpx.AsyncClient) -> OrchestratorService:
    return OrchestratorService(
        repository,
        client,
        "http://ingestion",
        "http://knowledge",
        "http://retrieval",
        "http://model",
    )


def test_create_task_runs_complete_ingestion_pipeline() -> None:
    repository = FakeRepository()
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path.endswith("/sources"):
            assert request.headers["Authorization"] == "Bearer token"
            return httpx.Response(201, json=report_payload())
        if request.url.path.endswith("/normalize"):
            assert request.headers["Authorization"] == "Bearer token"
            return httpx.Response(
                200,
                json={"documents": [document_payload()], "warnings": ["parser_warning"]},
            )
        if request.url.path == "/v1/documents/extract":
            return httpx.Response(
                200,
                json={
                    "document_id": "document-1",
                    "extraction": {"confirmed": [], "candidates": []},
                    "graph_write": {
                        "backend": "neo4j",
                        "mode": "mock",
                        "document_ids": ["document-1"],
                        "records_count": 0,
                        "warnings": ["neo4j_adapter_pending"],
                    },
                    "warnings": ["neo4j_adapter_pending"],
                },
            )
        return httpx.Response(
            200,
            json={
                "vector_write": {
                    "backend": "qdrant",
                    "mode": "mock",
                    "document_ids": ["document-1"],
                    "records_count": 1,
                    "warnings": ["qdrant_adapter_pending"],
                },
                "warnings": ["qdrant_adapter_pending"],
            },
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await service(repository, client).create_task(
                principal(),
                [UploadFile(file=BytesIO(b"data"), filename="file.docx")],
                "Bearer token",
                "request-1",
            )
            assert result.status.value == "completed"
            assert result.report is not None
            assert result.report.warnings == [
                "parser_warning",
                "neo4j_adapter_pending",
                "qdrant_adapter_pending",
            ]

    asyncio.run(run())
    assert repository.transitions == ["pending", "processing", "completed"]
    assert calls[1:] == [
        f"/ingestion/tasks/{repository.task.id}/normalize",
        "/v1/documents/extract",
        "/v1/documents/index",
    ]


def test_storage_failure_marks_task_failed() -> None:
    repository = FakeRepository()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            503,
            json={
                "code": "storage_unavailable",
                "message": "Source storage is unavailable",
                "request_id": "request-1",
            },
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(OrchestratorServiceError):
                await service(repository, client).create_task(
                    principal(),
                    [UploadFile(file=BytesIO(b"data"), filename="file.docx")],
                    "Bearer token",
                    "request-1",
                )

    asyncio.run(run())
    assert repository.failed_message == "Source storage is unavailable"
    assert repository.transitions == ["pending", "failed"]


def test_empty_normalization_marks_task_failed() -> None:
    repository = FakeRepository()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/sources"):
            return httpx.Response(201, json=report_payload())
        return httpx.Response(
            200,
            json={"documents": [], "warnings": ["unsupported_source_format:file.bin"]},
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(OrchestratorServiceError) as error:
                await service(repository, client).create_task(
                    principal(),
                    [UploadFile(file=BytesIO(b"data"), filename="file.bin")],
                    "Bearer token",
                    "request-1",
                )
            assert error.value.code == "normalization_empty"

    asyncio.run(run())
    assert repository.transitions == ["pending", "processing", "failed"]


def test_task_is_visible_only_to_owner_or_admin() -> None:
    owner = principal()
    now = datetime.now(UTC)
    task = IngestionTask(
        id=uuid4(),
        user_id=owner.user_id,
        status="pending",
        created_at=now,
        updated_at=now,
    )
    repository = FakeRepository(task)

    async def run() -> None:
        async with httpx.AsyncClient() as client:
            orchestrator = service(repository, client)
            assert (await orchestrator.get_task(task.id, owner)).id == task.id
            assert (await orchestrator.get_task(task.id, principal(UserRole.ADMIN))).id == task.id
            with pytest.raises(OrchestratorServiceError) as error:
                await orchestrator.get_task(task.id, principal())
            assert error.value.status_code == 404

    asyncio.run(run())
