from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from shared.contracts import NormalizedDocument, SourceSpan
from shared.utils.source_span import compute_source_span_id

from .dto import (
    AliasDTO,
    ClaimDTO,
    ClaimsBundleDTO,
    DocumentDTO,
    EntityDTO,
    GeographyDTO,
    MeasurementDTO,
    ObservationDTO,
    ReviewDecisionDTO,
    SourceSpanDTO,
)

ENTITY_KINDS = {
    "entity",
    "material",
    "substance",
    "process",
    "equipment",
    "property",
    "expert",
    "source",
}
SEMANTIC_RELATION_MAP = {
    "relation": "USES_MATERIAL",
    "material": "USES_MATERIAL",
    "process": "OPERATES_AT_CONDITION",
    "equipment": "USES_EQUIPMENT",
    "property": "PRODUCES_OUTPUT",
    "expert": "EXPERT_IN",
    "geography": "APPLIED_IN_GEOGRAPHY",
}
NUMBER_PATTERN = re.compile(r"[-+]?\d+(?:[,.]\d+)?")


def entity_id_for_name(name: str, domain_type: str) -> str:
    raw = f"{domain_type}:{name.strip().lower()}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def map_source_span(span: SourceSpan) -> SourceSpanDTO:
    table_row_id = span.table_block_id if span.table_block_id and ":row:" in span.table_block_id else None
    return SourceSpanDTO(
        source_span_id=compute_source_span_id(span),
        document_id=span.document_id,
        page_number=span.page,
        raw_text=span.text,
        char_start=span.start_offset,
        char_end=span.end_offset,
        source_type=span.source_type,
        table_block_id=span.table_block_id,
        table_row_id=table_row_id,
        highlight_start=span.start_offset,
        highlight_end=span.end_offset,
    )


def map_document(document: NormalizedDocument) -> DocumentDTO:
    return DocumentDTO(
        document_id=document.id,
        title=document.title,
        source_type=document.source_type,
        access_level=document.access_policy.level,
        language=str(document.metadata.get("language", "ru")),
    )


def map_claim_status(status: str, confidence: float) -> str:
    if status == "confirmed":
        return "auto_verified" if confidence < 0.9 else "verified"
    if status == "disputed":
        return "conflicting"
    if status == "deprecated":
        return "deprecated"
    return "candidate"


def parse_measurement(value: str) -> MeasurementDTO:
    measurement_id = uuid.uuid4().hex[:16]
    match = NUMBER_PATTERN.search(value)
    numeric = float(match.group(0).replace(",", ".")) if match else None
    unit = value.replace(match.group(0), "").strip() if match else ""
    return MeasurementDTO(
        measurement_id=measurement_id,
        raw_text=value,
        value=numeric,
        unit=unit,
        normalized_value=numeric,
        normalized_unit=unit,
    )


def artifacts_to_bundle(document: NormalizedDocument, extraction: dict[str, Any]) -> ClaimsBundleDTO:
    bundle = ClaimsBundleDTO()
    bundle.documents.append(map_document(document))
    span_map = {compute_source_span_id(span): map_source_span(span) for span in document.source_spans}
    bundle.spans.extend(span_map.values())
    entity_index: dict[str, str] = {}
    timestamp = now_iso()

    def ensure_entity(name: str, domain_type: str) -> str:
        key = name.strip().lower()
        if key not in entity_index:
            entity_id = entity_id_for_name(name, domain_type)
            entity_index[key] = entity_id
            bundle.entities.append(
                EntityDTO(
                    entity_id=entity_id,
                    canonical_name=name.strip(),
                    domain_type=domain_type,
                    created_at=timestamp,
                )
            )
        return entity_index[key]

    for artifact in [*extraction.get("confirmed", []), *extraction.get("candidates", [])]:
        kind = str(artifact.get("kind", "entity"))
        value = str(artifact.get("value", "")).strip()
        if not value:
            continue
        status = map_claim_status(str(artifact.get("status", "candidate")), float(artifact.get("confidence", 0.0)))
        source_span_ids = [str(item) for item in artifact.get("source_span_ids", [])]
        metadata = artifact.get("metadata", {}) if isinstance(artifact.get("metadata"), dict) else {}
        artifact_id = str(artifact.get("id", uuid.uuid4().hex))

        if kind == "relation":
            bundle.candidate_relations.append(
                {
                    "candidate_id": artifact_id[:16],
                    "raw_data": value,
                    "extracted_at": timestamp,
                    "relation_type": str(metadata.get("relation_type", "unknown")),
                }
            )
            continue

        if kind == "review_decision":
            bundle.review_decisions.append(
                ReviewDecisionDTO(
                    decision_id=artifact_id[:16],
                    reviewer_id=str(metadata.get("reviewer_id", "system")),
                    status=str(metadata.get("status", artifact.get("status", "pending"))),
                    comment=str(metadata.get("comment", value)),
                    decided_at=timestamp,
                    claim_id=str(metadata.get("claim_id")) if metadata.get("claim_id") else None,
                )
            )
            continue

        if kind in {"conclusion", "recommendation"} and str(artifact.get("status", "candidate")) != "confirmed":
            observation_id = artifact_id[:16]
            bundle.observations.append(
                ObservationDTO(
                    observation_id=observation_id,
                    description=value,
                    context_raw=str(metadata.get("context_raw", "")),
                )
            )
            bundle.claims.append(
                ClaimDTO(
                    claim_id=uuid.uuid4().hex[:16],
                    status="candidate",
                    confidence=float(artifact.get("confidence", 0.0)),
                    statement=value,
                    claim_extracted_at=timestamp,
                    claim_last_updated_at=timestamp,
                    source_span_ids=source_span_ids,
                    observation_id=observation_id,
                )
            )
            continue

        if kind == "alias":
            target_name = str(metadata.get("canonical", value))
            entity_id = ensure_entity(target_name, "Material")
            bundle.aliases.append(
                AliasDTO(
                    alias_id=artifact_id[:16],
                    name=value,
                    entity_id=entity_id,
                    confidence=float(artifact.get("confidence", 0.0)),
                )
            )
            continue

        if kind == "geography":
            geo_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"geo:{value}").hex[:16]
            bundle.geographies.append(
                GeographyDTO(
                    geo_id=geo_id,
                    name=value,
                    type=str(metadata.get("geo_type", "region")),
                    precision=str(metadata.get("precision", "unknown")),
                )
            )
            if source_span_ids:
                claim_id = artifact_id[:16]
                bundle.claims.append(
                    ClaimDTO(
                        claim_id=claim_id,
                        status=status if status in {"verified", "auto_verified", "candidate"} else "candidate",
                        confidence=float(artifact.get("confidence", 0.0)),
                        statement=value,
                        claim_extracted_at=timestamp,
                        claim_last_updated_at=timestamp,
                        source_span_ids=source_span_ids,
                        geo_ids=[geo_id],
                        semantic_relations=[{"type": "APPLIED_IN_GEOGRAPHY", "target_id": geo_id}],
                    )
                )
            continue

        if kind == "measurement":
            measurement = parse_measurement(value)
            measurement.measurement_id = artifact_id[:16]
            bundle.measurements.append(measurement)
            if source_span_ids:
                claim_id = uuid.uuid4().hex[:16]
                bundle.claims.append(
                    ClaimDTO(
                        claim_id=claim_id,
                        status=status if status in {"verified", "auto_verified", "candidate", "conflicting"} else "candidate",
                        confidence=float(artifact.get("confidence", 0.0)),
                        statement=value,
                        claim_extracted_at=timestamp,
                        claim_last_updated_at=timestamp,
                        source_span_ids=source_span_ids,
                        measurement_ids=[measurement.measurement_id],
                    )
                )
            continue

        if kind == "claim":
            claim_id = artifact_id[:16]
            entity_ids = [ensure_entity(item, "Entity") for item in metadata.get("entity_names", []) if isinstance(item, str)]
            bundle.claims.append(
                ClaimDTO(
                    claim_id=claim_id,
                    status=status if status in {"verified", "auto_verified", "candidate", "conflicting"} else "candidate",
                    confidence=float(artifact.get("confidence", 0.0)),
                    statement=value,
                    claim_extracted_at=timestamp,
                    claim_last_updated_at=timestamp,
                    source_span_ids=source_span_ids,
                    entity_ids=entity_ids,
                )
            )
            continue

        if kind in ENTITY_KINDS:
            domain_type = "Material" if kind in {"material", "substance"} else kind.capitalize()
            entity_id = ensure_entity(value, domain_type)
            if str(artifact.get("status", "candidate")) != "confirmed":
                bundle.candidate_entities.append(
                    {
                        "candidate_id": artifact_id[:16],
                        "raw_data": value,
                        "extracted_at": timestamp,
                        "entity_id": entity_id,
                    }
                )
            elif source_span_ids:
                rel_type = SEMANTIC_RELATION_MAP.get(kind, "USES_MATERIAL")
                bundle.claims.append(
                    ClaimDTO(
                        claim_id=uuid.uuid4().hex[:16],
                        status=status if status in {"verified", "auto_verified"} else "auto_verified",
                        confidence=float(artifact.get("confidence", 0.0)),
                        statement=value,
                        claim_extracted_at=timestamp,
                        claim_last_updated_at=timestamp,
                        source_span_ids=source_span_ids,
                        entity_ids=[entity_id],
                        semantic_relations=[{"type": rel_type, "target_id": entity_id}],
                    )
                )
            continue

        if str(artifact.get("status", "candidate")) != "confirmed":
            bundle.candidate_entities.append(
                {
                    "candidate_id": artifact_id[:16],
                    "raw_data": value,
                    "extracted_at": timestamp,
                }
            )

    return bundle
