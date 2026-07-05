from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ChatMessage, ChatSession


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_sessions(self, user_id: UUID) -> list[ChatSession]:
        result = await self._session.scalars(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
        )
        return list(result)

    async def get_session(self, session_id: UUID, user_id: UUID) -> ChatSession | None:
        return await self._session.scalar(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
            )
        )

    async def create_session(self, user_id: UUID, title: str) -> ChatSession:
        session = ChatSession(user_id=user_id, title=title)
        self._session.add(session)
        await self._session.commit()
        await self._session.refresh(session)
        return session

    async def delete_session(self, session_id: UUID, user_id: UUID) -> bool:
        session = await self.get_session(session_id, user_id)
        if session is None:
            return False
        await self._session.delete(session)
        await self._session.commit()
        return True

    async def get_messages(self, session_id: UUID) -> list[ChatMessage]:
        result = await self._session.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        return list(result)

    async def save_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
        query_run_id: UUID | None = None,
    ) -> ChatMessage:
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            query_run_id=query_run_id,
        )
        self._session.add(message)
        await self._session.execute(
            update(ChatSession)
            .where(ChatSession.id == session_id)
            .values(updated_at=func.now())
        )
        await self._session.commit()
        await self._session.refresh(message)
        return message

    async def delete_message(self, message_id: UUID) -> None:
        message = await self._session.get(ChatMessage, message_id)
        if message is None:
            return
        await self._session.delete(message)
        await self._session.commit()
