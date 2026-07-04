from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Select, delete, func, select, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession

from infra.postgres.common.cursor import CursorPage, decode_cursor, encode_cursor

from .models import ExtractedEntity, Notification, NotificationMatchResult, UserInterest


@dataclass(frozen=True, slots=True)
class ExtractedEntityInput:
    entity_label: str
    entity_type: str
    confidence: float | None = None
    document_id: str | None = None
    source_span_id: str | None = None
    metadata: dict | None = None


@dataclass(frozen=True, slots=True)
class NotificationMatchInput:
    reference_id: str | None
    reference_type: str | None
    match_score: float | None
    match_payload: dict


class NotificationWorkflowRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_interests(self, user_id: UUID) -> UserInterest | None:
        return await self._session.scalar(select(UserInterest).where(UserInterest.user_id == user_id))

    async def list_extracted_entities(self, user_id: UUID) -> list[ExtractedEntity]:
        result = await self._session.scalars(
            select(ExtractedEntity)
            .where(ExtractedEntity.user_id == user_id)
            .order_by(ExtractedEntity.entity_type, ExtractedEntity.entity_label)
        )
        return list(result)

    async def upsert_interests_with_entities(
        self,
        user_id: UUID,
        raw_text: str,
        entities_snapshot: dict,
        entities: list[ExtractedEntityInput],
    ) -> tuple[UserInterest, list[ExtractedEntity]]:
        async with self._session.begin():
            interest = await self._session.scalar(select(UserInterest).where(UserInterest.user_id == user_id))
            if interest is None:
                interest = UserInterest(
                    user_id=user_id,
                    raw_text=raw_text,
                    extracted_entities=entities_snapshot,
                )
                self._session.add(interest)
                await self._session.flush()
            else:
                interest.raw_text = raw_text
                interest.extracted_entities = entities_snapshot
                interest.updated_at = datetime.now(UTC)
                await self._session.execute(
                    delete(ExtractedEntity).where(ExtractedEntity.user_interest_id == interest.id)
                )
            rows = [
                ExtractedEntity(
                    id=uuid4(),
                    user_interest_id=interest.id,
                    user_id=user_id,
                    entity_label=item.entity_label,
                    entity_type=item.entity_type,
                    confidence=item.confidence,
                    document_id=item.document_id,
                    source_span_id=item.source_span_id,
                    metadata_=item.metadata or {},
                )
                for item in entities
            ]
            self._session.add_all(rows)
        await self._session.refresh(interest)
        persisted = await self.list_extracted_entities(user_id)
        return interest, persisted

    async def record_match_result(
        self,
        user_id: UUID,
        match: NotificationMatchInput,
        *,
        notification_id: UUID | None = None,
    ) -> NotificationMatchResult:
        async with self._session.begin():
            row = NotificationMatchResult(
                id=uuid4(),
                user_id=user_id,
                notification_id=notification_id,
                reference_id=match.reference_id,
                reference_type=match.reference_type,
                match_score=match.match_score,
                match_payload=match.match_payload,
            )
            self._session.add(row)
        await self._session.refresh(row)
        return row

    async def create_notification_with_match(
        self,
        user_id: UUID,
        *,
        type: str,
        message: str,
        reference_id: str | None,
        reference_type: str | None,
        match: NotificationMatchInput,
    ) -> tuple[Notification, NotificationMatchResult]:
        async with self._session.begin():
            notification = Notification(
                id=uuid4(),
                user_id=user_id,
                type=type,
                message=message,
                reference_id=reference_id,
                reference_type=reference_type,
                is_read=False,
            )
            self._session.add(notification)
            await self._session.flush()
            match_row = NotificationMatchResult(
                id=uuid4(),
                user_id=user_id,
                notification_id=notification.id,
                reference_id=match.reference_id,
                reference_type=match.reference_type,
                match_score=match.match_score,
                match_payload=match.match_payload,
            )
            self._session.add(match_row)
        await self._session.refresh(notification)
        await self._session.refresh(match_row)
        return notification, match_row

    async def list_notifications_since(
        self,
        user_id: UUID,
        *,
        since: datetime | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> CursorPage:
        query: Select[tuple[Notification]] = select(Notification).where(Notification.user_id == user_id)
        if cursor is not None:
            cursor_created_at, cursor_id = decode_cursor(cursor)
            query = query.where(
                tuple_(Notification.created_at, Notification.id) > tuple_(cursor_created_at, cursor_id)
            )
        elif since is not None:
            query = query.where(Notification.created_at > since)
        query = query.order_by(Notification.created_at.asc(), Notification.id.asc()).limit(limit + 1)
        result = await self._session.execute(query)
        rows = list(result.scalars().all())
        next_cursor = None
        if len(rows) > limit:
            last = rows[limit - 1]
            next_cursor = encode_cursor(last.created_at, last.id)
            rows = rows[:limit]
        return CursorPage(items=rows, next_cursor=next_cursor)

    async def count_unread(self, user_id: UUID) -> int:
        value = await self._session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        )
        return int(value or 0)

    async def mark_as_read(self, notification_id: UUID, user_id: UUID) -> bool:
        async with self._session.begin():
            result = await self._session.execute(
                update(Notification)
                .where(Notification.id == notification_id, Notification.user_id == user_id)
                .values(is_read=True)
            )
            return bool(result.rowcount)

    async def mark_all_as_read(self, user_id: UUID) -> int:
        async with self._session.begin():
            result = await self._session.execute(
                update(Notification)
                .where(Notification.user_id == user_id, Notification.is_read.is_(False))
                .values(is_read=True)
            )
            return int(result.rowcount or 0)
