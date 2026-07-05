from datetime import datetime
from uuid import UUID

import httpx

from infra.postgres.notification_db.repository import (
    NotificationData,
    SqlAlchemyNotificationRepository,
)
from shared.contracts import (
    NotificationListPayload,
    NotificationMarkReadPayload,
    NotificationPayload,
    UserInterestItem,
    UserInterestsPayload,
    UserInterestsUpdatePayload,
)
from shared.security import AuthenticatedPrincipal

from ..core.config import settings


class NotificationServiceError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


TYPE_TITLES = {
    "interest_match": "Новый документ по интересам",
    "ingestion_complete": "Документ обработан",
    "conflict_detected": "Обнаружено противоречие",
}


class NotificationService:
    def __init__(
        self,
        repository: SqlAlchemyNotificationRepository,
        client: httpx.AsyncClient | None = None,
        model_url: str | None = None,
    ) -> None:
        self._repository = repository
        self._client = client
        self._model_url = (model_url or settings.model_url).rstrip("/")

    async def list_notifications(
        self,
        principal: AuthenticatedPrincipal,
        since: datetime | None = None,
        cursor: str | None = None,
    ) -> NotificationListPayload:
        notes, next_cursor = await self._repository.list_user_notifications(
            principal.user_id,
            since=since,
            cursor=cursor,
            limit=settings.notification_list_limit,
        )
        items = [self._payload(note) for note in notes]
        unread_count = await self._repository.count_unread(principal.user_id)
        return NotificationListPayload(
            items=items,
            unread_count=unread_count,
            next_cursor=next_cursor,
        )

    async def mark_read(
        self, principal: AuthenticatedPrincipal, notification_id: UUID
    ) -> NotificationMarkReadPayload:
        updated = await self._repository.mark_as_read(notification_id, principal.user_id)
        if not updated:
            raise NotificationServiceError(404, "notification_not_found", "Notification not found")
        return NotificationMarkReadPayload(updated_count=1)

    async def mark_all_read(self, principal: AuthenticatedPrincipal) -> NotificationMarkReadPayload:
        return NotificationMarkReadPayload(
            updated_count=await self._repository.mark_all_as_read(principal.user_id)
        )

    async def get_interests(self, principal: AuthenticatedPrincipal) -> UserInterestsPayload:
        interest = await self._repository.get_user_interests(principal.user_id)
        if interest is None:
            return UserInterestsPayload(user_id=principal.user_id)
        entities = interest.extracted_entities or {}
        return UserInterestsPayload(
            user_id=principal.user_id,
            raw_text=interest.raw_text,
            interests=[
                UserInterestItem.model_validate(item)
                for item in entities.get("interests", [])
                if isinstance(item, dict)
            ],
            extracted_entities=entities,
            updated_at=interest.updated_at,
        )

    async def update_interests(
        self,
        principal: AuthenticatedPrincipal,
        payload: UserInterestsUpdatePayload,
    ) -> UserInterestsPayload:
        interests = payload.interests
        warnings = []
        if payload.raw_text.strip() and not interests:
            extracted = await self._extract_interests(payload.raw_text)
            interests = extracted["interests"]
            warnings = extracted["warnings"]
        entities = {
            "interests": [
                item.model_dump(mode="json") for item in interests
            ]
        }
        if warnings:
            entities["warnings"] = warnings
        interest = await self._repository.update_user_interests(
            principal.user_id,
            payload.raw_text,
            entities,
        )
        return UserInterestsPayload(
            user_id=principal.user_id,
            raw_text=interest.raw_text,
            interests=interests,
            extracted_entities=interest.extracted_entities or entities,
            updated_at=interest.updated_at,
            warnings=warnings,
        )

    async def create_event(self, data: NotificationData) -> NotificationPayload:
        note = await self._repository.create_notification(data)
        return self._payload(note)

    async def _extract_interests(self, raw_text: str) -> dict[str, list]:
        if self._client is None:
            return {"interests": [], "warnings": ["model_interest_extraction_unavailable"]}
        try:
            response = await self._client.post(
                f"{self._model_url}/v1/interests/extract",
                json={"text": raw_text},
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            return {"interests": [], "warnings": ["model_interest_extraction_failed"]}
        interests = [
            UserInterestItem.model_validate(item)
            for item in payload.get("interests", [])
            if isinstance(item, dict)
        ]
        return {
            "interests": interests,
            "warnings": [str(item) for item in payload.get("warnings", [])],
        }

    @staticmethod
    def _payload(note) -> NotificationPayload:
        title = TYPE_TITLES.get(note.type) or note.message.split(".")[0]
        reference_type = getattr(note, "reference_type", None) or "document"
        return NotificationPayload(
            id=note.id,
            title=title,
            reason=note.message,
            type=note.type,
            reference_id=note.reference_id,
            reference_type=reference_type,
            read=note.is_read,
            match_score=getattr(note, "match_score", None),
            match_reason=str((getattr(note, "match_payload", None) or {}).get("reason") or ""),
            created_at=note.created_at,
        )
