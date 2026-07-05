from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Select, delete, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from infra.postgres.common.cursor import CursorPage, decode_cursor, encode_cursor

from .access_audit import (
    build_access_denied_details,
    build_export_audit_details,
    build_search_audit_details,
    build_source_viewed_details,
)

from .models import (
    AuditEvent,
    CascadeStatus,
    DocumentCascadeRefs,
    DocumentDeletionStatus,
    IndexedDocument,
    ReviewDecision,
    ReviewDecisionStatus,
)


class WorkflowStorageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_audit_events_cursor(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
        action: str | None = None,
        user_id: UUID | None = None,
    ) -> CursorPage:
        query: Select[tuple[AuditEvent]] = select(AuditEvent)
        if action is not None:
            query = query.where(AuditEvent.action == action)
        if user_id is not None:
            query = query.where(AuditEvent.user_id == user_id)
        if cursor is not None:
            cursor_created_at, cursor_id = decode_cursor(cursor)
            query = query.where(
                tuple_(AuditEvent.created_at, AuditEvent.id)
                < tuple_(cursor_created_at, cursor_id)
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

    async def record_audit_event(
        self,
        *,
        user_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict,
        request_id: str,
        commit: bool = True,
    ) -> AuditEvent:
        event = AuditEvent(
            id=uuid4(),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            request_id=request_id,
        )
        self._session.add(event)
        if commit:
            await self._session.commit()
            await self._session.refresh(event)
        else:
            await self._session.flush()
        return event

    async def apply_review_decision_with_audit(
        self,
        *,
        candidate_id: str,
        candidate_type: str,
        status: ReviewDecisionStatus,
        reviewer_user_id: UUID,
        request_id: str,
        document_id: str | None = None,
        source_span_id: str | None = None,
        claim_id: str | None = None,
        comment: str | None = None,
    ) -> ReviewDecision:
        async with self._session.begin():
            decision = await self._upsert_review_decision(
                candidate_id=candidate_id,
                candidate_type=candidate_type,
                status=status,
                reviewer_user_id=reviewer_user_id,
                document_id=document_id,
                source_span_id=source_span_id,
                claim_id=claim_id,
                comment=comment,
            )
            await self.record_audit_event(
                user_id=reviewer_user_id,
                action="review_decision",
                resource_type="review_candidate",
                resource_id=candidate_id,
                details={
                    "candidate_type": candidate_type,
                    "status": status.value,
                    "document_id": document_id,
                    "source_span_id": source_span_id,
                    "claim_id": claim_id,
                    "comment": comment,
                },
                request_id=request_id,
                commit=False,
            )
        await self._session.refresh(decision)
        return decision

    async def _upsert_review_decision(
        self,
        *,
        candidate_id: str,
        candidate_type: str,
        status: ReviewDecisionStatus,
        reviewer_user_id: UUID | None = None,
        document_id: str | None = None,
        source_span_id: str | None = None,
        claim_id: str | None = None,
        comment: str | None = None,
    ) -> ReviewDecision:
        existing = await self._session.scalar(
            select(ReviewDecision).where(
                ReviewDecision.candidate_id == candidate_id,
                ReviewDecision.candidate_type == candidate_type,
            )
        )
        decided_at = datetime.now(UTC) if status != ReviewDecisionStatus.PENDING else None
        if existing is None:
            decision = ReviewDecision(
                id=uuid4(),
                candidate_id=candidate_id,
                candidate_type=candidate_type,
                status=status.value,
                reviewer_user_id=reviewer_user_id,
                document_id=document_id,
                source_span_id=source_span_id,
                claim_id=claim_id,
                comment=comment,
                decided_at=decided_at,
            )
            self._session.add(decision)
        else:
            existing.status = status.value
            existing.reviewer_user_id = reviewer_user_id
            if document_id is not None:
                existing.document_id = document_id
            if source_span_id is not None:
                existing.source_span_id = source_span_id
            if claim_id is not None:
                existing.claim_id = claim_id
            if comment is not None:
                existing.comment = comment
            existing.decided_at = decided_at
            existing.updated_at = datetime.now(UTC)
            decision = existing
        await self._session.flush()
        return decision

    async def begin_document_deletion(
        self,
        document_id: str,
        *,
        reason: str,
        request_id: str,
        user_id: UUID,
    ) -> IndexedDocument:
        async with self._session.begin():
            document = await self._session.get(IndexedDocument, document_id)
            if document is None:
                raise KeyError(document_id)
            document.deletion_status = DocumentDeletionStatus.PENDING.value
            document.tombstone_reason = reason
            document.updated_at = datetime.now(UTC)
            refs = await self._session.get(DocumentCascadeRefs, document_id)
            if refs is None:
                refs = DocumentCascadeRefs(
                    document_id=document_id,
                    cascade_status=CascadeStatus.PENDING.value,
                )
                self._session.add(refs)
            else:
                refs.cascade_status = CascadeStatus.PENDING.value
                refs.cascade_steps = {}
                refs.last_error = None
                refs.updated_at = datetime.now(UTC)
            await self.record_audit_event(
                user_id=user_id,
                action="document_deleted",
                resource_type="document",
                resource_id=document_id,
                details={"phase": "begin", "reason": reason},
                request_id=request_id,
                commit=False,
            )
        await self._session.refresh(document)
        return document

    async def update_document_cascade_step(
        self,
        document_id: str,
        step: str,
        *,
        completed: bool,
        error: str | None = None,
    ) -> DocumentCascadeRefs:
        async with self._session.begin():
            refs = await self._session.get(DocumentCascadeRefs, document_id)
            if refs is None:
                raise KeyError(document_id)
            steps = dict(refs.cascade_steps or {})
            steps[step] = {
                "completed": completed,
                "updated_at": datetime.now(UTC).isoformat(),
                "error": error,
            }
            refs.cascade_steps = steps
            refs.cascade_status = (
                CascadeStatus.COMPLETED.value if completed and error is None else CascadeStatus.IN_PROGRESS.value
            )
            if error:
                refs.cascade_status = CascadeStatus.FAILED.value
                refs.last_error = error
            refs.updated_at = datetime.now(UTC)
            document = await self._session.get(IndexedDocument, document_id)
            if document is not None:
                document.deletion_status = DocumentDeletionStatus.IN_PROGRESS.value
                document.updated_at = datetime.now(UTC)
        await self._session.refresh(refs)
        return refs

    async def finalize_document_deletion(
        self,
        document_id: str,
        *,
        request_id: str,
        user_id: UUID,
    ) -> IndexedDocument:
        async with self._session.begin():
            document = await self._session.get(IndexedDocument, document_id)
            if document is None:
                raise KeyError(document_id)
            document.deletion_status = DocumentDeletionStatus.COMPLETED.value
            document.deleted_at = datetime.now(UTC)
            document.updated_at = datetime.now(UTC)
            refs = await self._session.get(DocumentCascadeRefs, document_id)
            if refs is not None:
                refs.cascade_status = CascadeStatus.COMPLETED.value
                refs.last_error = None
                refs.updated_at = datetime.now(UTC)
            await self.record_audit_event(
                user_id=user_id,
                action="document_deleted",
                resource_type="document",
                resource_id=document_id,
                details={"phase": "completed"},
                request_id=request_id,
                commit=False,
            )
        await self._session.refresh(document)
        return document

    async def abort_document_deletion(
        self,
        document_id: str,
        *,
        error: str,
        request_id: str,
        user_id: UUID,
    ) -> IndexedDocument:
        async with self._session.begin():
            document = await self._session.get(IndexedDocument, document_id)
            if document is None:
                raise KeyError(document_id)
            document.deletion_status = DocumentDeletionStatus.FAILED.value
            document.updated_at = datetime.now(UTC)
            refs = await self._session.get(DocumentCascadeRefs, document_id)
            if refs is not None:
                refs.cascade_status = CascadeStatus.FAILED.value
                refs.last_error = error
                refs.updated_at = datetime.now(UTC)
            await self.record_audit_event(
                user_id=user_id,
                action="document_deleted",
                resource_type="document",
                resource_id=document_id,
                details={"phase": "failed", "error": error},
                request_id=request_id,
                commit=False,
            )
        await self._session.refresh(document)
        return document

    async def save_admin_setting_with_audit(
        self,
        *,
        setting_key: str,
        setting_value: dict,
        user_id: UUID,
        request_id: str,
        previous_value: dict | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        from infra.postgres.chat_ui_db.models import AdminSetting

        async with self._session.begin():
            existing = await self._session.scalar(
                select(AdminSetting).where(AdminSetting.setting_key == setting_key)
            )
            if existing is None:
                setting = AdminSetting(
                    setting_key=setting_key,
                    setting_value=setting_value,
                    description=description,
                )
                self._session.add(setting)
            else:
                existing.setting_value = setting_value
                if description is not None:
                    existing.description = description
                setting = existing
            await self.record_audit_event(
                user_id=user_id,
                action="admin_setting_changed",
                resource_type="admin_setting",
                resource_id=setting_key,
                details={
                    "previous_value": previous_value or {},
                    "new_value": setting_value,
                },
                request_id=request_id,
                commit=False,
            )
            await self._session.flush()
            return {
                "setting_key": setting.setting_key,
                "setting_value": dict(setting.setting_value),
                "description": setting.description,
            }

    async def purge_document_pg_refs(self, document_id: str) -> None:
        async with self._session.begin():
            await self._session.execute(
                delete(ReviewDecision).where(ReviewDecision.document_id == document_id)
            )
            refs = await self._session.get(DocumentCascadeRefs, document_id)
            if refs is not None:
                refs.source_span_ids = []
                refs.claim_ids = []
                refs.vector_point_ids = []
                refs.graph_node_refs = []
                refs.minio_object_refs = []
                refs.updated_at = datetime.now(UTC)

    async def record_access_denied_audit(
        self,
        *,
        user_id: UUID | None,
        resource_type: str,
        resource_id: str,
        role: str,
        request_id: str,
        source_span_id: str | None = None,
        document_id: str | None = None,
        reason: str | None = None,
        query_run_id: str | None = None,
        export_format: str | None = None,
        commit: bool = True,
    ) -> AuditEvent:
        return await self.record_audit_event(
            user_id=user_id,
            action="access_denied",
            resource_type=resource_type,
            resource_id=resource_id,
            details=build_access_denied_details(
                role=role,
                source_span_id=source_span_id,
                document_id=document_id,
                reason=reason,
                query_run_id=query_run_id,
                export_format=export_format,
            ),
            request_id=request_id,
            commit=commit,
        )

    async def record_source_viewed_audit(
        self,
        *,
        user_id: UUID | None,
        source_span_id: str,
        role: str,
        status: str,
        request_id: str,
        document_id: str | None = None,
        commit: bool = True,
    ) -> AuditEvent:
        return await self.record_audit_event(
            user_id=user_id,
            action="source_viewed",
            resource_type="source_span",
            resource_id=source_span_id,
            details=build_source_viewed_details(
                source_span_id=source_span_id,
                role=role,
                status=status,
                document_id=document_id,
            ),
            request_id=request_id,
            commit=commit,
        )

    async def record_search_audit(
        self,
        *,
        user_id: UUID | None,
        query: str,
        role: str,
        status: str,
        request_id: str,
        result_count: int | None = None,
        filters: dict[str, Any] | None = None,
        commit: bool = True,
    ) -> AuditEvent:
        return await self.record_audit_event(
            user_id=user_id,
            action="search",
            resource_type="search_query",
            resource_id=query[:256],
            details=build_search_audit_details(
                query=query,
                role=role,
                status=status,
                result_count=result_count,
                filters=filters,
            ),
            request_id=request_id,
            commit=commit,
        )

    async def record_export_audit(
        self,
        *,
        user_id: UUID | None,
        export_job_id: str,
        query_run_id: str,
        export_format: str,
        role: str,
        status: str,
        request_id: str,
        commit: bool = True,
    ) -> AuditEvent:
        return await self.record_audit_event(
            user_id=user_id,
            action="document_exported",
            resource_type="export_job",
            resource_id=export_job_id,
            details=build_export_audit_details(
                query_run_id=query_run_id,
                export_format=export_format,
                role=role,
                status=status,
            ),
            request_id=request_id,
            commit=commit,
        )

    def audit_event_to_dict(self, event: AuditEvent) -> dict[str, Any]:
        return {
            "id": event.id,
            "user_id": event.user_id,
            "action": event.action,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "details": event.details,
            "request_id": event.request_id,
            "created_at": event.created_at,
        }
