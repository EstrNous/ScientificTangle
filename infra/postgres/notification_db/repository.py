from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import Select, func, select, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession

from infra.postgres.common.cursor import decode_cursor, encode_cursor

from .models import Notification, NotificationMatchResult, UserInterest


@dataclass(frozen=True, slots=True)
class NotificationData:
    user_id: UUID
    type: str
    message: str
    reference_id: str | None = None
    reference_type: str | None = None
    match_score: float | None = None
    match_reason: str = ""
    match_payload: dict | None = None

class NotificationRepository(Protocol):
    async def get_user_notifications(self, user_id: UUID, limit: int = 20, since: datetime | None = None) -> list[Notification]: ...
    async def list_user_notifications(
        self,
        user_id: UUID,
        *,
        since: datetime | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[Notification], str | None]: ...
    async def count_unread(self, user_id: UUID) -> int: ...
    async def find_notification_by_reference(
        self, user_id: UUID, type: str, reference_id: str
    ) -> Notification | None: ...
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
        notifications = list(result)
        await self._attach_match_results(notifications)
        return notifications

    async def list_user_notifications(
        self,
        user_id: UUID,
        *,
        since: datetime | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[Notification], str | None]:
        query: Select[tuple[Notification]] = select(Notification).where(Notification.user_id == user_id)
        if cursor is not None:
            cursor_created_at, cursor_id = decode_cursor(cursor)
            query = query.where(
                tuple_(Notification.created_at, Notification.id)
                < tuple_(cursor_created_at, cursor_id)
            )
        elif since is not None:
            query = query.where(Notification.created_at > since)
        query = query.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit + 1)
        result = await self._session.scalars(query)
        notifications = list(result)
        next_cursor = None
        if len(notifications) > limit:
            last = notifications[limit - 1]
            next_cursor = encode_cursor(last.created_at, last.id)
            notifications = notifications[:limit]
        await self._attach_match_results(notifications)
        return notifications, next_cursor

    async def count_unread(self, user_id: UUID) -> int:
        value = await self._session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        )
        return int(value or 0)

    async def find_notification_by_reference(
        self,
        user_id: UUID,
        type: str,
        reference_id: str,
    ) -> Notification | None:
        note = await self._session.scalar(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.type == type,
                Notification.reference_id == reference_id,
            )
        )
        if note is None:
            return None
        await self._attach_match_results([note])
        return note

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
        if data.reference_id:
            existing = await self.find_notification_by_reference(
                data.user_id,
                data.type,
                data.reference_id,
            )
            if existing is not None:
                return existing
        note = Notification(
            user_id=data.user_id,
            type=data.type,
            message=data.message,
            reference_id=data.reference_id,
            reference_type=data.reference_type,
        )
        self._session.add(note)
        await self._session.flush()
        if data.match_score is not None or data.match_payload:
            self._session.add(
                NotificationMatchResult(
                    user_id=data.user_id,
                    notification_id=note.id,
                    reference_id=data.reference_id,
                    reference_type=data.reference_type,
                    match_score=data.match_score,
                    match_payload={
                        **(data.match_payload or {}),
                        "reason": data.match_reason,
                    },
                )
            )
        await self._session.commit()
        await self._session.refresh(note)
        await self._attach_match_results([note])
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

    async def _attach_match_results(self, notifications: list[Notification]) -> None:
        notification_ids = [note.id for note in notifications]
        if not notification_ids:
            return
        result = await self._session.scalars(
            select(NotificationMatchResult)
            .where(NotificationMatchResult.notification_id.in_(notification_ids))
            .order_by(NotificationMatchResult.created_at.desc())
        )
        matches_by_notification = {}
        for match in result:
            if match.notification_id not in matches_by_notification:
                matches_by_notification[match.notification_id] = match
        for note in notifications:
            match = matches_by_notification.get(note.id)
            if match is not None:
                note.match_score = match.match_score
                note.match_payload = match.match_payload or {}
