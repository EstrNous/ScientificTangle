from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from infra.postgres.notification_db import SqlAlchemyNotificationRepository, NotificationWorkflowRepository
from infra.postgres.notification_db.database import get_session

from ..service.matching_service import MatchingService
from ..service.notification_service import NotificationService


def get_notification_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> NotificationService:
    return NotificationService(
        SqlAlchemyNotificationRepository(session),
        client=request.app.state.http_client,
    )


def get_matching_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MatchingService:
    repository = SqlAlchemyNotificationRepository(session)
    return MatchingService(
        repository,
        NotificationWorkflowRepository(session),
        client=request.app.state.http_client,
    )
