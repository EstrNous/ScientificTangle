from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from infra.postgres.orchestrator_db import get_session
from infra.postgres.orchestrator_db.document_catalog_repository import DocumentCatalogRepository
from shared.contracts import DocumentCatalogItem, DocumentCatalogResponse, UserRole
from shared.security import AuthenticatedPrincipal
from shared.web import ServiceError, require_principal

router = APIRouter(prefix="/documents", tags=["documents"])

_RESERVED_DOCUMENT_SEGMENTS = frozenset({"upload"})


def require_admin(
    principal: AuthenticatedPrincipal = Depends(require_principal),
) -> AuthenticatedPrincipal:
    if principal.role != UserRole.ADMIN:
        from shared.web import ServiceError

        raise ServiceError(403, "forbidden", "Admin access required")
    return principal


@router.get("", response_model=DocumentCatalogResponse)
async def list_documents(
    principal: Annotated[AuthenticatedPrincipal, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
    status: str | None = None,
    catalog_filter: str | None = Query(default=None, alias="filter"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> DocumentCatalogResponse:
    repository = DocumentCatalogRepository(session)
    items, total = await repository.list_documents(
        status=status,
        catalog_filter=catalog_filter,
        limit=limit,
        offset=offset,
    )
    return DocumentCatalogResponse(
        items=[DocumentCatalogItem.model_validate(item) for item in items],
        total=total,
        filters_applied={"status": status, "filter": catalog_filter},
    )


@router.get("/{document_id}", response_model=DocumentCatalogItem)
async def get_document(
    document_id: str,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DocumentCatalogItem:
    if document_id in _RESERVED_DOCUMENT_SEGMENTS:
        raise ServiceError(404, "document_not_found", "Document not found")
    repository = DocumentCatalogRepository(session)
    item = await repository.get_document(document_id)
    if item is None:
        raise ServiceError(404, "document_not_found", "Document not found")
    return DocumentCatalogItem.model_validate(item)
