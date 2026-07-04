import hashlib
import uuid
from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class QueryRunStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskKind(StrEnum):
    DOCUMENT_INGESTION = "document_ingestion"
    DICTIONARY_INGESTION = "dictionary_ingestion"


class DictionaryVersionStatus(StrEnum):
    VALIDATED = "validated"
    VALIDATION_FAILED = "validation_failed"
    ACTIVE = "active"
    INACTIVE = "inactive"


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
    normalized_documents: list["NormalizedDocument"] = Field(default_factory=list)
    documents_count: int = 0
    source_spans_count: int = 0
    tables_count: int = 0
    indexed_points_count: int = 0
    extracted_claims_count: int = 0
    candidates_count: int = 0


class DictionaryFilePayload(BaseModel):
    path: str
    kind: Literal["entities", "aliases", "units", "geographies"]
    sha256: str = Field(min_length=64, max_length=64)
    entries: list[dict] = Field(default_factory=list)


class DictionaryPackagePayload(BaseModel):
    schema_version: Literal["dictionary-package.v1"] = "dictionary-package.v1"
    version: str = Field(min_length=1, max_length=128)
    package_sha256: str = Field(min_length=64, max_length=64)
    source: StoredSource
    files: list[DictionaryFilePayload] = Field(min_length=1)


class DictionaryIngestionReport(BaseModel):
    stage: Literal["dictionary"] = "dictionary"
    dictionary_version_id: UUID | None = None
    version: str = ""
    package_sha256: str = ""
    files_count: int = 0
    entries_count: int = 0
    warnings: list[str] = Field(default_factory=list)


class DictionaryVersionPayload(BaseModel):
    id: UUID
    version: str
    package_sha256: str
    status: DictionaryVersionStatus
    files: list[DictionaryFilePayload] = Field(default_factory=list)
    uploaded_by: UUID
    created_at: datetime
    activated_at: datetime | None = None


class IngestionTaskPayload(BaseModel):
    id: UUID
    status: IngestionTaskStatus
    task_kind: TaskKind = TaskKind.DOCUMENT_INGESTION
    dictionary_version_id: UUID | None = None
    report: IngestionReport | DictionaryIngestionReport | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class ApiError(BaseModel):
    code: str
    message: str
    request_id: str
    query_run_id: UUID | None = None


class SourceSpan(BaseModel):
    id: str
    document_id: str
    page: int
    start_offset: int
    end_offset: int
    text: str
    table_block_id: str | None = None
    source_type: Literal["text", "table", "figure", "caption"]

    @model_validator(mode="before")
    @classmethod
    def ensure_id(cls, value: object) -> object:
        if not isinstance(value, dict) or value.get("id"):
            return value
        raw = (
            f"{value.get('document_id', '')}:{value.get('page', '')}:"
            f"{value.get('start_offset', '')}:{value.get('end_offset', '')}:"
            f"{value.get('table_block_id') or ''}"
        )
        return {**value, "id": hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]}


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
    mode: Literal["mock", "live", "adapter_pending"] = "mock"
    document_ids: list[str] = Field(default_factory=list)
    records_count: int = Field(default=0, ge=0)
    confirmed_count: int = Field(default=0, ge=0)
    claim_ids: list[str] = Field(default_factory=list)
    graph_entity_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class KnowledgeIngestionRequest(BaseModel):
    document: NormalizedDocument
    dictionary_version_id: UUID | None = None


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
    entity_ids: list[str] = Field(default_factory=list)
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


class QueryRunResponse(BaseModel):
    query_run_id: str
    query_ir: QueryIR
    evidence_bundle: EvidenceBundle
    answer: AnswerPayload
    unsupported_warnings: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ExportRequest(BaseModel):
    query_run_id: UUID
    format: Literal["markdown", "json"]


class ExportPayload(BaseModel):
    export_job_id: UUID
    query_run_id: UUID
    format: Literal["markdown", "json"]
    status: QueryRunStatus
    content_type: str
    content: str | dict
    file_url: str = ""
    warnings: list[str] = Field(default_factory=list)
    generated_at: datetime


class GraphNode(BaseModel):
    id: str
    label: str
    type: str


class GraphLink(BaseModel):
    source: str
    target: str
    type: str


class GraphSubgraph(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    links: list[GraphLink] = Field(default_factory=list)


class SourcePayload(BaseModel):
    source_span: SourceSpan
    document_title: str
    source_type: str
    metadata: dict = Field(default_factory=dict)
    access_policy: AccessPolicy


class SearchResult(BaseModel):
    source: SourcePayload
    relevance_score: float = 0.0
    claim_ids: list[str] = Field(default_factory=list)
    entity_ids: list[str] = Field(default_factory=list)


class SearchResultPayload(BaseModel):
    items: list[SearchResult] = Field(default_factory=list)
    total_found: int = 0
    warnings: list[str] = Field(default_factory=list)


class QueryRunPayload(BaseModel):
    id: UUID
    status: QueryRunStatus
    question: str
    query_ir: QueryIR | None = None
    evidence_bundle: EvidenceBundle | None = None
    answer: AnswerPayload | None = None
    graph_subgraph: GraphSubgraph = Field(default_factory=GraphSubgraph)
    retrieval_trace: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
    request_id: str
    latency_ms: int | None = None
    dictionary_version_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class GraphEntity(BaseModel):
    id: str
    name: str
    type: str
    status: str


class GraphCandidate(BaseModel):
    id: str
    name: str
    type: str
    confidence: float = Field(ge=0.0, le=1.0)


class NodeCombinationRow(BaseModel):
    model_config = ConfigDict(extra="allow")


class NodeCombinationGroup(BaseModel):
    group: str = ""
    rows: list[dict] = Field(default_factory=list)


class GraphPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    knowledge_graph: GraphSubgraph = Field(default_factory=GraphSubgraph, alias="knowledgeGraph")
    subgraph: GraphSubgraph = Field(default_factory=GraphSubgraph)
    entities: list[GraphEntity] = Field(default_factory=list)
    candidates: list[GraphCandidate] = Field(default_factory=list)
    node_combinations: list[NodeCombinationGroup] = Field(default_factory=list, alias="nodeCombinations")


class SearchResultItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    material: str
    process: str
    year: int | None = None
    geo: str = ""
    geo_key: str = Field(default="", alias="geoKey")


class SearchResultsPayload(BaseModel):
    items: list[SearchResultItem] = Field(default_factory=list)


class AuditEvent(BaseModel):
    id: str
    user: str = ""
    user_id: str = ""
    role: str = ""
    action: str
    status: str = ""
    object: str = ""
    resource_type: str = ""
    resource_id: str = ""
    request_id: str = ""
    timestamp: str = ""
    details: dict = Field(default_factory=dict)
    source_span_id: str | None = None


class StrategicDirection(BaseModel):
    id: str
    name: str
    coverage: float = Field(ge=0.0, le=1.0)
    documents: int = 0


class StrategicMetricsPayload(BaseModel):
    updated_at: str = ""
    directions: list[StrategicDirection] = Field(default_factory=list)
    totals: dict[str, int] = Field(default_factory=dict)
    low_coverage_topics: list[str] = Field(default_factory=list)
    high_conflict_topics: list[str] = Field(default_factory=list)
    metric_sources: dict[str, list[str]] = Field(default_factory=dict)


class StrategicEvaluationQuestion(BaseModel):
    id: str
    text: str
    status: str = "warn"
    expected_sources: int = 0
    actual_sources: int = 0
    missing_evidence: int = 0
    unsupported_claims: int = 0
    latency_ms: int = 0
    citation_coverage: float = 0.0
    numeric_correctness: float = 0.0
    sources: list[str] = Field(default_factory=list)


class StrategicEvaluationSummary(BaseModel):
    avg_citation_coverage: float = 0.0
    avg_numeric_correctness: float = 0.0
    avg_latency_ms: int = 0
    unsupported_claim_rate: float = 0.0
    entity_linking_f1: float = 0.0
    evidence_recall_at_5: float = 0.0


class StrategicEvaluationPayload(BaseModel):
    summary: StrategicEvaluationSummary = Field(default_factory=StrategicEvaluationSummary)
    questions: list[StrategicEvaluationQuestion] = Field(default_factory=list)


class LabGap(BaseModel):
    id: str
    title: str
    description: str
    constraints: list[str] = Field(default_factory=list)
    related_cases: list[dict] = Field(default_factory=list)
    experts: list[str] = Field(default_factory=list)


class LabContradiction(BaseModel):
    id: str
    process: str
    claim_a: str
    claim_b: str
    condition_a: str
    condition_b: str
    source_a: str
    source_b: str
    risk: Literal["high", "medium", "low"] = "medium"


class LabMatrixView(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    row_type: str = Field(alias="rowType")
    col_type: str = Field(alias="colType")
    rows: list[str] = Field(default_factory=list)
    cols: list[str] = Field(default_factory=list)
    matrix: list[list[int]] = Field(default_factory=list)
    cell_sources: list[list[list[str]]] = Field(default_factory=list, alias="cellSources")


class LabCoveragePayload(BaseModel):
    summary: dict[str, int] = Field(default_factory=dict)
    matrices: dict[str, LabMatrixView] = Field(default_factory=dict)
    gaps: list[LabGap] = Field(default_factory=list)
    contradictions: list[LabContradiction] = Field(default_factory=list)
    coverage: dict | None = None


class ServiceInfo(BaseModel):
    service_name: str
    version: str = "0.1.0"
    status: Literal["ok", "degraded", "down"] = "ok"
