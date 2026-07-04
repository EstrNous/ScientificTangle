from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from .models import DocumentDeletionStatus, IndexedDocument, ReviewDecision, ReviewDecisionStatus
from .review_storage import ReviewStorageRepository

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "e2" / "review_source_delete.json"


def load_e2_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def validate_e2_fixture(payload: dict[str, Any] | None = None) -> list[str]:
    data = payload or load_e2_fixture()
    errors: list[str] = []
    required_keys = {
        "indexed_documents",
        "source_span_lookup",
        "review_decisions",
        "document_cascade_refs",
        "neo4j_candidates",
    }
    missing = required_keys - set(data)
    if missing:
        errors.append(f"missing fixture sections: {sorted(missing)}")
    for span in data.get("source_span_lookup", []):
        if span.get("highlight_start", 0) > span.get("highlight_end", 0):
            errors.append(f"invalid highlight range for {span.get('source_span_id')}")
    for decision in data.get("review_decisions", []):
        if not decision.get("candidate_id") or not decision.get("candidate_type"):
            errors.append("review decision requires candidate_id and candidate_type")
    for refs in data.get("document_cascade_refs", []):
        if not refs.get("document_id"):
            errors.append("document_cascade_refs requires document_id")
    return errors


async def seed_e2_fixtures(session: AsyncSession) -> dict[str, int]:
    payload = load_e2_fixture()
    validation_errors = validate_e2_fixture(payload)
    if validation_errors:
        raise ValueError("; ".join(validation_errors))

    storage = ReviewStorageRepository(session)
    counts = {
        "indexed_documents": 0,
        "source_span_lookup": 0,
        "review_decisions": 0,
        "document_cascade_refs": 0,
    }

    for document in payload["indexed_documents"]:
        existing = await session.get(IndexedDocument, document["document_id"])
        if existing is None:
            session.add(
                IndexedDocument(
                    document_id=document["document_id"],
                    title=document["title"],
                    source_type=document["source_type"],
                    source_spans_count=document.get("source_spans_count", 0),
                    indexed_points_count=document.get("indexed_points_count", 0),
                    access_level=document["access_level"],
                    metadata_=document.get("metadata", {}),
                    deletion_status=document.get("deletion_status", DocumentDeletionStatus.NONE.value),
                )
            )
            counts["indexed_documents"] += 1

    document_access: dict[str, tuple[str, list[str]]] = {}
    for document in payload["indexed_documents"]:
        metadata = document.get("metadata", {})
        document_access[document["document_id"]] = (
            document["access_level"],
            list(metadata.get("allowed_roles", [])),
        )

    for span in payload["source_span_lookup"]:
        span_access_level = span.get("access_level")
        span_allowed_roles = span.get("allowed_roles")
        if span_access_level is None:
            span_access_level, default_roles = document_access.get(
                span["document_id"],
                ("internal", []),
            )
            if span_allowed_roles is None:
                span_allowed_roles = default_roles
        if span_allowed_roles is None:
            span_allowed_roles = []
        await storage.upsert_source_span_lookup(
            source_span_id=span["source_span_id"],
            document_id=span["document_id"],
            page=span["page"],
            highlight_start=span["highlight_start"],
            highlight_end=span["highlight_end"],
            source_type=span["source_type"],
            text_snippet=span["text_snippet"],
            table_block_id=span.get("table_block_id"),
            table_row_id=span.get("table_row_id"),
            access_level=span_access_level,
            allowed_roles=span_allowed_roles,
        )
        counts["source_span_lookup"] += 1

    for decision in payload["review_decisions"]:
        existing = await storage.get_decision(decision["candidate_id"], decision["candidate_type"])
        if existing is None:
            session.add(
                ReviewDecision(
                    id=uuid4(),
                    candidate_id=decision["candidate_id"],
                    candidate_type=decision["candidate_type"],
                    status=decision.get("status", ReviewDecisionStatus.PENDING.value),
                    document_id=decision.get("document_id"),
                    source_span_id=decision.get("source_span_id"),
                    claim_id=decision.get("claim_id"),
                )
            )
            counts["review_decisions"] += 1
    await session.commit()

    for refs in payload["document_cascade_refs"]:
        await storage.upsert_document_cascade_refs(
            refs["document_id"],
            source_span_ids=refs.get("source_span_ids", []),
            claim_ids=refs.get("claim_ids", []),
            vector_point_ids=refs.get("vector_point_ids", []),
            graph_node_refs=refs.get("graph_node_refs", []),
            minio_object_refs=refs.get("minio_object_refs", []),
        )
        counts["document_cascade_refs"] += 1

    return counts
