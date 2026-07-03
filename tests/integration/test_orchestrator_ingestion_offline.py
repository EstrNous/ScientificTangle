import asyncio
import importlib
import sys
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from fastapi import UploadFile

from shared.contracts import IngestionReport, UserRole
from shared.security import AuthenticatedPrincipal


class FakeRepository:
    def __init__(self) -> None:
        self.task = None
        self.transitions: list[str] = []
        self.audit_events: list[dict[str, object]] = []

    async def create(self, user_id: UUID):
        now = datetime.now(UTC)
        from infra.postgres.orchestrator_db import IngestionTask

        self.task = IngestionTask(
            id=uuid4(),
            user_id=user_id,
            status="pending",
            created_at=now,
            updated_at=now,
        )
        self.transitions.append("pending")
        return self.task

    async def get(self, task_id: UUID):
        if self.task is not None and self.task.id == task_id:
            return self.task
        return None

    async def mark_processing(self, task, report: IngestionReport):
        task.status = "processing"
        task.report = report.model_dump(mode="json")
        self.transitions.append("processing")
        return task

    async def mark_completed(self, task, report: IngestionReport):
        task.status = "completed"
        task.report = report.model_dump(mode="json")
        self.transitions.append("completed")
        return task

    async def mark_failed(self, task, message: str):
        task.status = "failed"
        task.error_message = message
        self.transitions.append("failed")
        return task

    async def record_audit_event(self, user_id, action, resource_type, resource_id, details, request_id):
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


def principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(user_id=uuid4(), role=UserRole.RESEARCHER, token_id=uuid4())


def report_payload() -> dict:
    return {
        "sources": [
            {
                "object_key": "uploads/u/task/file.docx",
                "original_filename": "file.docx",
                "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "size_bytes": 4,
                "sha256": "a" * 64,
            }
        ],
        "warnings": [],
        "normalized_documents": [],
        "documents_count": 0,
        "source_spans_count": 0,
        "tables_count": 0,
        "indexed_points_count": 0,
        "extracted_claims_count": 0,
        "candidates_count": 0,
    }


def test_orchestrator_ingestion_pipeline_offline() -> None:
    orchestrator_root = Path(__file__).resolve().parents[2] / "services" / "orchestrator"
    sys.path.insert(0, str(orchestrator_root))
    for module_name in [name for name in sys.modules if name == "app" or name.startswith("app.")]:
        sys.modules.pop(module_name, None)
    importlib.invalidate_caches()
    from app.service.service import OrchestratorService

    repository = FakeRepository()
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path.endswith("/sources"):
            return httpx.Response(201, json=report_payload())
        if request.url.path.endswith("/normalize"):
            return httpx.Response(
                200,
                json={
                    "documents": [
                        {
                            "id": "document-1",
                            "source_type": "docx",
                            "title": "T",
                            "content": "Ni",
                            "source_spans": [],
                            "table_blocks": [],
                        }
                    ],
                    "warnings": [],
                },
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
                        "warnings": [],
                    },
                    "warnings": [],
                },
            )
        return httpx.Response(
            200,
            json={
                "vector_write": {
                    "backend": "qdrant",
                    "mode": "live",
                    "document_ids": ["document-1"],
                    "records_count": 1,
                    "warnings": [],
                },
                "warnings": [],
            },
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = OrchestratorService(
                repository,
                client,
                "http://ingestion",
                "http://knowledge",
                "http://retrieval",
                "http://model",
            )
            result = await service.create_task(
                principal(),
                [UploadFile(file=BytesIO(b"data"), filename="file.docx")],
                "Bearer token",
                "request-1",
            )
            assert result.status.value == "completed"
            assert result.report is not None
            assert result.report.indexed_points_count == 1

    asyncio.run(run())
    assert "/v1/documents/index" in calls
