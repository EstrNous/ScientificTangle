from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from infra.postgres.chat_ui_db import ChatRepository, get_session

from ..service.analytics_service import AdminService, AnalyticsService
from ..service.chat_service import ChatService
from ..service.graph_service import GraphService
from ..service.service import GatewayService


def get_gateway_service(request: Request) -> GatewayService:
    return request.app.state.gateway_service


def get_graph_service(request: Request) -> GraphService:
    return GraphService(request.app.state.http_client)


def get_analytics_service(request: Request) -> AnalyticsService:
    return AnalyticsService(request.app.state.http_client)


def get_admin_service(request: Request) -> AdminService:
    return AdminService(request.app.state.http_client)


def get_chat_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ChatService:
    return ChatService(
        repository=ChatRepository(session),
        gateway_service=request.app.state.gateway_service,
    )
