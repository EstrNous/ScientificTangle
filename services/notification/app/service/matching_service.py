from uuid import UUID

import httpx

from infra.postgres.notification_db.repository import SqlAlchemyNotificationRepository
from infra.postgres.notification_db.workflow_repository import (
    NotificationMatchInput,
    NotificationWorkflowRepository,
)
from shared.contracts import NotificationPayload, UserInterestItem

from ..core.config import settings
from .notification_service import NotificationService


class MatchingService:
    def __init__(
        self,
        repository: SqlAlchemyNotificationRepository,
        workflow_repository: NotificationWorkflowRepository,
        client: httpx.AsyncClient | None = None,
        model_url: str | None = None,
        match_score_threshold: float = 0.4,
    ) -> None:
        self._repository = repository
        self._workflow_repository = workflow_repository
        self._client = client
        self._model_url = (model_url or settings.model_url).rstrip("/")
        self._match_score_threshold = match_score_threshold

    async def match_and_notify(
        self,
        user_id: UUID,
        document_id: str,
        artifacts: list[dict],
    ) -> list[NotificationPayload]:
        interest = await self._repository.get_user_interests(user_id)
        if interest is None:
            return []
        entities = interest.extracted_entities or {}
        interests = [
            UserInterestItem.model_validate(item)
            for item in entities.get("interests", [])
            if isinstance(item, dict)
        ]
        if not interests or not artifacts:
            return []
        if self._client is None:
            return []
        try:
            response = await self._client.post(
                f"{self._model_url}/v1/notifications/match",
                json={
                    "interests": [item.model_dump(mode="json") for item in interests],
                    "artifacts": artifacts,
                },
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            return []
        created: list[NotificationPayload] = []
        for match in payload.get("matches", []):
            if not isinstance(match, dict):
                continue
            score = float(match.get("score") or 0.0)
            if score < self._match_score_threshold:
                continue
            label = str(match.get("interest_label") or "")
            reason = str(match.get("reason") or "")
            notification, _ = await self._workflow_repository.create_notification_with_match(
                user_id,
                type="interest_match",
                message=f"Совпадение с подпиской: {label}",
                reference_id=document_id,
                reference_type="document",
                match=NotificationMatchInput(
                    reference_id=document_id,
                    reference_type="document",
                    match_score=score,
                    match_payload={
                        "reason": reason,
                        "interest_label": label,
                        "artifact_id": match.get("artifact_id"),
                    },
                ),
            )
            notification.match_score = score
            notification.match_payload = {"reason": reason}
            created.append(NotificationService._payload(notification))
        return created
