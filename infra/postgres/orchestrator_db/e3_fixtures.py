from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from infra.postgres.notification_db.workflow_repository import (
    ExtractedEntityInput,
    NotificationMatchInput,
    NotificationWorkflowRepository,
)
from infra.postgres.orchestrator_db.e2_fixtures import seed_e2_fixtures
from infra.postgres.orchestrator_db.models import (
    CascadeStatus,
    DocumentCascadeRefs,
    DocumentDeletionStatus,
    IndexedDocument,
    ReviewDecisionStatus,
)
from infra.postgres.orchestrator_db.workflow_storage import WorkflowStorageRepository

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "e3" / "workflow_state.json"


def load_e3_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def validate_e3_fixture(payload: dict[str, Any] | None = None) -> list[str]:
    data = payload or load_e3_fixture()
    errors: list[str] = []
    required_keys = {
        "user_interests",
        "notification_matches",
        "review_actions",
        "admin_settings",
        "document_deletion",
    }
    missing = required_keys - set(data)
    if missing:
        errors.append(f"missing fixture sections: {sorted(missing)}")
    deletion = data.get("document_deletion", {})
    if not deletion.get("document_id"):
        errors.append("document_deletion requires document_id")
    return errors


async def resolve_user_id(session: AsyncSession, username: str) -> UUID:
    result = await session.execute(
        text("SELECT id FROM users WHERE username = :username LIMIT 1"),
        {"username": username},
    )
    row = result.first()
    if row is None:
        raise RuntimeError(f"user '{username}' not found; run auth-seed-users first")
    return row[0]


async def seed_e3_fixtures(session: AsyncSession) -> dict[str, int]:
    validation_errors = validate_e3_fixture()
    if validation_errors:
        raise ValueError("; ".join(validation_errors))

    counts = await seed_e2_fixtures(session)
    payload = load_e3_fixture()
    workflow = WorkflowStorageRepository(session)
    notifications = NotificationWorkflowRepository(session)

    for interest in payload["user_interests"]:
        user_id = await resolve_user_id(session, interest["user_ref"])
        entity_rows = [
            ExtractedEntityInput(
                entity_label=item["entity_label"],
                entity_type=item["entity_type"],
                confidence=item.get("confidence"),
                document_id=item.get("document_id"),
                source_span_id=item.get("source_span_id"),
                metadata=item.get("metadata"),
            )
            for item in interest.get("extracted_entities", [])
        ]
        await notifications.upsert_interests_with_entities(
            user_id,
            interest["raw_text"],
            interest.get("extracted_entities_snapshot", {}),
            entity_rows,
        )
        counts["user_interests"] = counts.get("user_interests", 0) + 1
        counts["extracted_entities"] = counts.get("extracted_entities", 0) + len(entity_rows)

    for match in payload["notification_matches"]:
        user_id = await resolve_user_id(session, match["user_ref"])
        await notifications.create_notification_with_match(
            user_id,
            type=match["type"],
            message=match["message"],
            reference_id=match.get("reference_id"),
            reference_type=match.get("reference_type"),
            match=NotificationMatchInput(
                reference_id=match.get("reference_id"),
                reference_type=match.get("reference_type"),
                match_score=match.get("match_score"),
                match_payload=match.get("match_payload", {}),
            ),
        )
        counts["notification_matches"] = counts.get("notification_matches", 0) + 1

    for action in payload["review_actions"]:
        await workflow.apply_review_decision_with_audit(
            candidate_id=action["candidate_id"],
            candidate_type=action["candidate_type"],
            status=ReviewDecisionStatus(action["status"]),
            reviewer_user_id=await resolve_user_id(session, "researcher"),
            request_id="e3-fixture-review",
            document_id=action.get("document_id"),
            source_span_id=action.get("source_span_id"),
            claim_id=action.get("claim_id"),
            comment=action.get("comment"),
        )
        counts["review_actions"] = counts.get("review_actions", 0) + 1

    for setting in payload["admin_settings"]:
        await workflow.save_admin_setting_with_audit(
            setting_key=setting["setting_key"],
            setting_value=setting["setting_value"],
            user_id=await resolve_user_id(session, "researcher"),
            request_id="e3-fixture-admin",
            description=setting.get("description"),
        )
        counts["admin_settings"] = counts.get("admin_settings", 0) + 1

    deletion = payload["document_deletion"]
    document_id = deletion["document_id"]
    existing = await session.get(IndexedDocument, document_id)
    if existing is None:
        session.add(
            IndexedDocument(
                document_id=document_id,
                title=deletion["title"],
                source_type=deletion["source_type"],
                access_level=deletion["access_level"],
                deletion_status=DocumentDeletionStatus.NONE.value,
            )
        )
        counts["indexed_documents"] = counts.get("indexed_documents", 0) + 1
    cascade = deletion.get("cascade_refs", {})
    refs = await session.get(DocumentCascadeRefs, document_id)
    if refs is None:
        session.add(
            DocumentCascadeRefs(
                document_id=document_id,
                source_span_ids=cascade.get("source_span_ids", []),
                claim_ids=cascade.get("claim_ids", []),
                vector_point_ids=cascade.get("vector_point_ids", []),
                graph_node_refs=cascade.get("graph_node_refs", []),
                minio_object_refs=cascade.get("minio_object_refs", []),
                cascade_status=CascadeStatus.NONE.value,
            )
        )
        counts["document_cascade_refs"] = counts.get("document_cascade_refs", 0) + 1
    await session.commit()
    return counts
