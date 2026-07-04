from uuid import UUID

import httpx

from infra.postgres.orchestrator_db import QueryRunRepository
from shared.contracts import ExportPayload
from shared.security import AuthenticatedPrincipal

from .query import _UnusedIngestionRepository
from .service import OrchestratorService


class ExportService:
    def __init__(
        self,
        client: httpx.AsyncClient,
        query_repository: QueryRunRepository | None = None,
        ingestion_url: str = "http://ingestion",
        knowledge_url: str = "http://knowledge",
        retrieval_url: str = "http://retrieval",
        model_url: str = "http://model",
        export_url: str = "http://export",
    ) -> None:
        self._service = OrchestratorService(
            _UnusedIngestionRepository(),
            client,
            ingestion_url,
            knowledge_url,
            retrieval_url,
            model_url,
            export_url,
            query_repository=query_repository,
            enforce_active_dictionary=False,
        )

    async def export_query_run(
        self,
        principal: AuthenticatedPrincipal,
        run_id: UUID,
        export_format: str,
        request_id: str,
    ) -> ExportPayload:
        return await self._service.export_query_run(
            principal, run_id, export_format, request_id
        )
