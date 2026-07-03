from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import IngestionStatus, IngestionTask, QueryRun, QueryRunStatus


@dataclass(frozen=True, slots=True)
class IngestionTaskData:
    user_id: UUID
    status: IngestionStatus = IngestionStatus.PENDING


@dataclass(frozen=True, slots=True)
class QueryRunData:
    user_id: UUID
    status: QueryRunStatus = QueryRunStatus.PENDING
    query_ir: dict | None = None


class OrchestratorRepository(Protocol):
    async def create_ingestion_task(self, data: IngestionTaskData) -> IngestionTask: ...

    async def get_ingestion_task(self, task_id: UUID) -> IngestionTask | None: ...

    async def update_ingestion_status(self, task_id: UUID, status: IngestionStatus,
                                      report: dict | None = None) -> IngestionTask | None: ...

    async def create_query_run(self, data: QueryRunData) -> QueryRun: ...

    async def update_query_run(self, run_id: UUID, status: QueryRunStatus, trace: dict | None = None,
                               latency: int | None = None) -> QueryRun | None: ...


class SqlAlchemyOrchestratorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- Ingestion Task Methods ---
    async def create_ingestion_task(self, data: IngestionTaskData) -> IngestionTask:
        task = IngestionTask(user_id=data.user_id, status=data.status.value)
        self._session.add(task)
        await self._session.commit()
        await self._session.refresh(task)
        return task

    async def get_ingestion_task(self, task_id: UUID) -> IngestionTask | None:
        return await self._session.get(IngestionTask, task_id)

    async def update_ingestion_status(self, task_id: UUID, status: IngestionStatus,
                                      report: dict | None = None) -> IngestionTask | None:
        task = await self._session.get(IngestionTask, task_id)
        if not task:
            return None
        task.status = status.value
        if report:
            task.report = report
        await self._session.commit()
        await self._session.refresh(task)
        return task

    # --- Query Run Methods ---
    async def create_query_run(self, data: QueryRunData) -> QueryRun:
        run = QueryRun(user_id=data.user_id, status=data.status.value, query_ir=data.query_ir)
        self._session.add(run)
        await self._session.commit()
        await self._session.refresh(run)
        return run

    async def update_query_run(self, run_id: UUID, status: QueryRunStatus, trace: dict | None = None,
                               latency: int | None = None) -> QueryRun | None:
        run = await self._session.get(QueryRun, run_id)
        if not run:
            return None
        run.status = status.value
        if trace:
            run.retrieval_trace = trace
        if latency:
            run.latency_ms = latency
        await self._session.commit()
        await self._session.refresh(run)
        return run