import logging
from uuid import UUID
from typing import Any
import httpx

from shared.contracts import AuditEventResponse, AuditLogFilter
from app.service.base import BaseService

logger = logging.getLogger(__name__)

class AuditService(BaseService):
    def __init__(self, repository: Any, client: httpx.AsyncClient) -> None:
        # Ему не нужны ссылки на внешние микросервисы, он работает чисто с локальной БД оркестратора
        super().__init__(client)
        self._repo = repository

    async def list_audit_events(
        self, 
        filters: AuditLogFilter, 
        limit: int = 50, 
        offset: int = 0
    ) -> AuditEventResponse:
        """
        Извлекает историю системных событий (логи аудита) с возможностью 
        фильтрации по типу действия, пользователю или временному промежутку.
        """
        events, total_count = await self._repo.get_audit_logs(
            action_type=filters.action_type,
            user_id=filters.user_id,
            status=filters.status,
            start_date=filters.start_date,
            end_date=filters.end_date,
            limit=limit,
            offset=offset
        )
        
        return AuditEventResponse(
            items=events,
            total=total_count,
            limit=limit,
            offset=offset
        )

    async def log_security_event(self, user_id: UUID, action: str, details: dict[str, Any]) -> None:
        """Внутренний хелпер для фиксации критических действий (например, экспорт данных)."""
        try:
            await self._repo.create_audit_entry(
                user_id=user_id,
                action=action,
                details=details,
                status="SUCCESS"
            )
        except Exception as ex:
            # Ошибка записи аудита не должна валить основной бизнес-процесс пользователя
            logger.error(f"Failed to write audit log for user {user_id}, action {action}: {ex}")