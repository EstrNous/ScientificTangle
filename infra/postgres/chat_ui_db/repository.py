from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import ChatSession, ChatMessage

class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_session(self, user_id: UUID, title: str) -> ChatSession:
        session = ChatSession(user_id=user_id, title=title)
        self._session.add(session)
        await self._session.commit()
        await self._session.refresh(session)
        return session

    async def get_messages(self, session_id: UUID) -> list[ChatMessage]:
        result = await self._session.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        return list(result)

    async def save_message(self, session_id: UUID, role: str, content: str, query_run_id: UUID | None = None) -> ChatMessage:
        message = ChatMessage(session_id=session_id, role=role, content=content, query_run_id=query_run_id)
        self._session.add(message)
        await self._session.commit()
        await self._session.refresh(message)
        return message