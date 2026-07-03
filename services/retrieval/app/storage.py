from typing import Protocol

from shared.contracts import (
    AccessPolicy,
    RetrievalIndexRequest,
    SearchResultPayload,
    SourcePayload,
    StorageWriteResult,
    UserRole,
)


class StorageAdapterNotReady(RuntimeError):
    pass


class RetrievalStorageAdapter(Protocol):
    @property
    def is_ready(self) -> bool: ...

    async def index(self, request: RetrievalIndexRequest) -> StorageWriteResult: ...

    async def search(
        self,
        question: str,
        filters: dict,
        access_roles: list[str],
        limit: int,
    ) -> SearchResultPayload: ...

    async def get_source(
        self,
        source_span_id: str,
        access_roles: list[str],
    ) -> SourcePayload | None: ...


class PendingRetrievalStorageAdapter:
    is_ready = False

    async def index(self, request: RetrievalIndexRequest) -> StorageWriteResult:
        raise StorageAdapterNotReady("qdrant_adapter_pending")

    async def search(
        self,
        question: str,
        filters: dict,
        access_roles: list[str],
        limit: int,
    ) -> SearchResultPayload:
        raise StorageAdapterNotReady("qdrant_adapter_pending")

    async def get_source(
        self,
        source_span_id: str,
        access_roles: list[str],
    ) -> SourcePayload | None:
        raise StorageAdapterNotReady("qdrant_adapter_pending")


def access_allowed(policy: AccessPolicy, access_roles: list[str]) -> bool:
    roles = set(access_roles)
    if UserRole.ADMIN.value in roles:
        return True
    allowed_roles = set(policy.allowed_roles)
    if policy.level == "public":
        return True
    if policy.level == "internal":
        internal_roles = {
            UserRole.RESEARCHER.value,
            UserRole.ANALYST.value,
            UserRole.MANAGER.value,
        }
        if allowed_roles:
            internal_roles &= allowed_roles
        return bool(roles & internal_roles)
    return bool(allowed_roles and roles & allowed_roles)
