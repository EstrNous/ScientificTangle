import json
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from infra.postgres.notification_db.repository import (
    NotificationData,
    SqlAlchemyNotificationRepository,
)
from infra.postgres.notification_db.workflow_repository import NotificationWorkflowRepository
from shared.contracts import NotificationPayload

from ..core.config import Settings
from .matching_service import MatchingService
from .notification_service import NotificationService


class NotificationDeliveryHandler:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        http_client: httpx.AsyncClient | None,
        resolved_settings: Settings,
    ) -> None:
        self._session_factory = session_factory
        self._http_client = http_client
        self._settings = resolved_settings

    async def handle_message(self, raw_message: str) -> list[NotificationPayload]:
        payload = json.loads(raw_message)
        if not isinstance(payload, dict):
            return []
        kind = str(payload.get("kind") or "")
        body = payload.get("payload")
        if not isinstance(body, dict):
            return []
        if kind == "event":
            created = await self._create_event(body)
            return [created] if created is not None else []
        if kind == "match":
            return await self._create_matches(body)
        return []

    async def _create_event(self, body: dict[str, Any]) -> NotificationPayload | None:
        async with self._session_factory() as session:
            service = NotificationService(
                SqlAlchemyNotificationRepository(session),
                client=self._http_client,
                model_url=self._settings.model_url,
            )
            return await service.create_event(
                NotificationData(
                    user_id=UUID(str(body["user_id"])),
                    type=str(body["type"]),
                    message=str(body["message"]),
                    reference_id=body.get("reference_id"),
                    reference_type=body.get("reference_type"),
                    match_score=body.get("match_score"),
                    match_reason=str(body.get("match_reason") or ""),
                    match_payload=body.get("match_payload"),
                )
            )

    async def _create_matches(self, body: dict[str, Any]) -> list[NotificationPayload]:
        async with self._session_factory() as session:
            repository = SqlAlchemyNotificationRepository(session)
            service = MatchingService(
                repository,
                NotificationWorkflowRepository(session),
                client=self._http_client,
                model_url=self._settings.model_url,
                match_score_threshold=self._settings.match_score_threshold,
            )
            return await service.match_and_notify(
                UUID(str(body["user_id"])),
                str(body["document_id"]),
                body.get("artifacts") or [],
            )
