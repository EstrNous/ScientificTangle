from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from infra.postgres.orchestrator_db.access_audit import validate_access_audit_details
from infra.postgres.orchestrator_db.e3_fixtures import resolve_user_id, seed_e3_fixtures
from infra.postgres.orchestrator_db.models import DocumentDeletionStatus, IndexedDocument
from infra.postgres.orchestrator_db.review_storage import ReviewStorageRepository
from infra.postgres.orchestrator_db.workflow_storage import WorkflowStorageRepository

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "e4" / "evidence_access.json"

QDRANT_FILTER_FIELDS = frozenset(
    {
        "access_level",
        "allowed_roles",
        "source_type",
        "page",
        "highlight_start",
        "highlight_end",
        "table_row_id",
        "numeric_min",
        "numeric_max",
        "units",
        "geo_bucket",
        "geo_country",
        "published_year",
        "dictionary_version_id",
        "claim_ids",
        "graph_entity_ids",
        "document_id",
        "source_span_id",
    }
)


def load_e4_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def validate_e4_fixture(payload: dict[str, Any] | None = None) -> list[str]:
    data = payload or load_e4_fixture()
    errors: list[str] = []
    required_keys = {
        "users",
        "indexed_documents",
        "source_span_lookup",
        "document_cascade_refs",
        "qdrant_payloads",
        "audit_events",
        "access_expectations",
    }
    missing = required_keys - set(data)
    if missing:
        errors.append(f"missing fixture sections: {sorted(missing)}")

    levels = {document["access_level"] for document in data.get("indexed_documents", [])}
    if not {"public", "internal", "restricted"} <= levels:
        errors.append("fixture must include public, internal and restricted documents")

    partner_users = [
        user for user in data.get("users", []) if user.get("role") == "external_partner"
    ]
    if not partner_users:
        errors.append("fixture must include external_partner user reference")

    for payload_item in data.get("qdrant_payloads", []):
        errors.extend(validate_qdrant_payload_fixture(payload_item))

    for event in data.get("audit_events", []):
        errors.extend(validate_access_audit_details(event.get("action", ""), event.get("details", {})))

    expectations = data.get("access_expectations", {})
    partner = expectations.get("external_partner", {})
    if not partner.get("forbidden_source_span_ids"):
        errors.append("external_partner expectations must define forbidden_source_span_ids")

    return errors


def validate_qdrant_payload_fixture(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = QDRANT_FILTER_FIELDS - set(payload)
    if missing:
        errors.append(
            f"qdrant payload {payload.get('point_id', '?')} missing fields: {sorted(missing)}"
        )
    if payload.get("source_type") == "table" and not payload.get("table_row_id"):
        errors.append(
            f"table payload {payload.get('point_id', '?')} requires table_row_id"
        )
    return errors


async def seed_e4_fixtures(session: AsyncSession) -> dict[str, int]:
    validation_errors = validate_e4_fixture()
    if validation_errors:
        raise ValueError("; ".join(validation_errors))

    counts = await seed_e3_fixtures(session)
    payload = load_e4_fixture()
    storage = ReviewStorageRepository(session)
    workflow = WorkflowStorageRepository(session)

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
            counts["indexed_documents"] = counts.get("indexed_documents", 0) + 1

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
        counts["source_span_lookup"] = counts.get("source_span_lookup", 0) + 1

    for refs in payload["document_cascade_refs"]:
        await storage.upsert_document_cascade_refs(
            refs["document_id"],
            source_span_ids=refs.get("source_span_ids", []),
            claim_ids=refs.get("claim_ids", []),
            vector_point_ids=refs.get("vector_point_ids", []),
            graph_node_refs=refs.get("graph_node_refs", []),
            minio_object_refs=refs.get("minio_object_refs", []),
        )
        counts["document_cascade_refs"] = counts.get("document_cascade_refs", 0) + 1

    for event in payload["audit_events"]:
        user_id = await resolve_user_id(session, event["user_ref"])
        await workflow.record_audit_event(
            user_id=user_id,
            action=event["action"],
            resource_type=event["resource_type"],
            resource_id=event["resource_id"],
            details=event["details"],
            request_id=event["request_id"],
        )
        counts["audit_events"] = counts.get("audit_events", 0) + 1

    counts["qdrant_payloads"] = len(payload["qdrant_payloads"])
    return counts


async def resolve_fixture_user_id(session: AsyncSession, user_ref: str) -> UUID:
    return await resolve_user_id(session, user_ref)
