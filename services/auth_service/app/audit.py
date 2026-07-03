import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AuthAuditEvent:
    action: str
    status: str
    occurred_at: datetime
    user_id: UUID | None = None
    username: str | None = None
    session_id: UUID | None = None
    request_id: str | None = None
    ip_address: str | None = None


class AuthAuditSink(Protocol):
    async def record(self, event: AuthAuditEvent) -> None: ...


class NullAuthAuditSink:
    async def record(self, event: AuthAuditEvent) -> None:
        return None


class LoggingAuthAuditSink:
    def __init__(self) -> None:
        self._logger = logging.getLogger("auth_service.audit")

    async def record(self, event: AuthAuditEvent) -> None:
        self._logger.info(json.dumps(asdict(event), default=str, separators=(",", ":")))
