from uuid import UUID

import httpx
from fastapi import UploadFile

from infra.postgres.orchestrator_db import IngestionTaskRepository, QueryRunRepository
from shared.contracts import DictionaryVersionPayload, IngestionTaskPayload
from shared.security import AuthenticatedPrincipal

from .service import OrchestratorService


class DictionaryService:
    def __init__(
        self,
        repository: IngestionTaskRepository,
        client: httpx.AsyncClient,
        ingestion_url: str,
        knowledge_url: str,
        query_repository: QueryRunRepository | None = None,
    ) -> None:
        self._service = OrchestratorService(
            repository,
            client,
            ingestion_url,
            knowledge_url,
            "http://retrieval",
            "http://model",
            "http://export",
            query_repository=query_repository,
        )

    async def upload_dictionary(
        self,
        principal: AuthenticatedPrincipal,
        package: UploadFile,
        authorization: str,
        request_id: str,
    ) -> IngestionTaskPayload:
        return await self._service.upload_dictionary(
            principal, package, authorization, request_id
        )

    async def list_dictionaries(self, request_id: str) -> list[DictionaryVersionPayload]:
        return await self._service.list_dictionaries(request_id)

    async def get_active_dictionary(self, request_id: str) -> DictionaryVersionPayload:
        return await self._service.get_active_dictionary(request_id)

    async def activate_dictionary(
        self,
        principal: AuthenticatedPrincipal,
        version_id: UUID,
        request_id: str,
    ) -> DictionaryVersionPayload:
        return await self._service.activate_dictionary(principal, version_id, request_id)
