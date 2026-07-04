from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Notification, UserInterest


@dataclass(frozen=True, slots=True)
class NotificationData:
    user_id: UUID
    type: str
    message: str
    reference_id: str | None = None
    reference_type: str | None = None

class NotificationRepository(Protocol):
    async def get_user_notifications(self, user_id: UUID, limit: int = 20, since: datetime | None = None) -> list[Notification]: ...
    async def mark_as_read(self, notification_id: UUID, user_id: UUID) -> bool: ...
    async def mark_all_as_read(self, user_id: UUID) -> int: ...
    async def create_notification(self, data: NotificationData) -> Notification: ...
    async def get_user_interests(self, user_id: UUID) -> UserInterest | None: ...
    async def update_user_interests(self, user_id: UUID, raw_text: str, entities: dict) -> UserInterest: ...

class SqlAlchemyNotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_notifications(
        self,
        user_id: UUID,
        limit: int = 20,
        since: datetime | None = None,
    ) -> list[Notification]:
        query = select(Notification).where(Notification.user_id == user_id)
        if since is not None:
            query = query.where(Notification.created_at > since)
        result = await self._session.scalars(
            query
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return list(result)

    async def mark_as_read(self, notification_id: UUID, user_id: UUID) -> bool:
        result = await self._session.execute(
            update(Notification)
            .where(Notification.id == notification_id, Notification.user_id == user_id)
            .values(is_read=True)
        )
        await self._session.commit()
        return bool(result.rowcount)

    async def mark_all_as_read(self, user_id: UUID) -> int:
        result = await self._session.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True)
        )
        await self._session.commit()
        return int(result.rowcount or 0)

    async def create_notification(self, data: NotificationData) -> Notification:
        note = Notification(
            user_id=data.user_id,
            type=data.type,
            message=data.message,
            reference_id=data.reference_id,
            reference_type=data.reference_type,
        )
        self._session.add(note)
        await self._session.commit()
        await self._session.refresh(note)
        return note

    async def get_user_interests(self, user_id: UUID) -> UserInterest | None:
        return await self._session.scalar(select(UserInterest).where(UserInterest.user_id == user_id))

    async def update_user_interests(self, user_id: UUID, raw_text: str, entities: dict) -> UserInterest:
        interest = await self._session.scalar(select(UserInterest).where(UserInterest.user_id == user_id))
        if interest:
            interest.raw_text = raw_text
            interest.extracted_entities = entities
        else:
            interest = UserInterest(user_id=user_id, raw_text=raw_text, extracted_entities=entities)
            self._session.add(interest)
        await self._session.commit()
        await self._session.refresh(interest)
        return interest
