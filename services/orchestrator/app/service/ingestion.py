from uuid import UUID

import httpx
from fastapi import UploadFile

from infra.postgres.orchestrator_db import IngestionTaskRepository
from shared.contracts import IngestionTaskPayload
from shared.security import AuthenticatedPrincipal

from .service import OrchestratorService


class IngestionService:
    def __init__(
        self,
        repository: IngestionTaskRepository,
        client: httpx.AsyncClient,
        ingestion_url: str = "http://ingestion",
        knowledge_url: str = "http://knowledge",
        retrieval_url: str = "http://retrieval",
        model_url: str = "http://model",
        enforce_active_dictionary: bool = False,
    ) -> None:
        self._service = OrchestratorService(
            repository,
            client,
            ingestion_url,
            knowledge_url,
            retrieval_url,
            model_url,
            enforce_active_dictionary=enforce_active_dictionary,
        )

    async def start_ingestion_task(
        self,
        principal: AuthenticatedPrincipal,
        files: list[UploadFile],
        authorization: str,
        request_id: str,
    ) -> tuple[IngestionTaskPayload, UUID]:
        return await self._service.start_ingestion_task(
            principal, files, authorization, request_id
        )

    async def continue_ingestion_task(
        self,
        task_id: UUID,
        user_id: UUID,
        authorization: str,
        request_id: str,
        session_factory,
        role: str = "",
    ) -> None:
        await self._service.continue_ingestion_task(
            task_id, user_id, authorization, request_id, session_factory, role
        )

    async def create_task(
        self,
        principal: AuthenticatedPrincipal,
        files: list[UploadFile],
        authorization: str,
        request_id: str,
    ) -> IngestionTaskPayload:
        return await self._service.create_task(principal, files, authorization, request_id)

    async def get_task(
        self,
        task_id: UUID,
        principal: AuthenticatedPrincipal,
    ) -> IngestionTaskPayload:
        return await self._service.get_task(task_id, principal)
