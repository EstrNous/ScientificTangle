import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.contracts import (
    AnswerPayload,
    EvidenceBundle,
    ExportPayload,
    GraphSubgraph,
    IngestionReport,
    DictionaryIngestionReport,
    IngestionTaskStatus,
    QueryIR,
    QueryRunStatus,
    TaskKind,
)

from .models import ExportJob, ExportJobStatus, IngestionTask, QueryRun, QueryRunStatus


class IngestionTaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        user_id: UUID,
        task_kind: TaskKind = TaskKind.DOCUMENT_INGESTION,
        dictionary_version_id: UUID | None = None,
    ) -> IngestionTask:
        task = IngestionTask(
            user_id=user_id,
            status=IngestionTaskStatus.PENDING.value,
            task_kind=task_kind.value,
            dictionary_version_id=dictionary_version_id,
        )
        self._session.add(task)
        await self._session.commit()
        await self._session.refresh(task)
        return task

    async def get(self, task_id: UUID) -> IngestionTask | None:
        return await self._session.get(IngestionTask, task_id)

    async def set_report(
        self, task: IngestionTask, report: IngestionReport | DictionaryIngestionReport
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
        report: IngestionReport | DictionaryIngestionReport,
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
        report: IngestionReport | DictionaryIngestionReport,
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

    async def list_audit_events(
        self,
        limit: int = 200,
        offset: int = 0,
        action: str | None = None,
        user_id: UUID | None = None,
    ) -> list[dict]:
        return await self._list_audit_events(
            limit=limit,
            offset=offset,
            action=action,
            user_id=user_id,
        )

    async def _list_audit_events(
        self,
        limit: int = 200,
        offset: int = 0,
        action: str | None = None,
        user_id: UUID | None = None,
    ) -> list[dict]:
        clauses: list[str] = []
        params: dict[str, object] = {"limit": limit, "offset": offset}
        if action is not None:
            clauses.append("action = :action")
            params["action"] = action
        if user_id is not None:
            clauses.append("user_id = :user_id")
            params["user_id"] = user_id
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        result = await self._session.execute(
            text(
                f"""
                SELECT id, user_id, action, resource_type, resource_id, details, request_id, created_at
                FROM audit_events
                {where}
                ORDER BY created_at DESC
                LIMIT :limit
                OFFSET :offset
                """
            ),
            params,
        )
        rows = result.mappings().all()
        return [dict(row) for row in rows]

    async def _save(self, task: IngestionTask) -> None:
        await self._session.commit()
        await self._session.refresh(task)


class QueryRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        user_id: UUID,
        question: str,
        request_id: str,
        dictionary_version_id: UUID | None = None,
    ) -> QueryRun:
        run = QueryRun(
            user_id=user_id,
            raw_question=question,
            request_id=request_id,
            status=QueryRunStatus.PENDING.value,
            warnings=[],
            graph_subgraph=GraphSubgraph().model_dump(mode="json"),
            dictionary_version_id=dictionary_version_id,
        )
        self._session.add(run)
        await self._save(run)
        return run

    async def get(self, run_id: UUID) -> QueryRun | None:
        return await self._session.get(QueryRun, run_id)

    async def create_export_job(
        self,
        user_id: UUID,
        query_run_id: UUID,
        export_format: str,
    ) -> ExportJob:
        job = ExportJob(
            user_id=user_id,
            query_run_id=query_run_id,
            format=export_format,
            status=ExportJobStatus.PENDING.value,
        )
        self._session.add(job)
        await self._save_export_job(job)
        return job

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

    async def mark_export_processing(self, job: ExportJob) -> ExportJob:
        job.status = ExportJobStatus.PROCESSING.value
        job.updated_at = datetime.now(UTC)
        await self._save_export_job(job)
        return job

    async def mark_export_completed(
        self,
        job: ExportJob,
        payload: ExportPayload,
        file_url: str,
    ) -> ExportJob:
        job.status = ExportJobStatus.COMPLETED.value
        job.file_url = file_url
        job.payload = payload.model_dump(mode="json")
        job.error_message = None
        job.updated_at = datetime.now(UTC)
        await self._save_export_job(job)
        return job

    async def mark_export_failed(self, job: ExportJob, message: str) -> ExportJob:
        job.status = ExportJobStatus.FAILED.value
        job.error_message = message
        job.updated_at = datetime.now(UTC)
        await self._save_export_job(job)
        return job

    async def _save(self, run: QueryRun) -> None:
        await self._session.commit()
        await self._session.refresh(run)

    async def _save_export_job(self, job: ExportJob) -> None:
        await self._session.commit()
        await self._session.refresh(job)

    async def list_audit_events(
        self,
        limit: int = 200,
        offset: int = 0,
        action: str | None = None,
        user_id: UUID | None = None,
    ) -> list[dict]:
        clauses: list[str] = []
        params: dict[str, object] = {"limit": limit, "offset": offset}
        if action is not None:
            clauses.append("action = :action")
            params["action"] = action
        if user_id is not None:
            clauses.append("user_id = :user_id")
            params["user_id"] = user_id
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        result = await self._session.execute(
            text(
                f"""
                SELECT id, user_id, action, resource_type, resource_id, details, request_id, created_at
                FROM audit_events
                {where}
                ORDER BY created_at DESC
                LIMIT :limit
                OFFSET :offset
                """
            ),
            params,
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
