from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Select, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    DocumentCascadeRefs,
    ReviewDecision,
    ReviewDecisionStatus,
    SourceSpanLookup,
)


def table_row_id_from_block(table_block_id: str | None) -> str | None:
    if not table_block_id or ":row:" not in table_block_id:
        return None
    return table_block_id


class ReviewStorageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ensure_pending_decision(
        self,
        candidate_id: str,
        candidate_type: str,
        *,
        document_id: str | None = None,
        source_span_id: str | None = None,
        claim_id: str | None = None,
    ) -> ReviewDecision:
        existing = await self.get_decision(candidate_id, candidate_type)
        if existing is not None:
            return existing
        decision = ReviewDecision(
            id=uuid4(),
            candidate_id=candidate_id,
            candidate_type=candidate_type,
            status=ReviewDecisionStatus.PENDING.value,
            document_id=document_id,
            source_span_id=source_span_id,
            claim_id=claim_id,
        )
        self._session.add(decision)
        await self._session.commit()
        await self._session.refresh(decision)
        return decision

    async def get_decision(self, candidate_id: str, candidate_type: str) -> ReviewDecision | None:
        result = await self._session.execute(
            select(ReviewDecision).where(
                ReviewDecision.candidate_id == candidate_id,
                ReviewDecision.candidate_type == candidate_type,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_decision(
        self,
        candidate_id: str,
        candidate_type: str,
        status: ReviewDecisionStatus,
        *,
        reviewer_user_id: UUID | None = None,
        document_id: str | None = None,
        source_span_id: str | None = None,
        claim_id: str | None = None,
        comment: str | None = None,
    ) -> ReviewDecision:
        existing = await self.get_decision(candidate_id, candidate_type)
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
        await self._session.commit()
        await self._session.refresh(decision)
        return decision

    async def list_decisions(
        self,
        *,
        status: str | None = None,
        candidate_type: str | None = None,
        document_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ReviewDecision]:
        query: Select[tuple[ReviewDecision]] = select(ReviewDecision)
        if status is not None:
            query = query.where(ReviewDecision.status == status)
        if candidate_type is not None:
            query = query.where(ReviewDecision.candidate_type == candidate_type)
        if document_id is not None:
            query = query.where(ReviewDecision.document_id == document_id)
        query = query.order_by(ReviewDecision.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def upsert_source_span_lookup(
        self,
        *,
        source_span_id: str,
        document_id: str,
        page: int,
        highlight_start: int,
        highlight_end: int,
        source_type: str,
        text_snippet: str,
        table_block_id: str | None = None,
        table_row_id: str | None = None,
        access_level: str = "internal",
        allowed_roles: list[str] | None = None,
    ) -> SourceSpanLookup:
        row_id = table_row_id or table_row_id_from_block(table_block_id)
        roles = allowed_roles or []
        stmt = (
            insert(SourceSpanLookup)
            .values(
                source_span_id=source_span_id,
                document_id=document_id,
                page=page,
                highlight_start=highlight_start,
                highlight_end=highlight_end,
                table_row_id=row_id,
                table_block_id=table_block_id,
                source_type=source_type,
                text_snippet=text_snippet,
                access_level=access_level,
                allowed_roles=roles,
            )
            .on_conflict_do_update(
                index_elements=[SourceSpanLookup.source_span_id],
                set_={
                    "document_id": document_id,
                    "page": page,
                    "highlight_start": highlight_start,
                    "highlight_end": highlight_end,
                    "table_row_id": row_id,
                    "table_block_id": table_block_id,
                    "source_type": source_type,
                    "text_snippet": text_snippet,
                    "access_level": access_level,
                    "allowed_roles": roles,
                },
            )
            .returning(SourceSpanLookup)
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.scalar_one()

    async def get_source_span_lookup(self, source_span_id: str) -> SourceSpanLookup | None:
        return await self._session.get(SourceSpanLookup, source_span_id)

    async def list_source_spans_for_document(self, document_id: str) -> list[SourceSpanLookup]:
        result = await self._session.execute(
            select(SourceSpanLookup)
            .where(SourceSpanLookup.document_id == document_id)
            .order_by(SourceSpanLookup.page, SourceSpanLookup.highlight_start)
        )
        return list(result.scalars().all())

    async def upsert_document_cascade_refs(
        self,
        document_id: str,
        *,
        source_span_ids: list[str] | None = None,
        claim_ids: list[str] | None = None,
        vector_point_ids: list[str] | None = None,
        graph_node_refs: list[dict] | None = None,
        minio_object_refs: list[dict] | None = None,
    ) -> DocumentCascadeRefs:
        existing = await self._session.get(DocumentCascadeRefs, document_id)
        if existing is None:
            refs = DocumentCascadeRefs(
                document_id=document_id,
                source_span_ids=source_span_ids or [],
                claim_ids=claim_ids or [],
                vector_point_ids=vector_point_ids or [],
                graph_node_refs=graph_node_refs or [],
                minio_object_refs=minio_object_refs or [],
            )
            self._session.add(refs)
        else:
            if source_span_ids is not None:
                existing.source_span_ids = source_span_ids
            if claim_ids is not None:
                existing.claim_ids = claim_ids
            if vector_point_ids is not None:
                existing.vector_point_ids = vector_point_ids
            if graph_node_refs is not None:
                existing.graph_node_refs = graph_node_refs
            if minio_object_refs is not None:
                existing.minio_object_refs = minio_object_refs
            existing.updated_at = datetime.now(UTC)
            refs = existing
        await self._session.commit()
        await self._session.refresh(refs)
        return refs

    async def get_document_cascade_refs(self, document_id: str) -> DocumentCascadeRefs | None:
        return await self._session.get(DocumentCascadeRefs, document_id)
