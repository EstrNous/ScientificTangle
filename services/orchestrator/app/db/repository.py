from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import IngestionTask
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
