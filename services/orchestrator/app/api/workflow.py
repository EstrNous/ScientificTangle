from datetime import UTC, datetime
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from infra.postgres.orchestrator_db import QueryRunRepository, get_session
from infra.postgres.orchestrator_db.models import (
    DocumentCascadeRefs,
    DocumentDeletionStatus,
    IndexedDocument,
    ReviewDecision,
    ReviewDecisionStatus,
    SourceSpanLookup,
)
from shared.contracts import (
    AccessPolicy,
    DeleteDocumentResult,
    ReviewDecisionPayload,
    ReviewDecisionResult,
    ReviewQueueItem,
    ReviewQueuePayload,
    UserRole,
)
from shared.security import AuthenticatedPrincipal
from shared.web import ServiceError, require_principal

from ..core.config import settings

router = APIRouter(tags=["workflow"])


class ReviewQueueRequest(BaseModel):
    status: str = "pending"
    limit: int = Field(default=20, ge=1, le=100)


class AdminPolicyPatchRequest(BaseModel):
    access_policy: AccessPolicy


def require_admin(principal: AuthenticatedPrincipal = Depends(require_principal)) -> AuthenticatedPrincipal:
    if principal.role != UserRole.ADMIN:
        raise ServiceError(403, "forbidden", "Admin access required")
    return principal


@router.get("/review/queue", response_model=ReviewQueuePayload)
async def get_review_queue(
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
    status: str = "pending",
    limit: int = 20,
) -> ReviewQueuePayload:
    return await review_queue_payload(session, status, limit)


@router.post("/review/queue", response_model=ReviewQueuePayload)
async def post_review_queue(
    payload: ReviewQueueRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ReviewQueuePayload:
    return await review_queue_payload(session, payload.status, payload.limit)


@router.post("/review/decisions", response_model=ReviewDecisionResult)
async def review_decision(
    payload: ReviewDecisionPayload,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ReviewDecisionResult:
    decision = await session.get(ReviewDecision, payload.item_id)
    if decision is None:
        raise ServiceError(404, "review_item_not_found", "Review item not found")
    status = {
        "approve": ReviewDecisionStatus.APPROVED,
        "reject": ReviewDecisionStatus.REJECTED,
        "defer": ReviewDecisionStatus.DEFERRED,
    }[payload.decision]
    decided_at = datetime.now(UTC)
    decision.status = status.value
    decision.reviewer_user_id = principal.user_id
    decision.comment = payload.reason
    decision.decided_at = decided_at
    decision.updated_at = decided_at
    await session.commit()
    await session.refresh(decision)
    await QueryRunRepository(session).record_audit_event(
        principal.user_id,
        "review_decision",
        "review_item",
        str(decision.id),
        {
            "decision": payload.decision,
            "document_id": decision.document_id,
            "source_span_ids": payload.source_span_ids,
        },
        request.state.request_id,
    )
    return ReviewDecisionResult(
        item_id=decision.id,
        status=status.value,
        decided_by=principal.user_id,
        decided_at=decision.decided_at or decided_at,
    )


@router.delete("/documents/{document_id}", response_model=DeleteDocumentResult)
async def delete_document(
    document_id: str,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DeleteDocumentResult:
    document = await session.get(IndexedDocument, document_id)
    if document is None:
        return DeleteDocumentResult(document_id=document_id, status="not_found")
    refs = await session.get(DocumentCascadeRefs, document_id)
    deleted_source_spans = len(refs.source_span_ids) if refs else document.source_spans_count
    deleted_vectors = len(refs.vector_point_ids) if refs else document.indexed_points_count
    deleted_graph_nodes = len(refs.graph_node_refs) if refs else 0
    warnings = await purge_downstream_refs(request.app.state.http_client, document_id)
    document.deletion_status = DocumentDeletionStatus.COMPLETED.value
    document.deleted_at = datetime.now(UTC)
    document.tombstone_reason = "user_requested_delete"
    document.updated_at = datetime.now(UTC)
    await session.execute(delete(SourceSpanLookup).where(SourceSpanLookup.document_id == document_id))
    if refs is not None:
        await session.delete(refs)
    await session.commit()
    await QueryRunRepository(session).record_audit_event(
        principal.user_id,
        "document_deleted",
        "document",
        document_id,
        {
            "deleted_source_spans": deleted_source_spans,
            "deleted_vectors": deleted_vectors,
            "deleted_graph_nodes": deleted_graph_nodes,
            "warnings": warnings,
        },
        request.state.request_id,
    )
    return DeleteDocumentResult(
        document_id=document_id,
        status="deleted",
        deleted_source_spans=deleted_source_spans,
        deleted_vectors=deleted_vectors,
        deleted_graph_nodes=deleted_graph_nodes,
        warnings=warnings,
    )


@router.patch("/admin/policies/{document_id}")
async def patch_admin_policy(
    document_id: str,
    payload: AdminPolicyPatchRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    document = await session.get(IndexedDocument, document_id)
    if document is None:
        raise ServiceError(404, "document_not_found", "Document not found")
    document.access_level = payload.access_policy.level
    document.metadata_ = {
        **(document.metadata_ or {}),
        "allowed_roles": payload.access_policy.allowed_roles,
    }
    document.updated_at = datetime.now(UTC)
    await session.commit()
    await QueryRunRepository(session).record_audit_event(
        principal.user_id,
        "admin_setting_changed",
        "document",
        document_id,
        {"access_policy": payload.access_policy.model_dump(mode="json")},
        request.state.request_id,
    )
    return {
        "document_id": document_id,
        "access_policy": payload.access_policy.model_dump(mode="json"),
    }


async def review_queue_payload(
    session: AsyncSession,
    status: str,
    limit: int,
) -> ReviewQueuePayload:
    normalized_status = status if status in {"pending", "approved", "rejected", "deferred"} else "pending"
    result = await session.execute(
        select(ReviewDecision)
        .where(ReviewDecision.status == normalized_status)
        .order_by(ReviewDecision.created_at.desc())
        .limit(limit)
    )
    decisions = list(result.scalars().all())
    return ReviewQueuePayload(
        items=[
            ReviewQueueItem(
                id=decision.id,
                document_id=decision.document_id or "",
                source_span_id=decision.source_span_id,
                claim_id=decision.claim_id,
                status=decision.status,
                payload={
                    "candidate_id": decision.candidate_id,
                    "candidate_type": decision.candidate_type,
                    "comment": decision.comment or "",
                },
                created_at=decision.created_at,
            )
            for decision in decisions
        ],
        total_found=len(decisions),
    )


async def purge_downstream_refs(client: httpx.AsyncClient, document_id: str) -> list[str]:
    warnings = []
    retrieval_response = await delete_if_available(
        client,
        f"{settings.retrieval_url.rstrip('/')}/v1/documents/{document_id}/index",
    )
    knowledge_response = await delete_if_available(
        client,
        f"{settings.knowledge_url.rstrip('/')}/v1/documents/{document_id}/graph",
    )
    for service_name, response in (
        ("retrieval", retrieval_response),
        ("knowledge", knowledge_response),
    ):
        if response is None:
            warnings.append(f"{service_name}_purge_unavailable")
        elif response.status_code not in {200, 202, 204, 404, 405}:
            warnings.append(f"{service_name}_purge_failed")
        elif response.status_code in {404, 405}:
            warnings.append(f"{service_name}_purge_endpoint_missing")
    return warnings


async def delete_if_available(client: httpx.AsyncClient, url: str) -> httpx.Response | None:
    try:
        return await client.delete(url)
    except httpx.HTTPError:
        return None
