from uuid import UUID

from infra.postgres.notification_db.repository import SqlAlchemyNotificationRepository
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

    async def list_notifications(self, principal: AuthenticatedPrincipal) -> list[dict]:
        notes = await self._repository.get_user_notifications(principal.user_id)
        return [self._payload(note) for note in notes]

    async def mark_read(self, principal: AuthenticatedPrincipal, notification_id: UUID) -> None:
        updated = await self._repository.mark_as_read(notification_id, principal.user_id)
        if not updated:
            raise NotificationServiceError(404, "notification_not_found", "Notification not found")

    async def mark_all_read(self, principal: AuthenticatedPrincipal) -> None:
        await self._repository.mark_all_as_read(principal.user_id)

    @staticmethod
    def _payload(note) -> dict:
        title = TYPE_TITLES.get(note.type) or note.message.split(".")[0]
        return {
            "id": str(note.id),
            "title": title,
            "reason": note.message,
            "type": note.type,
            "reference_id": note.reference_id,
            "read": note.is_read,
            "created_at": note.created_at.isoformat(),
        }
