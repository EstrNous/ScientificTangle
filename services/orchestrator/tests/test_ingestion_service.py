import asyncio
from datetime import UTC, datetime
from io import BytesIO
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import UploadFile

from infra.postgres.orchestrator_db import IngestionTask
from app.service.service import OrchestratorService, OrchestratorServiceError
from shared.contracts import IngestionReport, UserRole
from shared.security import AuthenticatedPrincipal


class FakeRepository:
    def __init__(self, task: IngestionTask | None = None) -> None:
        self.task = task
        self.failed_message: str | None = None

    async def create(self, user_id: UUID) -> IngestionTask:
        now = datetime.now(UTC)
        self.task = IngestionTask(
            id=uuid4(),
            user_id=user_id,
            status="pending",
            created_at=now,
            updated_at=now,
        )
        return self.task

    async def get(self, task_id: UUID) -> IngestionTask | None:
        if self.task is not None and self.task.id == task_id:
            return self.task
        return None

    async def set_report(
        self, task: IngestionTask, report: IngestionReport
    ) -> IngestionTask:
        task.report = report.model_dump(mode="json")
        return task

    async def mark_failed(self, task: IngestionTask, message: str) -> IngestionTask:
        task.status = "failed"
        task.error_message = message
        self.failed_message = message
        return task


def principal(role: UserRole = UserRole.RESEARCHER) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(user_id=uuid4(), role=role, token_id=uuid4())


def report_payload() -> dict[str, object]:
    return {
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
    }


def test_create_task_persists_storage_report() -> None:
    repository = FakeRepository()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer token"
        assert request.headers["X-Request-ID"] == "request-1"
        return httpx.Response(201, json=report_payload())

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = OrchestratorService(repository, client, "http://ingestion")
            result = await service.create_task(
                principal(),
                [UploadFile(file=BytesIO(b"data"), filename="file.txt")],
                "Bearer token",
                "request-1",
            )
            assert result.status.value == "pending"
            assert result.report is not None
            assert result.report.sources[0].original_filename == "file.txt"

    asyncio.run(run())


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
            service = OrchestratorService(repository, client, "http://ingestion")
            with pytest.raises(OrchestratorServiceError):
                await service.create_task(
                    principal(),
                    [UploadFile(file=BytesIO(b"data"), filename="file.txt")],
                    "Bearer token",
                    "request-1",
                )

    asyncio.run(run())
    assert repository.failed_message == "Source storage is unavailable"
    assert repository.task is not None
    assert repository.task.status == "failed"


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
            service = OrchestratorService(repository, client, "http://ingestion")
            assert (await service.get_task(task.id, owner)).id == task.id
            admin = principal(UserRole.ADMIN)
            assert (await service.get_task(task.id, admin)).id == task.id
            with pytest.raises(OrchestratorServiceError) as error:
                await service.get_task(task.id, principal())
            assert error.value.status_code == 404

    asyncio.run(run())
