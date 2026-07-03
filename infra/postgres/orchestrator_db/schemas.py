from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from .models import IngestionStatus, QueryRunStatus

# Модели для IngestionTask
class IngestionTaskCreate(BaseModel):
    user_id: UUID

class IngestionTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    status: IngestionStatus
    report: dict[str, Any] | None = None

# Модели для QueryRun
class QueryRunCreate(BaseModel):
    user_id: UUID
    query_ir: dict[str, Any] | None = None

class QueryRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    status: QueryRunStatus
    query_ir: dict[str, Any] | None = None
    latency_ms: int | None = None

# Модель для обновления статусов (универсальная)
class StatusUpdate(BaseModel):
    status: IngestionStatus | QueryRunStatus