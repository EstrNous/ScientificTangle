from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from infra.postgres.chat_ui_db import ChatRepository, get_session

from ..service.chat_service import ChatService
from ..service.graph_service import GraphService
from ..service.service import GatewayService


def get_gateway_service(request: Request) -> GatewayService:
    return request.app.state.gateway_service


def get_graph_service() -> GraphService:
    return GraphService()


def get_chat_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ChatService:
    return ChatService(
        repository=ChatRepository(session),
        gateway_service=request.app.state.gateway_service,
    )
