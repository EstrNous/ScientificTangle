import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .models import IngestionTask, QueryRun, QueryRunStatus
from shared.contracts import IngestionReport, IngestionTaskStatus


class IngestionTaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user_id: UUID) -> IngestionTask:
        task = IngestionTask(user_id=user_id, status=IngestionTaskStatus.PENDING.value)
        self._session.add(task)
        await self._session.commit()
        await self._session.refresh(task)
        return task

    async def get(self, task_id: UUID) -> IngestionTask | None:
        return await self._session.get(IngestionTask, task_id)

    async def set_report(
        self, task: IngestionTask, report: IngestionReport
    ) -> IngestionTask:
        task.status = IngestionTaskStatus.COMPLETED.value
        task.report = report.model_dump(mode="json")
        task.error_message = None
        task.updated_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(task)
        return task

    async def mark_processing(
        self,
        task: IngestionTask,
        report: IngestionReport,
    ) -> IngestionTask:
        task.status = IngestionTaskStatus.PROCESSING.value
        task.report = report.model_dump(mode="json")
        task.error_message = None
        task.updated_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(task)
        return task

    async def mark_completed(
        self,
        task: IngestionTask,
        report: IngestionReport,
    ) -> IngestionTask:
        task.status = IngestionTaskStatus.COMPLETED.value
        task.report = report.model_dump(mode="json")
        task.error_message = None
        task.updated_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(task)
        return task

    async def mark_failed(self, task: IngestionTask, message: str) -> IngestionTask:
        task.status = IngestionTaskStatus.FAILED.value
        task.error_message = message
        task.updated_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(task)
        return task

    async def create_query_run(self, user_id: UUID, raw_query: str) -> QueryRun:
        run = QueryRun(
            user_id=user_id,
            raw_query=raw_query,
            status=QueryRunStatus.PROCESSING.value,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self._session.add(run)
        await self._session.commit()
        await self._session.refresh(run)
        return run

    async def complete_query_run(
        self,
        run: QueryRun,
        query_ir: dict,
        retrieval_trace: dict,
        answer_payload: dict,
        latency_ms: int,
    ) -> QueryRun:
        run.status = QueryRunStatus.COMPLETED.value
        run.query_ir = query_ir
        run.retrieval_trace = retrieval_trace
        run.answer_payload = answer_payload
        run.latency_ms = latency_ms
        run.error_message = None
        run.updated_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(run)
        return run

    async def fail_query_run(self, run: QueryRun, message: str, latency_ms: int) -> QueryRun:
        run.status = QueryRunStatus.FAILED.value
        run.error_message = message
        run.latency_ms = latency_ms
        run.updated_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(run)
        return run

    async def record_audit_event(
        self,
        user_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict,
        request_id: str,
    ) -> None:
        await self._session.execute(
            text(
                """
                INSERT INTO audit_events (id, user_id, action, resource_type, resource_id, details, request_id)
                VALUES (:id, :user_id, :action, :resource_type, :resource_id, CAST(:details AS jsonb), :request_id)
                """
            ),
            {
                "id": uuid4(),
                "user_id": user_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": json.dumps(details, ensure_ascii=False),
                "request_id": request_id,
            },
        )
        await self._session.commit()
