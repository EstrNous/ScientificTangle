from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from infra.postgres.notification_db.workflow_repository import (
    NotificationMatchInput,
    NotificationWorkflowRepository,
)
from infra.postgres.orchestrator_db.e4_fixtures import seed_e4_fixtures
from infra.postgres.orchestrator_db.models import QueryRun, QueryRunStatus
from infra.postgres.orchestrator_db.product_events_storage import (
    PRODUCT_AUDIT_ACTIONS,
    ExportArtifactInput,
    ProductEventsStorageRepository,
)
from infra.postgres.orchestrator_db.workflow_storage import WorkflowStorageRepository

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "e5" / "product_events.json"


def load_e5_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def validate_e5_fixture(payload: dict[str, Any] | None = None) -> list[str]:
    data = payload or load_e5_fixture()
    errors: list[str] = []
    required_keys = {
        "export_jobs",
        "audit_events",
        "notification_events",
        "audit_csv_export",
    }
    missing = required_keys - set(data)
    if missing:
        errors.append(f"missing fixture sections: {sorted(missing)}")

    for event in data.get("audit_events", []):
        action = event.get("action", "")
        if action not in PRODUCT_AUDIT_ACTIONS:
            errors.append(f"unsupported product audit action: {action}")

    for job in data.get("export_jobs", []):
        if not job.get("artifacts"):
            errors.append("export_jobs require at least one artifact with MinIO metadata")
        for artifact in job.get("artifacts", []):
            if not artifact.get("storage_key"):
                errors.append("export artifact requires storage_key")

    csv_export = data.get("audit_csv_export", {})
    if not csv_export.get("storage_key"):
        errors.append("audit_csv_export requires storage_key")
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


async def _ensure_query_run(
    session: AsyncSession,
    *,
    user_id: UUID,
    query_run_ref: str,
) -> UUID:
    existing = await session.scalar(
        select(QueryRun.id).where(QueryRun.request_id == query_run_ref).limit(1)
    )
    if existing is not None:
        return existing
    run = QueryRun(
        id=uuid4(),
        user_id=user_id,
        raw_question="E5 offline export fixture question",
        request_id=query_run_ref,
        status=QueryRunStatus.COMPLETED.value,
        warnings=[],
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run.id


async def seed_e5_fixtures(session: AsyncSession) -> dict[str, int]:
    validation_errors = validate_e5_fixture()
    if validation_errors:
        raise ValueError("; ".join(validation_errors))

    counts = await seed_e4_fixtures(session)
    payload = load_e5_fixture()
    product = ProductEventsStorageRepository(session)
    workflow = WorkflowStorageRepository(session)
    notifications = NotificationWorkflowRepository(session)

    export_jobs = 0
    export_artifacts = 0
    audit_events = 0
    notification_events = 0

    for job_spec in payload["export_jobs"]:
        user_id = await resolve_user_id(session, job_spec["user_ref"])
        query_run_id = await _ensure_query_run(
            session,
            user_id=user_id,
            query_run_ref=job_spec["query_run_ref"],
        )
        job = await product.create_export_job(
            user_id=user_id,
            query_run_id=query_run_id,
            export_format=job_spec["format"],
        )
        export_jobs += 1
        artifacts = [
            ExportArtifactInput(
                artifact_kind=item["artifact_kind"],
                storage_key=item["storage_key"],
                content_type=item["content_type"],
                byte_size=item.get("byte_size"),
                checksum=item.get("checksum"),
            )
            for item in job_spec["artifacts"]
        ]
        rows = await product.attach_export_artifacts(job.id, artifacts)
        export_artifacts += len(rows)

    for event_spec in payload["audit_events"]:
        user_id = await resolve_user_id(session, event_spec["user_ref"])
        await workflow.record_audit_event(
            user_id=user_id,
            action=event_spec["action"],
            resource_type=event_spec["resource_type"],
            resource_id=event_spec["resource_id"],
            details=event_spec["details"],
            request_id=event_spec["request_id"],
        )
        audit_events += 1

    for note_spec in payload["notification_events"]:
        user_id = await resolve_user_id(session, note_spec["user_ref"])
        await notifications.create_notification_with_match(
            user_id,
            type=note_spec["type"],
            message=note_spec["message"],
            reference_id=note_spec.get("reference_id"),
            reference_type=note_spec.get("reference_type"),
            match=NotificationMatchInput(
                reference_id=note_spec.get("reference_id"),
                reference_type=note_spec.get("reference_type"),
                match_score=note_spec.get("match_score"),
                match_payload=note_spec.get("match_payload", {}),
            ),
        )
        notification_events += 1

    csv_spec = payload["audit_csv_export"]
    csv_user_id = await resolve_user_id(session, csv_spec["user_ref"])
    csv_row = await product.create_audit_csv_export(
        user_id=csv_user_id,
        filter_params=csv_spec["filter_params"],
    )
    await product.complete_audit_csv_export(
        csv_row.id,
        storage_key=csv_spec["storage_key"],
        row_count=csv_spec["row_count"],
    )

    counts.update(
        {
            "export_jobs": export_jobs,
            "export_artifacts": export_artifacts,
            "audit_events": counts.get("audit_events", 0) + audit_events,
            "notification_events": notification_events,
            "audit_csv_exports": 1,
        }
    )
    return counts
