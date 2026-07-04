import json
from uuid import UUID

from shared.contracts import AuditEvent

from infra.postgres.orchestrator_db import IngestionTaskRepository, QueryRunRepository


class AuditService:
    def __init__(
        self,
        repository: IngestionTaskRepository | QueryRunRepository | None = None,
        query_repository: QueryRunRepository | None = None,
    ) -> None:
        self._repository = query_repository or repository

    async def list_audit_events(
        self,
        limit: int = 200,
        offset: int = 0,
        action: str | None = None,
        user_id: UUID | None = None,
    ) -> list[AuditEvent]:
        if self._repository is None:
            return []
        rows = await self._repository.list_audit_events(
            limit=limit,
            offset=offset,
            action=action,
            user_id=user_id,
        )
        events = []
        for row in rows:
            details = row.get("details") or {}
            if isinstance(details, str):
                try:
                    details = json.loads(details)
                except (TypeError, ValueError):
                    details = {}
            events.append(
                AuditEvent(
                    id=str(row["id"]),
                    user=str(row.get("user_id") or ""),
                    user_id=str(row.get("user_id") or ""),
                    role=str(details.get("role") or ""),
                    action=str(row["action"]),
                    object=str(row.get("resource_id") or ""),
                    status=str(details.get("status") or ""),
                    resource_type=str(row.get("resource_type") or ""),
                    resource_id=str(row.get("resource_id") or ""),
                    request_id=str(row.get("request_id") or ""),
                    timestamp=row["created_at"].isoformat() if row.get("created_at") else "",
                    details=details if isinstance(details, dict) else {},
                    source_span_id=details.get("source_span_id"),
                )
            )
        return events
