import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.contracts import (
    AnswerPayload,
    EvidenceBundle,
    GraphSubgraph,
    IngestionReport,
    IngestionTaskStatus,
    QueryIR,
    QueryRunStatus,
)

from .models import IngestionTask, QueryRun, QueryRunStatus


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
        await self._save(task)
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
        await self._save(task)
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
        await self._save(task)
        return task

    async def mark_failed(self, task: IngestionTask, message: str) -> IngestionTask:
        task.status = IngestionTaskStatus.FAILED.value
        task.error_message = message
        task.updated_at = datetime.now(UTC)
        await self._save(task)
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

    async def list_audit_events(self, limit: int = 200) -> list[dict]:
        result = await self._session.execute(
            text(
                """
                SELECT id, user_id, action, resource_type, resource_id, details, request_id, created_at
                FROM audit_events
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        )
        rows = result.mappings().all()
        return [dict(row) for row in rows]

    async def _save(self, task: IngestionTask) -> None:
        await self._session.commit()
        await self._session.refresh(task)


class QueryRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user_id: UUID, question: str, request_id: str) -> QueryRun:
        run = QueryRun(
            user_id=user_id,
            raw_question=question,
            request_id=request_id,
            status=QueryRunStatus.PENDING.value,
            warnings=[],
            graph_subgraph=GraphSubgraph().model_dump(mode="json"),
        )
        self._session.add(run)
        await self._save(run)
        return run

    async def get(self, run_id: UUID) -> QueryRun | None:
        return await self._session.get(QueryRun, run_id)

    async def mark_processing(self, run: QueryRun) -> QueryRun:
        run.status = QueryRunStatus.PROCESSING.value
        run.updated_at = datetime.now(UTC)
        await self._save(run)
        return run

    async def mark_completed(
        self,
        run: QueryRun,
        query_ir: QueryIR,
        evidence_bundle: EvidenceBundle,
        answer: AnswerPayload,
        graph_subgraph: GraphSubgraph,
        retrieval_trace: dict,
        warnings: list[str],
        latency_ms: int,
    ) -> QueryRun:
        run.status = QueryRunStatus.COMPLETED.value
        run.query_ir = query_ir.model_dump(mode="json")
        run.evidence_bundle = evidence_bundle.model_dump(mode="json")
        run.answer = answer.model_dump(mode="json")
        run.graph_subgraph = graph_subgraph.model_dump(mode="json")
        run.retrieval_trace = retrieval_trace
        run.warnings = warnings
        run.error_code = None
        run.error_message = None
        run.latency_ms = latency_ms
        run.updated_at = datetime.now(UTC)
        await self._save(run)
        return run

    async def mark_failed(
        self,
        run: QueryRun,
        code: str,
        message: str,
        latency_ms: int,
    ) -> QueryRun:
        run.status = QueryRunStatus.FAILED.value
        run.error_code = code
        run.error_message = message
        run.latency_ms = latency_ms
        run.updated_at = datetime.now(UTC)
        await self._save(run)
        return run

    async def _save(self, run: QueryRun) -> None:
        await self._session.commit()
        await self._session.refresh(run)

    async def list_audit_events(self, limit: int = 200) -> list[dict]:
        result = await self._session.execute(
            text(
                """
                SELECT id, user_id, action, resource_type, resource_id, details, request_id, created_at
                FROM audit_events
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        )
        rows = result.mappings().all()
        return [dict(row) for row in rows]

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
