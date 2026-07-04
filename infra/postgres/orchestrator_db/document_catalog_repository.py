from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from shared.contracts import (
    IngestionReport,
    KnowledgeIngestionResponse,
    NormalizedDocument,
    RetrievalIndexResponse,
    StoredSource,
)

from .models import DocumentDeletionStatus, IndexedDocument, IngestionTask, IngestionTaskStatus
from .review_storage import ReviewStorageRepository


def vector_point_id(span_id: str) -> str:
    return str(UUID(hex=hashlib.sha256(span_id.encode("utf-8")).hexdigest()[:32]))


class DocumentCatalogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._review_storage = ReviewStorageRepository(session)

    async def upsert_indexed_document(
        self,
        *,
        document_id: str,
        task_id: UUID,
        title: str,
        source_type: str,
        source_spans_count: int,
        indexed_points_count: int,
        access_level: str,
        metadata: dict | None = None,
    ) -> IndexedDocument:
        metadata_payload = metadata or {}
        stmt = (
            insert(IndexedDocument)
            .values(
                document_id=document_id,
                task_id=task_id,
                title=title,
                source_type=source_type,
                source_spans_count=source_spans_count,
                indexed_points_count=indexed_points_count,
                access_level=access_level,
                metadata_=metadata_payload,
                deletion_status=DocumentDeletionStatus.NONE.value,
            )
            .on_conflict_do_update(
                index_elements=[IndexedDocument.document_id],
                set_={
                    "task_id": task_id,
                    "title": title,
                    "source_type": source_type,
                    "source_spans_count": source_spans_count,
                    "indexed_points_count": indexed_points_count,
                    "access_level": access_level,
                    "metadata_": metadata_payload,
                    "updated_at": datetime.now(UTC),
                },
            )
            .returning(IndexedDocument)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def persist_ingestion_catalog(
        self,
        *,
        task_id: UUID,
        sources: list[StoredSource],
        documents: list[NormalizedDocument],
        knowledge_results: list[KnowledgeIngestionResponse],
        retrieval_result: RetrievalIndexResponse,
    ) -> None:
        _ = retrieval_result
        knowledge_by_document = {result.document_id: result for result in knowledge_results}
        for document in documents:
            spans = document.source_spans
            span_ids = [span.id for span in spans]
            knowledge_result = knowledge_by_document.get(document.id)
            claim_ids = list(knowledge_result.graph_write.claim_ids) if knowledge_result else []
            vector_point_ids = [vector_point_id(span_id) for span_id in span_ids]
            source_path = document.metadata.get("source_path")
            if source_path is None:
                for source in sources:
                    if source.original_filename == document.title or source.original_filename in document.title:
                        source_path = source.original_filename
                        break
            metadata = {
                **document.metadata,
                "source_path": source_path,
                "allowed_roles": list(document.access_policy.allowed_roles),
            }
            await self.upsert_indexed_document(
                document_id=document.id,
                task_id=task_id,
                title=document.title,
                source_type=document.source_type,
                source_spans_count=len(spans),
                indexed_points_count=len(vector_point_ids),
                access_level=document.access_policy.level,
                metadata=metadata,
            )
            for span in spans:
                await self._review_storage.upsert_source_span_lookup(
                    source_span_id=span.id,
                    document_id=document.id,
                    page=span.page,
                    highlight_start=span.start_offset,
                    highlight_end=span.end_offset,
                    source_type=span.source_type,
                    text_snippet=span.text,
                    table_block_id=span.table_block_id,
                    access_level=document.access_policy.level,
                    allowed_roles=list(document.access_policy.allowed_roles),
                )
            minio_refs = [
                {
                    "object_key": source.object_key,
                    "original_filename": source.original_filename,
                }
                for source in sources
                if source_path and source.original_filename == source_path
            ]
            graph_node_refs = [
                {"node_id": node_id}
                for node_id in (knowledge_result.graph_write.graph_entity_ids if knowledge_result else [])
            ]
            await self._review_storage.upsert_document_cascade_refs(
                document.id,
                source_span_ids=span_ids,
                claim_ids=claim_ids,
                vector_point_ids=vector_point_ids,
                graph_node_refs=graph_node_refs,
                minio_object_refs=minio_refs,
            )
        await self._session.commit()

    async def list_documents(
        self,
        *,
        status: str | None = None,
        catalog_filter: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        if status == "failed":
            failed_items = await self._failed_task_items(catalog_filter=catalog_filter, limit=limit, offset=offset)
            return failed_items, len(failed_items)
        query = self._indexed_query(status=status, catalog_filter=catalog_filter)
        count_result = await self._session.execute(select(func.count()).select_from(query.subquery()))
        total = int(count_result.scalar_one())
        result = await self._session.execute(
            query.order_by(IndexedDocument.created_at.desc()).limit(limit).offset(offset)
        )
        items = [self._indexed_document_item(row) for row in result.scalars().all()]
        if status is None:
            failed_items = await self._failed_task_items(catalog_filter=catalog_filter, limit=limit, offset=0)
            existing_ids = {item["document_id"] for item in items}
            for item in failed_items:
                if item["document_id"] not in existing_ids:
                    items.append(item)
            total += sum(1 for item in failed_items if item["document_id"] not in existing_ids)
        return items[:limit], total

    def _indexed_query(
        self,
        *,
        status: str | None,
        catalog_filter: str | None,
    ) -> Select:
        query: Select = select(IndexedDocument).where(
            IndexedDocument.deletion_status == DocumentDeletionStatus.NONE.value
        )
        if catalog_filter == "no_index":
            query = query.where(IndexedDocument.indexed_points_count == 0)
        if catalog_filter == "no_source_spans":
            query = query.where(IndexedDocument.source_spans_count == 0)
        if status == "completed":
            query = query.where(
                IndexedDocument.source_spans_count > 0,
                IndexedDocument.indexed_points_count > 0,
            )
        if status == "no_index":
            query = query.where(IndexedDocument.indexed_points_count == 0)
        if status == "no_source_spans":
            query = query.where(IndexedDocument.source_spans_count == 0)
        return query

    def _indexed_document_item(self, row: IndexedDocument) -> dict:
        metadata = row.metadata_ or {}
        item_status = "completed"
        if row.indexed_points_count == 0:
            item_status = "no_index"
        if row.source_spans_count == 0:
            item_status = "no_source_spans"
        return {
            "document_id": row.document_id,
            "title": row.title,
            "source_path": metadata.get("source_path"),
            "source_type": row.source_type,
            "ingestion_task_id": row.task_id,
            "status": item_status,
            "access_level": row.access_level,
            "source_spans_count": row.source_spans_count,
            "indexed_points_count": row.indexed_points_count,
            "created_at": row.created_at,
            "warnings": list(metadata.get("warnings", [])),
            "error_message": metadata.get("error_message"),
        }

    async def _failed_task_items(
        self,
        *,
        catalog_filter: str | None,
        limit: int,
        offset: int,
    ) -> list[dict]:
        query = select(IngestionTask).where(
            IngestionTask.status == IngestionTaskStatus.FAILED.value,
            IngestionTask.task_kind == "document_ingestion",
        )
        result = await self._session.execute(
            query.order_by(IngestionTask.created_at.desc()).limit(limit).offset(offset)
        )
        items: list[dict] = []
        for task in result.scalars().all():
            report = IngestionReport.model_validate(task.report or {})
            for source in report.sources:
                item = {
                    "document_id": f"failed:{task.id}:{source.original_filename}",
                    "title": source.original_filename,
                    "source_path": source.original_filename,
                    "source_type": source.content_type,
                    "ingestion_task_id": task.id,
                    "status": "failed",
                    "access_level": "internal",
                    "source_spans_count": 0,
                    "indexed_points_count": 0,
                    "created_at": task.created_at,
                    "warnings": list(report.warnings),
                    "error_message": task.error_message,
                }
                if catalog_filter == "no_index" and item["indexed_points_count"] != 0:
                    continue
                if catalog_filter == "no_source_spans" and item["source_spans_count"] != 0:
                    continue
                items.append(item)
        return items

    async def list_access_policies(self, limit: int = 200) -> list[dict]:
        result = await self._session.execute(
            select(IndexedDocument)
            .where(IndexedDocument.deletion_status == DocumentDeletionStatus.NONE.value)
            .order_by(IndexedDocument.created_at.desc())
            .limit(limit)
        )
        policies = []
        for row in result.scalars().all():
            metadata = row.metadata_ or {}
            policies.append(
                {
                    "document_id": row.document_id,
                    "title": row.title,
                    "access_level": row.access_level,
                    "allowed_roles": list(metadata.get("allowed_roles", [])),
                }
            )
        return policies

    async def count_restricted_documents(self) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(IndexedDocument)
            .where(
                IndexedDocument.deletion_status == DocumentDeletionStatus.NONE.value,
                IndexedDocument.access_level.in_(("restricted", "confidential")),
            )
        )
        return int(result.scalar_one())
