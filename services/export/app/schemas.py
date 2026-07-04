from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from shared.contracts import AnswerPayload


class ExportArtifactMeta(BaseModel):
    artifact_kind: str
    bucket_name: str
    storage_key: str
    content_type: str
    byte_size: int
    checksum: str
    file_url: str


class ExportJobCreateRequest(BaseModel):
    job_id: UUID
    user_id: UUID
    query_run_id: UUID
    format: Literal["markdown", "json", "jsonld"]
    document: dict[str, Any]
    answer: AnswerPayload | None = None


class ExportJobProcessResponse(BaseModel):
    job_id: UUID
    status: Literal["completed", "failed"]
    format: str
    artifacts: list[ExportArtifactMeta] = Field(default_factory=list)
    content: str | dict | None = None
    content_type: str = ""
    warnings: list[str] = Field(default_factory=list)
    error_message: str | None = None


class ExportJobStatusResponse(BaseModel):
    job_id: UUID
    user_id: UUID
    query_run_id: UUID
    format: str
    status: Literal["pending", "processing", "completed", "failed"]
    artifacts: list[ExportArtifactMeta] = Field(default_factory=list)
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
