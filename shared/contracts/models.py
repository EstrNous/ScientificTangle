import uuid
from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class UserRole(StrEnum):
    ADMIN = "admin"
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    MANAGER = "manager"
    EXTERNAL_PARTNER = "external_partner"


class IngestionTaskStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class StoredSource(BaseModel):
    object_key: str
    original_filename: str
    content_type: str
    size_bytes: int = Field(gt=0)
    sha256: str = Field(min_length=64, max_length=64)


class IngestionReport(BaseModel):
    stage: Literal["uploaded"] = "uploaded"
    sources: list[StoredSource] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class IngestionTaskPayload(BaseModel):
    id: UUID
    status: IngestionTaskStatus
    report: IngestionReport | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class ApiError(BaseModel):
    code: str
    message: str
    request_id: str


class SourceSpan(BaseModel):
    document_id: str
    page: int
    start_offset: int
    end_offset: int
    text: str
    table_block_id: str | None = None
    source_type: Literal["text", "table", "figure", "caption"]


class TableBlock(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    document_id: str
    page: int
    headers: list[str]
    rows: list[list[str]]
    caption: str = ""
    metadata: dict = Field(default_factory=dict)


class Quantity(BaseModel):
    value: float
    unit: str
    operator: Literal["eq", "lt", "le", "gt", "ge", "range"] = "eq"
    range_min: float | None = None
    range_max: float | None = None


class GeoContext(BaseModel):
    location_name: str
    latitude: float | None = None
    longitude: float | None = None
    region: str | None = None


class AccessPolicy(BaseModel):
    level: Literal["public", "internal", "restricted"] = "internal"
    allowed_roles: list[str] = Field(default_factory=list)


class NormalizedDocument(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    source_type: str
    title: str
    content: str
    source_spans: list[SourceSpan] = Field(default_factory=list)
    table_blocks: list[TableBlock] = Field(default_factory=list)
    quantities: list[Quantity] = Field(default_factory=list)
    geo_contexts: list[GeoContext] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    access_policy: AccessPolicy = Field(default_factory=AccessPolicy)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class NormalizeStoredSourcesRequest(BaseModel):
    sources: list[StoredSource] = Field(min_length=1)
    access_policy: AccessPolicy = Field(default_factory=AccessPolicy)


class NormalizeStoredSourcesResponse(BaseModel):
    documents: list[NormalizedDocument] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class StorageWriteResult(BaseModel):
    backend: Literal["neo4j", "qdrant"]
    mode: Literal["mock"] = "mock"
    document_ids: list[str] = Field(default_factory=list)
    records_count: int = Field(default=0, ge=0)
    warnings: list[str] = Field(default_factory=list)


class KnowledgeIngestionRequest(BaseModel):
    document: NormalizedDocument


class KnowledgeIngestionResponse(BaseModel):
    document_id: str
    extraction: dict = Field(default_factory=dict)
    graph_write: StorageWriteResult
    warnings: list[str] = Field(default_factory=list)


class RetrievalIndexRequest(BaseModel):
    documents: list[NormalizedDocument] = Field(min_length=1)
    knowledge_results: list[KnowledgeIngestionResponse] = Field(default_factory=list)


class RetrievalIndexResponse(BaseModel):
    vector_write: StorageWriteResult
    warnings: list[str] = Field(default_factory=list)


class Claim(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    statement: str
    claim_type: str = ""
    confidence: float = 0.0
    source_span_ids: list[str] = Field(default_factory=list)
    entity_ids: list[str] = Field(default_factory=list)
    claim_status: Literal["candidate", "confirmed", "disputed", "deprecated"] = "candidate"
    version: int = 1


class QueryIR(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    raw_query: str
    entities: list[str] = Field(default_factory=list)
    intent: str = ""
    filters: dict = Field(default_factory=dict)
    geo_filter: GeoContext | None = None
    numeric_filter: Quantity | None = None
    source_type_filter: list[str] | None = None
    limit: int = 20
    offset: int = 0


class EvidenceItem(BaseModel):
    source_span: SourceSpan
    relevance_score: float = 0.0
    claim_ids: list[str] = Field(default_factory=list)
    extraction_method: Literal["exact", "semantic", "table", "numeric", "geo"] = "semantic"


class EvidenceBundle(BaseModel):
    query_ir: QueryIR
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
    total_found: int = 0
    has_gaps: bool = False
    has_conflicts: bool = False
    gaps: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)


class AnswerPayload(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    query_ir: QueryIR
    evidence_bundle: EvidenceBundle
    answer_text: str
    confidence: float = 0.0
    sources_count: int = 0
    model_used: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ServiceInfo(BaseModel):
    service_name: str
    version: str = "0.1.0"
    status: Literal["ok", "degraded", "down"] = "ok"
