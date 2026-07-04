from uuid import UUID

from infra.postgres.notification_db.repository import SqlAlchemyNotificationRepository
from shared.contracts import (
    NotificationListPayload,
    NotificationMarkReadPayload,
    NotificationPayload,
    UserInterestItem,
    UserInterestsPayload,
    UserInterestsUpdatePayload,
)
from shared.security import AuthenticatedPrincipal


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
    def __init__(self, repository: SqlAlchemyNotificationRepository) -> None:
        self._repository = repository

    async def list_notifications(self, principal: AuthenticatedPrincipal) -> NotificationListPayload:
        notes = await self._repository.get_user_notifications(principal.user_id)
        items = [self._payload(note) for note in notes]
        return NotificationListPayload(
            items=items,
            unread_count=sum(1 for item in items if not item.read),
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
        entities = {
            "interests": [
                item.model_dump(mode="json") for item in payload.interests
            ]
        }
        interest = await self._repository.update_user_interests(
            principal.user_id,
            payload.raw_text,
            entities,
        )
        return UserInterestsPayload(
            user_id=principal.user_id,
            raw_text=interest.raw_text,
            interests=payload.interests,
            extracted_entities=interest.extracted_entities or entities,
            updated_at=interest.updated_at,
        )

    @staticmethod
    def _payload(note) -> NotificationPayload:
        title = TYPE_TITLES.get(note.type) or note.message.split(".")[0]
        return NotificationPayload(
            id=note.id,
            title=title,
            reason=note.message,
            type=note.type,
            reference_id=note.reference_id,
            read=note.is_read,
            created_at=note.created_at,
        )
