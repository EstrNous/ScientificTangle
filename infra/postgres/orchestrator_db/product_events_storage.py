from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Select, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from infra.postgres.common.cursor import CursorPage, decode_cursor, encode_cursor

from .models import (
    EXPORTS_BUCKET_NAME,
    AuditCsvExport,
    AuditCsvExportStatus,
    AuditEvent,
    ExportArtifact,
    ExportJob,
    ExportJobStatus,
)

PRODUCT_AUDIT_ACTIONS = frozenset(
    {
        "query_created",
        "answer_generated",
        "source_opened",
        "document_uploaded",
        "document_deleted",
        "document_exported",
        "review_decision",
        "access_denied",
        "admin_setting_changed",
        "source_viewed",
        "search",
    }
)

DEFAULT_EXPORT_ARTIFACT_RETENTION_DAYS = 30
DEFAULT_AUDIT_CSV_RETENTION_DAYS = 7
DEFAULT_NOTIFICATION_RETENTION_DAYS = 90

AUDIT_CSV_COLUMNS = (
    "id",
    "created_at",
    "user_id",
    "action",
    "resource_type",
    "resource_id",
    "request_id",
    "details",
)


@dataclass(frozen=True, slots=True)
class ExportArtifactInput:
    artifact_kind: str
    storage_key: str
    content_type: str
    byte_size: int | None = None
    bucket_name: str = EXPORTS_BUCKET_NAME
    file_url: str | None = None
    checksum: str | None = None
    retention_days: int = DEFAULT_EXPORT_ARTIFACT_RETENTION_DAYS


class ProductEventsStorageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_export_job(
        self,
        *,
        user_id: UUID,
        query_run_id: UUID,
        export_format: str,
    ) -> ExportJob:
        job = ExportJob(
            id=uuid4(),
            user_id=user_id,
            query_run_id=query_run_id,
            format=export_format,
            status=ExportJobStatus.PENDING.value,
        )
        self._session.add(job)
        await self._session.commit()
        await self._session.refresh(job)
        return job

    async def attach_export_artifacts(
        self,
        export_job_id: UUID,
        artifacts: list[ExportArtifactInput],
        *,
        mark_completed: bool = True,
    ) -> list[ExportArtifact]:
        async with self._session.begin():
            job = await self._session.get(ExportJob, export_job_id)
            if job is None:
                raise KeyError(str(export_job_id))
            rows: list[ExportArtifact] = []
            now = datetime.now(UTC)
            for item in artifacts:
                expires_at = now + timedelta(days=item.retention_days)
                row = ExportArtifact(
                    id=uuid4(),
                    export_job_id=export_job_id,
                    artifact_kind=item.artifact_kind,
                    bucket_name=item.bucket_name,
                    storage_key=item.storage_key,
                    file_url=item.file_url,
                    content_type=item.content_type,
                    byte_size=item.byte_size,
                    expires_at=expires_at,
                    checksum=item.checksum,
                )
                self._session.add(row)
                rows.append(row)
            if mark_completed:
                job.status = ExportJobStatus.COMPLETED.value
                job.completed_at = now
                job.updated_at = now
                if rows and rows[0].file_url:
                    job.file_url = rows[0].file_url
        for row in rows:
            await self._session.refresh(row)
        return rows

    async def get_export_job_with_artifacts(self, export_job_id: UUID) -> ExportJob | None:
        result = await self._session.scalar(
            select(ExportJob)
            .where(ExportJob.id == export_job_id)
            .options(selectinload(ExportJob.artifacts))
        )
        return result

    async def list_export_jobs_cursor(
        self,
        user_id: UUID,
        *,
        limit: int = 20,
        cursor: str | None = None,
        status: str | None = None,
    ) -> CursorPage:
        query: Select[tuple[ExportJob]] = select(ExportJob).where(ExportJob.user_id == user_id)
        if status is not None:
            query = query.where(ExportJob.status == status)
        if cursor is not None:
            cursor_created_at, cursor_id = decode_cursor(cursor)
            query = query.where(
                tuple_(ExportJob.created_at, ExportJob.id) < tuple_(cursor_created_at, cursor_id)
            )
        query = query.order_by(ExportJob.created_at.desc(), ExportJob.id.desc()).limit(limit + 1)
        result = await self._session.execute(query)
        rows = list(result.scalars().all())
        next_cursor = None
        if len(rows) > limit:
            last = rows[limit - 1]
            next_cursor = encode_cursor(last.created_at, last.id)
            rows = rows[:limit]
        return CursorPage(items=rows, next_cursor=next_cursor)

    async def list_audit_events_cursor(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
        action: str | None = None,
        user_id: UUID | None = None,
        resource_type: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
    ) -> CursorPage:
        query: Select[tuple[AuditEvent]] = select(AuditEvent)
        if action is not None:
            query = query.where(AuditEvent.action == action)
        if user_id is not None:
            query = query.where(AuditEvent.user_id == user_id)
        if resource_type is not None:
            query = query.where(AuditEvent.resource_type == resource_type)
        if created_after is not None:
            query = query.where(AuditEvent.created_at >= created_after)
        if created_before is not None:
            query = query.where(AuditEvent.created_at <= created_before)
        if cursor is not None:
            cursor_created_at, cursor_id = decode_cursor(cursor)
            query = query.where(
                tuple_(AuditEvent.created_at, AuditEvent.id) < tuple_(cursor_created_at, cursor_id)
            )
        query = query.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(limit + 1)
        result = await self._session.execute(query)
        rows = list(result.scalars().all())
        next_cursor = None
        if len(rows) > limit:
            last = rows[limit - 1]
            next_cursor = encode_cursor(last.created_at, last.id)
            rows = rows[:limit]
        return CursorPage(items=rows, next_cursor=next_cursor)

    async def create_audit_csv_export(
        self,
        *,
        user_id: UUID,
        filter_params: dict[str, Any],
        retention_days: int = DEFAULT_AUDIT_CSV_RETENTION_DAYS,
    ) -> AuditCsvExport:
        row = AuditCsvExport(
            id=uuid4(),
            user_id=user_id,
            status=AuditCsvExportStatus.PENDING.value,
            filter_params=filter_params,
            bucket_name=EXPORTS_BUCKET_NAME,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        _ = retention_days
        return row

    async def complete_audit_csv_export(
        self,
        export_id: UUID,
        *,
        storage_key: str,
        row_count: int,
        csv_text: str | None = None,
    ) -> AuditCsvExport:
        async with self._session.begin():
            row = await self._session.get(AuditCsvExport, export_id)
            if row is None:
                raise KeyError(str(export_id))
            row.status = AuditCsvExportStatus.COMPLETED.value
            row.storage_key = storage_key
            row.row_count = row_count
            row.completed_at = datetime.now(UTC)
            if csv_text is not None:
                _ = csv_text
        await self._session.refresh(row)
        return row

    async def list_audit_csv_exports(
        self,
        user_id: UUID,
        *,
        limit: int = 20,
        cursor: str | None = None,
    ) -> CursorPage:
        query: Select[tuple[AuditCsvExport]] = select(AuditCsvExport).where(
            AuditCsvExport.user_id == user_id
        )
        if cursor is not None:
            cursor_created_at, cursor_id = decode_cursor(cursor)
            query = query.where(
                tuple_(AuditCsvExport.created_at, AuditCsvExport.id)
                < tuple_(cursor_created_at, cursor_id)
            )
        query = (
            query.order_by(AuditCsvExport.created_at.desc(), AuditCsvExport.id.desc()).limit(limit + 1)
        )
        result = await self._session.execute(query)
        rows = list(result.scalars().all())
        next_cursor = None
        if len(rows) > limit:
            last = rows[limit - 1]
            next_cursor = encode_cursor(last.created_at, last.id)
            rows = rows[:limit]
        return CursorPage(items=rows, next_cursor=next_cursor)

    def audit_events_to_csv(self, events: list[AuditEvent]) -> str:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=AUDIT_CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for event in events:
            writer.writerow(self.audit_event_to_csv_row(event))
        return buffer.getvalue()

    def audit_event_to_csv_row(self, event: AuditEvent) -> dict[str, str]:
        return {
            "id": str(event.id),
            "created_at": event.created_at.astimezone(UTC).isoformat(),
            "user_id": str(event.user_id) if event.user_id is not None else "",
            "action": event.action,
            "resource_type": event.resource_type or "",
            "resource_id": event.resource_id or "",
            "request_id": event.request_id or "",
            "details": _serialize_details(event.details),
        }

    def export_artifact_to_dict(self, artifact: ExportArtifact) -> dict[str, Any]:
        return {
            "id": artifact.id,
            "export_job_id": artifact.export_job_id,
            "artifact_kind": artifact.artifact_kind,
            "bucket_name": artifact.bucket_name,
            "storage_key": artifact.storage_key,
            "file_url": artifact.file_url,
            "content_type": artifact.content_type,
            "byte_size": artifact.byte_size,
            "expires_at": artifact.expires_at,
            "checksum": artifact.checksum,
            "created_at": artifact.created_at,
        }

    def audit_csv_export_to_dict(self, row: AuditCsvExport) -> dict[str, Any]:
        return {
            "id": row.id,
            "user_id": row.user_id,
            "status": row.status,
            "filter_params": row.filter_params,
            "bucket_name": row.bucket_name,
            "storage_key": row.storage_key,
            "row_count": row.row_count,
            "content_type": row.content_type,
            "error_message": row.error_message,
            "created_at": row.created_at,
            "completed_at": row.completed_at,
        }


def _serialize_details(details: dict[str, Any]) -> str:
    import json

    return json.dumps(details, ensure_ascii=False, sort_keys=True)
