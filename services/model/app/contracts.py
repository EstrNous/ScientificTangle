import uuid
from typing import Any, Literal, Self

from pydantic import BaseModel, Field, model_validator

from shared.contracts import (
    AccessPolicy,
    AnswerPayload,
    EvidenceBundle,
    EvidenceItem,
    NormalizedDocument,
    QueryIR,
    SourceSpan,
)

CONFIRMED_MIN_CONFIDENCE = 0.72

CandidateReasonCode = Literal[
    "missing_source_span",
    "low_confidence",
    "ambiguous_alias",
    "conflicting_values",
    "needs_unit_check",
    "access_filtered",
    "schema_candidate",
]
ClaimStatus = Literal["confirmed", "candidate", "disputed", "deprecated"]
ArtifactKind = Literal[
    "entity",
    "alias",
    "measurement",
    "relation",
    "claim",
    "recommendation",
    "material",
    "substance",
    "process",
    "equipment",
    "property",
    "date",
    "geography",
    "expert",
    "source",
    "conclusion",
]
ModelMode = Literal["deterministic_degraded", "llm"]


class DocumentProfileSuggestion(BaseModel):
    source_type: str
    document_purpose: Literal[
        "research_article",
        "technical_report",
        "patent",
        "regulation",
        "experiment_log",
        "unknown",
    ] = "unknown"
    access_policy_suggestion: AccessPolicy = Field(default_factory=AccessPolicy)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class ExtractionArtifact(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    kind: ArtifactKind
    value: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    status: ClaimStatus
    source_span_ids: list[str] = Field(default_factory=list)
    source_spans: list[SourceSpan] = Field(default_factory=list)
    reason_codes: list[CandidateReasonCode] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def enforce_evidence_first_status(self) -> Self:
        if self.status == "confirmed":
            if not self.source_span_ids or not self.source_spans:
                raise ValueError("confirmed artifacts require SourceSpan evidence")
            if self.confidence < CONFIRMED_MIN_CONFIDENCE:
                raise ValueError("confirmed artifacts require sufficient confidence")
            if self.reason_codes:
                raise ValueError("confirmed artifacts cannot carry candidate reason codes")
        elif not self.reason_codes:
            raise ValueError("candidate-like artifacts require reason codes")
        return self


class UnsupportedWarning(BaseModel):
    statement: str = Field(min_length=1)
    reason_codes: list[CandidateReasonCode] = Field(default_factory=list)
    source_span_ids: list[str] = Field(default_factory=list)


class StructuredExtractionRequest(BaseModel):
    document: NormalizedDocument
    confirmed_confidence_threshold: float = Field(default=CONFIRMED_MIN_CONFIDENCE, ge=0.0, le=1.0)
    max_artifacts: int = Field(default=120, ge=1, le=500)


class StructuredExtractionResponse(BaseModel):
    schema_version: str = "structured_extraction.v1"
    prompt_version: str = "structured_extraction.v1"
    mode: ModelMode = "deterministic_degraded"
    document_id: str
    profile: DocumentProfileSuggestion
    confirmed: list[ExtractionArtifact] = Field(default_factory=list)
    candidates: list[ExtractionArtifact] = Field(default_factory=list)
    unsupported_warnings: list[UnsupportedWarning] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def enforce_layer_split(self) -> Self:
        if any(item.status != "confirmed" for item in self.confirmed):
            raise ValueError("confirmed layer accepts only confirmed artifacts")
        if any(item.status == "confirmed" for item in self.candidates):
            raise ValueError("candidate layer cannot contain confirmed artifacts")
        return self


class EmbeddingRequest(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=256)
    dimensions: int = Field(default=256, ge=4, le=768)
    model_name: str = "deterministic-hash-v1"
    input_type: Literal["document", "query"] = "document"


class EmbeddingItem(BaseModel):
    index: int
    text: str
    vector: list[float]


class EmbeddingResponse(BaseModel):
    schema_version: str = "embeddings.v1"
    prompt_version: str = "embeddings.v1"
    mode: ModelMode = "deterministic_degraded"
    model_name: str
    dimensions: int
    embeddings: list[EmbeddingItem]
    warnings: list[str] = Field(default_factory=list)


class QueryIRBuildRequest(BaseModel):
    raw_query: str = Field(min_length=1)
    limit: int = Field(default=20, ge=1, le=100)


class QueryIRBuildResponse(BaseModel):
    schema_version: str = "query_ir.v1"
    prompt_version: str = "query_ir.v1"
    mode: ModelMode = "deterministic_degraded"
    query_ir: QueryIR
    constraints: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class RerankRequest(BaseModel):
    query_ir: QueryIR
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
    limit: int = Field(default=20, ge=1, le=100)


class ScoredEvidenceItem(BaseModel):
    rank: int = Field(ge=1)
    score: float = Field(ge=0.0, le=1.0)
    evidence_item: EvidenceItem
    reasons: list[str] = Field(default_factory=list)


class RerankResponse(BaseModel):
    schema_version: str = "rerank.v1"
    prompt_version: str = "rerank.v1"
    mode: ModelMode = "deterministic_degraded"
    scored_items: list[ScoredEvidenceItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AnswerSynthesisRequest(BaseModel):
    query_ir: QueryIR
    evidence_bundle: EvidenceBundle
    candidate_items: list[ExtractionArtifact] = Field(default_factory=list)


class AnswerSynthesisResponse(BaseModel):
    schema_version: str = "answer_synthesis.v1"
    prompt_version: str = "answer_synthesis.v1"
    mode: ModelMode = "deterministic_degraded"
    answer: AnswerPayload
    unsupported_warnings: list[UnsupportedWarning] = Field(default_factory=list)
    candidate_count: int = 0
    warnings: list[str] = Field(default_factory=list)


class ConflictDetectionRequest(BaseModel):
    artifacts: list[ExtractionArtifact] = Field(default_factory=list)


class ConflictSignal(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    value_key: str
    artifact_ids: list[str] = Field(default_factory=list)
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)


class ConflictDetectionResponse(BaseModel):
    schema_version: str = "conflict_detection.v1"
    prompt_version: str = "conflict_detection.v1"
    mode: ModelMode = "deterministic_degraded"
    conflicts: list[ConflictSignal] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class GapSuggestionRequest(BaseModel):
    query_ir: QueryIR
    evidence_bundle: EvidenceBundle
    candidates: list[ExtractionArtifact] = Field(default_factory=list)


class GapSuggestion(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    gap_type: Literal["missing_evidence", "missing_numeric_constraint", "missing_geo", "missing_time", "conflict_review", "candidate_review"]
    description: str
    priority: Literal["low", "medium", "high"] = "medium"
    related_candidate_ids: list[str] = Field(default_factory=list)


class GapSuggestionResponse(BaseModel):
    schema_version: str = "gap_suggestions.v1"
    prompt_version: str = "gap_suggestions.v1"
    mode: ModelMode = "deterministic_degraded"
    gaps: list[GapSuggestion] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class UserInterestExtractionRequest(BaseModel):
    text: str = Field(min_length=1)


class UserInterest(BaseModel):
    label: str
    weight: float = Field(ge=0.0, le=1.0)
    source_terms: list[str] = Field(default_factory=list)


class UserInterestExtractionResponse(BaseModel):
    schema_version: str = "user_interests.v1"
    prompt_version: str = "user_interests.v1"
    mode: ModelMode = "deterministic_degraded"
    interests: list[UserInterest] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class NotificationMatchRequest(BaseModel):
    interests: list[UserInterest] = Field(default_factory=list)
    artifacts: list[ExtractionArtifact] = Field(default_factory=list)


class NotificationMatch(BaseModel):
    interest_label: str
    artifact_id: str
    score: float = Field(ge=0.0, le=1.0)
    reason: str


class NotificationMatchResponse(BaseModel):
    schema_version: str = "notification_matching.v1"
    prompt_version: str = "notification_matching.v1"
    mode: ModelMode = "deterministic_degraded"
    matches: list[NotificationMatch] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class JsonLdEnrichmentRequest(BaseModel):
    answer: AnswerPayload


class JsonLdEnrichmentResponse(BaseModel):
    schema_version: str = "jsonld_enrichment.v1"
    prompt_version: str = "jsonld_enrichment.v1"
    mode: ModelMode = "deterministic_degraded"
    jsonld: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)


class ModelStatusResponse(BaseModel):
    provider: str
    yandex_configured: bool
    chat_model: str
    embedding_doc_model: str
    embedding_query_model: str
    embedding_dimensions: int
    mode: ModelMode


class SchemaEntry(BaseModel):
    name: str
    version: str
    json_schema: dict[str, Any]


class SchemaRegistryResponse(BaseModel):
    schemas: list[SchemaEntry]


class PromptEntry(BaseModel):
    name: str
    version: str
    text: str


class PromptRegistryResponse(BaseModel):
    prompts: list[PromptEntry]
