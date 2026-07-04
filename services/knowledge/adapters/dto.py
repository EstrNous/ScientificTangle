from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ClaimStatus = Literal[
    "extracted",
    "candidate",
    "auto_verified",
    "verified",
    "conflicting",
    "deprecated",
    "rejected",
]

EntityID = str


class SourceSpanDTO(BaseModel):
    source_span_id: str
    document_id: str
    page_number: int
    raw_text: str
    char_start: int
    char_end: int
    source_type: str = "text"
    table_block_id: str | None = None


class ClaimDTO(BaseModel):
    claim_id: str
    claim_version: int = 1
    status: ClaimStatus = "extracted"
    confidence: float = 0.0
    statement: str = ""
    experiment_performed_at: str | None = None
    source_published_at: str | None = None
    claim_extracted_at: str | None = None
    claim_last_updated_at: str | None = None
    latest_supporting_evidence_date: str | None = None
    supersedes_claim_id: str | None = None
    updated_reason: str | None = None
    source_span_ids: list[str] = Field(default_factory=list)
    entity_ids: list[str] = Field(default_factory=list)
    measurement_ids: list[str] = Field(default_factory=list)
    geo_ids: list[str] = Field(default_factory=list)
    semantic_relations: list[dict[str, str]] = Field(default_factory=list)
    observation_id: str | None = None


class EntityDTO(BaseModel):
    entity_id: str
    canonical_name: str
    domain_type: str
    created_at: str | None = None


class AliasDTO(BaseModel):
    alias_id: str
    name: str
    type: str = "synonym"
    confidence: float = 1.0
    entity_id: str


class MeasurementDTO(BaseModel):
    measurement_id: str
    raw_text: str = ""
    operator: str = "eq"
    value: float | None = None
    min: float | None = None
    max: float | None = None
    unit: str = ""
    normalized_value: float | None = None
    normalized_unit: str = ""
    uncertainty: float | None = None
    dimension: str = ""


class DocumentDTO(BaseModel):
    document_id: str
    title: str
    source_type: str
    access_level: str = "internal"
    language: str = "ru"


class GeographyDTO(BaseModel):
    geo_id: str
    name: str
    type: str = "region"
    precision: str = "unknown"


class ObservationDTO(BaseModel):
    observation_id: str
    description: str
    context_raw: str = ""


class ExperimentDTO(BaseModel):
    experiment_id: str
    description: str = ""
    performed_at: str | None = None


class ReviewDecisionDTO(BaseModel):
    decision_id: str
    reviewer_id: str = "system"
    status: str = "pending"
    comment: str = ""
    decided_at: str | None = None
    claim_id: str | None = None


class ClaimsBundleDTO(BaseModel):
    claims: list[ClaimDTO] = Field(default_factory=list)
    spans: list[SourceSpanDTO] = Field(default_factory=list)
    entities: list[EntityDTO] = Field(default_factory=list)
    aliases: list[AliasDTO] = Field(default_factory=list)
    measurements: list[MeasurementDTO] = Field(default_factory=list)
    documents: list[DocumentDTO] = Field(default_factory=list)
    geographies: list[GeographyDTO] = Field(default_factory=list)
    observations: list[ObservationDTO] = Field(default_factory=list)
    experiments: list[ExperimentDTO] = Field(default_factory=list)
    candidate_entities: list[dict[str, Any]] = Field(default_factory=list)
    candidate_relations: list[dict[str, Any]] = Field(default_factory=list)
    candidate_classes: list[dict[str, Any]] = Field(default_factory=list)
    review_decisions: list[ReviewDecisionDTO] = Field(default_factory=list)


class ConflictDTO(BaseModel):
    conflict_id: str
    entity_id: str
    claim_ids: list[str] = Field(default_factory=list)
    measurement_ids: list[str] = Field(default_factory=list)
    reason: str
    confidence: float = 0.0


class GapDTO(BaseModel):
    gap_id: str
    domain_profile: str
    description: str
    expected_relation: str = ""
    entity_ids: list[str] = Field(default_factory=list)
    priority: Literal["low", "medium", "high"] = "medium"


class GraphNodeDTO(BaseModel):
    id: str
    label: str
    node_type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdgeDTO(BaseModel):
    id: str
    source: str
    target: str
    edge_type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphSubgraphDTO(BaseModel):
    nodes: list[GraphNodeDTO] = Field(default_factory=list)
    edges: list[GraphEdgeDTO] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    source_span_ids: list[str] = Field(default_factory=list)


class GraphNeighborhood(BaseModel):
    center_entity_id: str
    depth: int
    nodes: list[GraphNodeDTO] = Field(default_factory=list)
    edges: list[GraphEdgeDTO] = Field(default_factory=list)


class QueryPlanStep(BaseModel):
    operation: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class QueryPlan(BaseModel):
    steps: list[QueryPlanStep] = Field(default_factory=list)
    access_levels: list[str] = Field(default_factory=list)
    entity_hints: list[str] = Field(default_factory=list)
    limit: int = 50


class RankedClaimDTO(BaseModel):
    claim_id: str
    score: float
    status: ClaimStatus
    confidence: float
    source_span_ids: list[str] = Field(default_factory=list)


class EvidenceRecordDTO(BaseModel):
    claim_id: str
    statement: str
    confidence: float
    status: ClaimStatus
    source_span: SourceSpanDTO | None = None
    document_id: str | None = None
    access_level: str | None = None


class MeasurementAggregateDTO(BaseModel):
    group_key: str
    count: int
    avg_value: float | None = None
    min_value: float | None = None
    max_value: float | None = None
    unit: str = ""


class GroupComparisonDTO(BaseModel):
    group_a_key: str
    group_b_key: str
    group_a_avg: float | None = None
    group_b_avg: float | None = None
    delta: float | None = None
    unit: str = ""


class FactVersionDTO(BaseModel):
    fact_version_id: str
    claim_id: str
    version: int
    status: str
    recorded_at: str | None = None


class FactVersionHistoryDTO(BaseModel):
    claim_id: str
    claim_version: int
    status: str
    versions: list[FactVersionDTO] = Field(default_factory=list)
    superseded_claim_ids: list[str] = Field(default_factory=list)


class NeighborhoodFallbackResultDTO(BaseModel):
    evidence: list[EvidenceRecordDTO] = Field(default_factory=list)
    used_fallback: bool = False
    expanded_entity_ids: list[str] = Field(default_factory=list)


class BootstrapResultDTO(BaseModel):
    schema_version: str
    seeded_entity_types: int = 0
    seeded_relation_types: int = 0
    seeded_validation_rules: int = 0
    seeded_aliases: int = 0
    applied: dict[str, int] = Field(default_factory=dict)
