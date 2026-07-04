import asyncio
import json
from datetime import UTC, datetime
from io import BytesIO
from uuid import UUID, uuid4

import httpx
import pytest
from app.service.base import OrchestratorServiceError
from app.service.ingestion import IngestionService
from fastapi import UploadFile

from infra.postgres.orchestrator_db import IngestionTask
from shared.contracts import IngestionReport, UserRole
from shared.security import AuthenticatedPrincipal


class FakeRepository:
    def __init__(self, task: IngestionTask | None = None) -> None:
        self.task = task
        self.failed_message: str | None = None
        self.transitions: list[str] = []
        self.audit_events: list[dict[str, object]] = []

    async def create(self, user_id: UUID, task_kind=None, dictionary_version_id=None) -> IngestionTask:
        now = datetime.now(UTC)
        self.task = IngestionTask(
            id=uuid4(),
            user_id=user_id,
            status="pending",
            created_at=now,
            updated_at=now,
            task_kind=(task_kind.value if task_kind else "document_ingestion"),
            dictionary_version_id=dictionary_version_id,
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

    async def record_audit_event(
        self,
        user_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict,
        request_id: str,
    ) -> None:
        self.audit_events.append(
            {
                "user_id": user_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": details,
                "request_id": request_id,
            }
        )


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


def service(repository: FakeRepository, client: httpx.AsyncClient) -> IngestionService:
    return IngestionService(
        repository=repository,
        client=client,
        notification_url="http://notification",
        internal_service_token="test-internal-token",
        enforce_active_dictionary=False,
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
                        "mode": "live",
                        "document_ids": ["document-1"],
                        "records_count": 0,
                        "confirmed_count": 0,
                        "claim_ids": [],
                        "graph_entity_ids": [],
                        "warnings": [],
                    },
                    "warnings": [],
                },
            )
        if request.url.path == "/v1/documents/index":
            return httpx.Response(
                200,
                json={
                    "vector_write": {
                        "backend": "qdrant",
                        "mode": "live",
                        "document_ids": ["document-1"],
                        "records_count": 1,
                        "confirmed_count": 0,
                        "claim_ids": [],
                        "graph_entity_ids": [],
                        "warnings": [],
                    },
                    "warnings": [],
                },
            )
        if request.url.path == "/internal/v1/events":
            return httpx.Response(200, json={"id": str(uuid4()), "type": "ingestion_complete"})
        if request.url.path == "/internal/v1/match":
            return httpx.Response(200, json=[])
        return httpx.Response(404, json={"code": "not_found", "message": "unexpected"})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            orchestrator = service(repository, client)
            result = await orchestrator.create_task(
                principal(),
                [UploadFile(file=BytesIO(b"data"), filename="file.docx")],
                "Bearer token",
                "request-1",
            )
            assert result.status.value == "completed"
            assert result.report is not None
            assert result.report.warnings == ["parser_warning"]
            assert repository.audit_events[0]["action"] == "ingestion_upload"

    asyncio.run(run())
    assert repository.transitions == ["pending", "processing", "completed"]
    assert calls[1:] == [
        f"/ingestion/tasks/{repository.task.id}/normalize",
        "/v1/documents/extract",
        "/v1/documents/index",
        "/internal/v1/events",
    ]


def test_ingestion_complete_notification_payload() -> None:
    repository = FakeRepository()
    notification_calls: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/sources"):
            return httpx.Response(201, json=report_payload())
        if request.url.path.endswith("/normalize"):
            return httpx.Response(
                200,
                json={"documents": [document_payload()], "warnings": []},
            )
        if request.url.path == "/v1/documents/extract":
            return httpx.Response(
                200,
                json={
                    "document_id": "document-1",
                    "extraction": {
                        "confirmed": [{"id": "c1", "kind": "claim", "value": "nickel"}],
                        "candidates": [],
                    },
                    "graph_write": {
                        "backend": "neo4j",
                        "mode": "live",
                        "document_ids": ["document-1"],
                        "records_count": 2,
                        "confirmed_count": 1,
                        "claim_ids": [],
                        "graph_entity_ids": [],
                        "warnings": [],
                    },
                    "warnings": [],
                },
            )
        if request.url.path == "/v1/documents/index":
            return httpx.Response(
                200,
                json={
                    "vector_write": {
                        "backend": "qdrant",
                        "mode": "live",
                        "document_ids": ["document-1"],
                        "records_count": 3,
                        "confirmed_count": 0,
                        "claim_ids": [],
                        "graph_entity_ids": [],
                        "warnings": [],
                    },
                    "warnings": [],
                },
            )
        if request.url.path == "/internal/v1/events":
            notification_calls.append(
                {
                    "kind": "event",
                    "json": json.loads(request.content.decode()),
                    "token": request.headers.get("X-Internal-Service-Token"),
                }
            )
            return httpx.Response(
                200,
                json={
                    "id": str(uuid4()),
                    "title": "Документ обработан",
                    "reason": "test",
                    "type": "ingestion_complete",
                    "reference_id": str(repository.task.id),
                    "reference_type": "ingestion_task",
                    "read": False,
                    "match_reason": "",
                    "created_at": datetime.now(UTC).isoformat(),
                },
            )
        if request.url.path == "/internal/v1/match":
            notification_calls.append(
                {
                    "kind": "match",
                    "json": json.loads(request.content.decode()),
                    "token": request.headers.get("X-Internal-Service-Token"),
                }
            )
            return httpx.Response(
                200,
                json=[
                    {
                        "id": str(uuid4()),
                        "title": "Новый документ по интересам",
                        "reason": "Совпадение с подпиской: materials",
                        "type": "interest_match",
                        "reference_id": "document-1",
                        "reference_type": "document",
                        "read": False,
                        "match_score": 0.81,
                        "match_reason": "никель",
                        "created_at": datetime.now(UTC).isoformat(),
                    }
                ],
            )
        return httpx.Response(404, json={"code": "not_found", "message": "unexpected"})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            user = principal()
            orchestrator = service(repository, client)
            await orchestrator.create_task(
                user,
                [UploadFile(file=BytesIO(b"data"), filename="file.docx")],
                "Bearer token",
                "request-1",
            )

    asyncio.run(run())
    event_calls = [item for item in notification_calls if item["kind"] == "event"]
    match_calls = [item for item in notification_calls if item["kind"] == "match"]
    assert len(event_calls) == 1
    payload = event_calls[0]["json"]
    assert payload["type"] == "ingestion_complete"
    assert payload["user_id"] == str(repository.task.user_id)
    assert payload["reference_id"] == str(repository.task.id)
    assert payload["reference_type"] == "ingestion_task"
    assert "Обработано документов: 1" in payload["message"]
    assert "Извлечено сущностей: 1" in payload["message"]
    assert "Проиндексировано фрагментов: 3" in payload["message"]
    assert event_calls[0]["token"] == "test-internal-token"
    assert len(match_calls) == 1
    match_payload = match_calls[0]["json"]
    assert match_payload["user_id"] == str(repository.task.user_id)
    assert match_payload["document_id"] == "document-1"
    assert len(match_payload["artifacts"]) == 1
    assert match_payload["artifacts"][0]["id"] == "c1"
    assert match_calls[0]["token"] == "test-internal-token"


def test_ingestion_skips_interest_match_without_artifacts() -> None:
    repository = FakeRepository()
    notification_calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/sources"):
            return httpx.Response(201, json=report_payload())
        if request.url.path.endswith("/normalize"):
            return httpx.Response(
                200,
                json={"documents": [document_payload()], "warnings": []},
            )
        if request.url.path == "/v1/documents/extract":
            return httpx.Response(
                200,
                json={
                    "document_id": "document-1",
                    "extraction": {"confirmed": [], "candidates": []},
                    "graph_write": {
                        "backend": "neo4j",
                        "mode": "live",
                        "document_ids": ["document-1"],
                        "records_count": 0,
                        "confirmed_count": 0,
                        "claim_ids": [],
                        "graph_entity_ids": [],
                        "warnings": [],
                    },
                    "warnings": [],
                },
            )
        if request.url.path == "/v1/documents/index":
            return httpx.Response(
                200,
                json={
                    "vector_write": {
                        "backend": "qdrant",
                        "mode": "live",
                        "document_ids": ["document-1"],
                        "records_count": 1,
                        "confirmed_count": 0,
                        "claim_ids": [],
                        "graph_entity_ids": [],
                        "warnings": [],
                    },
                    "warnings": [],
                },
            )
        if request.url.path == "/internal/v1/events":
            return httpx.Response(200, json={"id": str(uuid4()), "type": "ingestion_complete"})
        if request.url.path == "/internal/v1/match":
            notification_calls.append(request.url.path)
            return httpx.Response(200, json=[])
        return httpx.Response(404, json={"code": "not_found", "message": "unexpected"})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await service(repository, client).create_task(
                principal(),
                [UploadFile(file=BytesIO(b"data"), filename="file.docx")],
                "Bearer token",
                "request-1",
            )

    asyncio.run(run())
    assert notification_calls == []


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
            orchestrator = service(repository, client)
            with pytest.raises(OrchestratorServiceError):
                await orchestrator.create_task(
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
            service = IngestionService(
                repository=repository,
                client=client,
                enforce_active_dictionary=False,
            )
            with pytest.raises(OrchestratorServiceError) as error:
                await service.create_task(
                    principal(),
                    [UploadFile(file=BytesIO(b"data"), filename="file.bin")],
                    "Bearer token",
                    "request-1",
                )
            assert error.value.code == "normalization_empty"

    asyncio.run(run())
    assert repository.transitions == ["pending", "processing", "failed"]


def test_mock_storage_adapter_marks_task_failed() -> None:
    repository = FakeRepository()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/sources"):
            return httpx.Response(201, json=report_payload())
        if request.url.path.endswith("/normalize"):
            return httpx.Response(
                200,
                json={"documents": [document_payload()], "warnings": []},
            )
        return httpx.Response(
            200,
            json={
                "document_id": "document-1",
                "extraction": {},
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

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(OrchestratorServiceError) as error:
                await service(repository, client).create_task(
                    principal(),
                    [UploadFile(file=BytesIO(b"data"), filename="file.docx")],
                    "Bearer token",
                    "request-1",
                )
            assert error.value.code == "storage_adapter_not_ready"

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
            admin = principal(UserRole.ADMIN)
            assert (await orchestrator.get_task(task.id, admin)).id == task.id
            with pytest.raises(OrchestratorServiceError) as error:
                await orchestrator.get_task(task.id, principal())
            assert error.value.status_code == 404

    asyncio.run(run())
