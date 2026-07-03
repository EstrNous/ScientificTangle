from dataclasses import dataclass
from typing import Protocol
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from .models import ExportJob

@dataclass(frozen=True, slots=True)
class ExportJobData:
    user_id: UUID
    format: str
    status: str = 'pending'

class ExportRepository(Protocol):
    async def create_job(self, data: ExportJobData) -> ExportJob: ...
    async def get_job(self, job_id: UUID) -> ExportJob | None: ...
    async def update_job_url(self, job_id: UUID, file_url: str, status: str = 'completed') -> ExportJob | None: ...

class SqlAlchemyExportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_job(self, data: ExportJobData) -> ExportJob:
        job = ExportJob(user_id=data.user_id, format=data.format, status=data.status)
        self._session.add(job)
        await self._session.commit()
        await self._session.refresh(job)
        return job

    async def get_job(self, job_id: UUID) -> ExportJob | None:
        return await self._session.get(ExportJob, job_id)

    async def update_job_url(self, job_id: UUID, file_url: str, status: str = 'completed') -> ExportJob | None:
        job = await self._session.get(ExportJob, job_id)
        if not job:
            return None
        job.file_url = file_url
        job.status = status
        await self._session.commit()
        await self._session.refresh(job)
        return job