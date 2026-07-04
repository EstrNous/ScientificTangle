#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from infra.postgres.orchestrator_db.e2_fixtures import load_e2_fixture
from infra.postgres.orchestrator_db.e3_fixtures import load_e3_fixture
from infra.postgres.orchestrator_db.e4_fixtures import load_e4_fixture
from infra.postgres.orchestrator_db.e5_fixtures import load_e5_fixture

COLLECTION_NAME = "st_evidence_v1"
MINIO_BUCKETS = (
    "source-files",
    "normalized-artifacts",
    "exports",
    "demo-archives",
    "temp-files",
)

PG_COUNT_QUERIES: dict[str, str] = {
    "users": "SELECT COUNT(*) FROM users",
    "indexed_documents": "SELECT COUNT(*) FROM indexed_documents",
    "source_span_lookup": "SELECT COUNT(*) FROM source_span_lookup",
    "review_decisions": "SELECT COUNT(*) FROM review_decisions",
    "document_cascade_refs": "SELECT COUNT(*) FROM document_cascade_refs",
    "export_jobs": "SELECT COUNT(*) FROM export_jobs",
    "export_artifacts": "SELECT COUNT(*) FROM export_artifacts",
    "audit_events": "SELECT COUNT(*) FROM audit_events",
    "audit_csv_exports": "SELECT COUNT(*) FROM audit_csv_exports",
    "notifications": "SELECT COUNT(*) FROM notifications",
    "notification_match_results": "SELECT COUNT(*) FROM notification_match_results",
    "user_interests": "SELECT COUNT(*) FROM user_interests",
    "extracted_entities": "SELECT COUNT(*) FROM extracted_entities",
    "admin_settings": "SELECT COUNT(*) FROM admin_settings",
    "roles": "SELECT COUNT(*) FROM roles",
}


@dataclass(slots=True)
class StoreStatus:
    status: str
    counts: dict[str, int | str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SeedInventoryReport:
    schema_version: str = "seed_inventory.v1"
    postgresql: StoreStatus = field(default_factory=lambda: StoreStatus(status="unknown"))
    neo4j: StoreStatus = field(default_factory=lambda: StoreStatus(status="unknown"))
    qdrant: StoreStatus = field(default_factory=lambda: StoreStatus(status="unknown"))
    minio: StoreStatus = field(default_factory=lambda: StoreStatus(status="unknown"))
    fixture_expectations: dict[str, int] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_fixture_expectations() -> dict[str, int]:
    e2 = load_e2_fixture()
    e3 = load_e3_fixture()
    e4 = load_e4_fixture()
    e5 = load_e5_fixture()

    document_ids = {
        *(item["document_id"] for item in e2.get("indexed_documents", [])),
        e3.get("document_deletion", {}).get("document_id"),
        *(item["document_id"] for item in e4.get("indexed_documents", [])),
    }
    document_ids.discard(None)

    source_span_ids = {
        *(item["source_span_id"] for item in e2.get("source_span_lookup", [])),
        *(item["source_span_id"] for item in e4.get("source_span_lookup", [])),
    }

    table_rows = sum(
        1
        for item in (*e2.get("source_span_lookup", []), *e4.get("source_span_lookup", []))
        if item.get("table_row_id")
    )

    return {
        "users_min": 2,
        "indexed_documents_min": len(document_ids),
        "source_span_lookup_min": len(source_span_ids),
        "table_rows_min": table_rows,
        "review_decisions_min": len(e2.get("review_decisions", [])),
        "document_cascade_refs_min": len(e2.get("document_cascade_refs", [])) + int(
            bool(e3.get("document_deletion", {}).get("cascade_refs"))
        ),
        "export_jobs_min": len(e5.get("export_jobs", [])),
        "export_artifacts_min": sum(len(job.get("artifacts", [])) for job in e5.get("export_jobs", [])),
        "audit_events_min": len(e4.get("audit_events", [])) + len(e5.get("audit_events", [])),
        "notification_events_min": len(e5.get("notification_events", [])),
        "audit_csv_exports_min": 1 if e5.get("audit_csv_export") else 0,
        "user_interests_min": len(e3.get("user_interests", [])),
        "qdrant_payloads_min": len(e4.get("qdrant_payloads", [])),
        "dictionary_versions_min": 0,
        "graph_nodes_min": 0,
        "claims_min": 0,
        "vectors_min": 0,
    }


async def count_postgresql(database_url: str) -> StoreStatus:
    status = StoreStatus(status="ok")
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            for key, query in PG_COUNT_QUERIES.items():
                try:
                    value = await session.scalar(text(query))
                    status.counts[key] = int(value or 0)
                except Exception as error:
                    status.warnings.append(f"{key}: {error}")
                    status.counts[key] = 0
    except Exception as error:
        status.status = "error"
        status.errors.append(str(error))
    finally:
        await engine.dispose()
    return status


async def count_neo4j(uri: str, user: str, password: str) -> StoreStatus:
    status = StoreStatus(status="ok")
    try:
        from neo4j import AsyncGraphDatabase
    except ImportError:
        status.status = "skipped"
        status.warnings.append("neo4j package not installed")
        return status

    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    try:
        async with driver.session() as session:
            total = await session.run("MATCH (n) RETURN count(n) AS c")
            record = await total.single()
            status.counts["graph_nodes"] = int(record["c"]) if record else 0

            for label in ("Document", "SourceSpan", "Claim", "DictionaryVersion", "Entity"):
                result = await session.run(f"MATCH (n:{label}) RETURN count(n) AS c")
                row = await result.single()
                status.counts[f"graph_{label.lower()}"] = int(row["c"]) if row else 0

            status.counts["claims"] = int(status.counts.get("graph_claim", 0))
            status.counts["dictionary_versions"] = int(status.counts.get("graph_dictionaryversion", 0))
    except Exception as error:
        status.status = "error"
        status.errors.append(str(error))
    finally:
        await driver.close()
    return status


async def count_qdrant(base_url: str, collection: str = COLLECTION_NAME) -> StoreStatus:
    status = StoreStatus(status="ok")
    url = base_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{url}/collections/{collection}")
            if response.status_code == 404:
                status.status = "empty"
                status.counts["vectors"] = 0
                status.counts["collection"] = collection
                return status
            response.raise_for_status()
            payload = response.json()
            result = payload.get("result", {})
            status.counts["vectors"] = int(result.get("points_count", 0))
            status.counts["indexed_vectors"] = int(result.get("indexed_vectors_count", 0))
            status.counts["collection"] = collection
    except Exception as error:
        status.status = "error"
        status.errors.append(str(error))
    return status


async def count_minio(endpoint: str, access_key: str, secret_key: str) -> StoreStatus:
    status = StoreStatus(status="ok")
    try:
        from minio import Minio
    except ImportError:
        status.status = "skipped"
        status.warnings.append("minio package not installed")
        return status

    secure = endpoint.startswith("https://")
    host = endpoint.replace("https://", "").replace("http://", "")
    client = Minio(host, access_key=access_key, secret_key=secret_key, secure=secure)
    total_objects = 0
    try:
        for bucket in MINIO_BUCKETS:
            bucket_count = 0
            if client.bucket_exists(bucket):
                for _ in client.list_objects(bucket, recursive=True):
                    bucket_count += 1
            status.counts[bucket] = bucket_count
            total_objects += bucket_count
        status.counts["objects_total"] = total_objects
    except Exception as error:
        status.status = "error"
        status.errors.append(str(error))
    return status


def validate_offline_counts(
    postgresql: StoreStatus,
    expectations: dict[str, int],
) -> dict[str, Any]:
    actual = postgresql.counts
    checks: list[dict[str, Any]] = []
    failures: list[str] = []

    mapping = {
        "users": "users_min",
        "indexed_documents": "indexed_documents_min",
        "source_span_lookup": "source_span_lookup_min",
        "review_decisions": "review_decisions_min",
        "document_cascade_refs": "document_cascade_refs_min",
        "export_jobs": "export_jobs_min",
        "export_artifacts": "export_artifacts_min",
        "audit_events": "audit_events_min",
        "notifications": "notification_events_min",
        "audit_csv_exports": "audit_csv_exports_min",
        "user_interests": "user_interests_min",
    }

    for actual_key, expected_key in mapping.items():
        minimum = expectations.get(expected_key, 0)
        value = int(actual.get(actual_key, 0))
        passed = value >= minimum
        checks.append(
            {
                "metric": actual_key,
                "actual": value,
                "minimum": minimum,
                "status": "pass" if passed else "fail",
            }
        )
        if not passed:
            failures.append(f"{actual_key}: {value} < {minimum}")

    return {
        "status": "pass" if not failures else "fail",
        "checks": checks,
        "failures": failures,
    }


async def build_inventory_report(
    *,
    database_url: str,
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
    qdrant_url: str,
    minio_endpoint: str,
    minio_access_key: str,
    minio_secret_key: str,
    include_remote: bool,
) -> SeedInventoryReport:
    expectations = compute_fixture_expectations()
    report = SeedInventoryReport(fixture_expectations=expectations)
    report.postgresql = await count_postgresql(database_url)
    if include_remote:
        report.neo4j = await count_neo4j(neo4j_uri, neo4j_user, neo4j_password)
        report.qdrant = await count_qdrant(qdrant_url)
        report.minio = await count_minio(minio_endpoint, minio_access_key, minio_secret_key)
    else:
        report.neo4j = StoreStatus(status="skipped", warnings=["include_remote=false"])
        report.qdrant = StoreStatus(status="skipped", warnings=["include_remote=false"])
        report.minio = StoreStatus(status="skipped", warnings=["include_remote=false"])
    report.validation = validate_offline_counts(report.postgresql, expectations)
    return report


async def seed_orchestrator_rbac(session: AsyncSession) -> dict[str, int]:
    from infra.postgres.orchestrator_db.models import Permission, Role, RolePermission

    roles = [
        Role(name="admin", description="Полный доступ"),
        Role(name="researcher", description="Исследователь"),
        Role(name="partner", description="Внешний партнёр"),
    ]
    permissions = [
        Permission(name="query.run", description="Запуск запросов"),
        Permission(name="ingestion.upload", description="Загрузка документов"),
        Permission(name="export.create", description="Экспорт отчётов"),
        Permission(name="admin.read", description="Просмотр админки"),
    ]
    role_permissions = [
        RolePermission(role_name="admin", permission_name="query.run"),
        RolePermission(role_name="admin", permission_name="ingestion.upload"),
        RolePermission(role_name="admin", permission_name="export.create"),
        RolePermission(role_name="admin", permission_name="admin.read"),
        RolePermission(role_name="researcher", permission_name="query.run"),
        RolePermission(role_name="researcher", permission_name="ingestion.upload"),
        RolePermission(role_name="researcher", permission_name="export.create"),
        RolePermission(role_name="partner", permission_name="query.run"),
    ]
    session.add_all(roles + permissions + role_permissions)
    await session.commit()
    return {
        "roles": len(roles),
        "permissions": len(permissions),
        "role_permissions": len(role_permissions),
    }


async def seed_gate_auth_users(database_url: str) -> dict[str, int]:
    from pwdlib import PasswordHash
    from sqlalchemy.dialects.postgresql import insert

    from infra.postgres.auth_audit_db.models import Role, User

    password_hash = PasswordHash.recommended()
    seed_users = (
        ("admin", "admin", Role.ADMIN, "admin@example.com"),
        ("researcher", "researcher", Role.RESEARCHER, "researcher@example.com"),
        ("analyst", "analyst", Role.ANALYST, "analyst@example.com"),
        ("manager", "manager", Role.MANAGER, "manager@example.com"),
        ("external_partner", "partner123", Role.EXTERNAL_PARTNER, "partner@example.com"),
    )
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    created = 0
    try:
        async with session_factory() as session:
            for username, password, role, email in seed_users:
                statement = insert(User).values(
                    username=username,
                    email=email,
                    password_hash=password_hash.hash(password),
                    role=role.value,
                    is_active=True,
                )
                statement = statement.on_conflict_do_update(
                    index_elements=[User.username],
                    set_={
                        "email": statement.excluded.email,
                        "password_hash": statement.excluded.password_hash,
                        "role": statement.excluded.role,
                        "is_active": True,
                        "deactivated_at": None,
                    },
                )
                await session.execute(statement)
                created += 1
            await session.commit()
    finally:
        await engine.dispose()
    return {"users": created}


async def run_offline_reseed(database_url: str) -> dict[str, Any]:
    from infra.postgres.orchestrator_db.e5_fixtures import seed_e5_fixtures
    from scripts.reset_pg_demo import DEFAULT_TABLES, reset_tables

    steps: list[dict[str, Any]] = []

    await reset_tables(database_url, DEFAULT_TABLES)
    steps.append({"step": "postgresql_truncate", "status": "ok", "tables": len(DEFAULT_TABLES)})

    auth_counts = await seed_gate_auth_users(database_url)
    steps.append({"step": "auth_users", "status": "ok", **auth_counts})

    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            rbac_counts = await seed_orchestrator_rbac(session)
            steps.append({"step": "orchestrator_rbac", "status": "ok", **rbac_counts})
            fixture_counts = await seed_e5_fixtures(session)
            steps.append({"step": "offline_fixtures_e5", "status": "ok", **fixture_counts})
    finally:
        await engine.dispose()

    report = await build_inventory_report(
        database_url=database_url,
        neo4j_uri="",
        neo4j_user="",
        neo4j_password="",
        qdrant_url="",
        minio_endpoint="",
        minio_access_key="",
        minio_secret_key="",
        include_remote=False,
    )
    return {
        "mode": "offline",
        "steps": steps,
        "inventory": report.to_dict(),
    }


async def reset_remote_stores(
    *,
    knowledge_url: str,
    retrieval_url: str,
    minio_container: str | None,
) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(f"{knowledge_url.rstrip('/')}/v1/graph/reset")
            response.raise_for_status()
            steps.append({"step": "neo4j_reset", "status": "ok", "detail": response.json()})
        except Exception as error:
            steps.append({"step": "neo4j_reset", "status": "error", "detail": str(error)})

        try:
            response = await client.post(f"{retrieval_url.rstrip('/')}/v1/index/reset")
            response.raise_for_status()
            steps.append({"step": "qdrant_reset", "status": "ok", "detail": response.json()})
        except Exception as error:
            steps.append({"step": "qdrant_reset", "status": "error", "detail": str(error)})

    if minio_container:
        import subprocess

        for bucket in MINIO_BUCKETS:
            command = [
                "docker",
                "exec",
                minio_container,
                "sh",
                "-c",
                f"mc alias set local http://localhost:9000 minioadmin minioadmin123 >/dev/null 2>&1; "
                f"mc rm --recursive --force local/{bucket} >/dev/null 2>&1 || true",
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            steps.append(
                {
                    "step": f"minio_purge_{bucket}",
                    "status": "ok" if result.returncode == 0 else "warn",
                    "detail": (result.stderr or result.stdout or "").strip(),
                }
            )
    else:
        steps.append(
            {
                "step": "minio_purge",
                "status": "skipped",
                "detail": "MINIO_CONTAINER not set",
            }
        )
    return steps


async def run_full_reseed(
    *,
    database_url: str,
    knowledge_url: str,
    retrieval_url: str,
    api_url: str,
    minio_container: str | None,
    skip_demo_ingest: bool,
) -> dict[str, Any]:
    payload = await run_offline_reseed(database_url)
    payload["mode"] = "full"
    payload["steps"].extend(
        await reset_remote_stores(
            knowledge_url=knowledge_url,
            retrieval_url=retrieval_url,
            minio_container=minio_container,
        )
    )

    if not skip_demo_ingest:
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "seed_demo.py"), "--api-url", api_url],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        payload["steps"].append(
            {
                "step": "demo_corpus_ingest",
                "status": "ok" if result.returncode == 0 else "error",
                "detail": (result.stdout or result.stderr or "").strip()[-2000:],
            }
        )

    report = await build_inventory_report(
        database_url=database_url,
        neo4j_uri=os.getenv("NEO4J_URL", "bolt://localhost:7687"),
        neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", "neo4j_pass"),
        qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        minio_endpoint=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
        minio_access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        minio_secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin123"),
        include_remote=True,
    )
    payload["inventory"] = report.to_dict()
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed inventory and reset/reseed gate")
    parser.add_argument(
        "--mode",
        choices=("report", "offline", "full"),
        default="report",
        help="report: counts only; offline: PG truncate+fixtures; full: offline+remote reset+ingest",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://st_user:st_pass@localhost:5432/scientific_tangle",
        ),
    )
    parser.add_argument("--knowledge-url", default=os.getenv("KNOWLEDGE_URL", "http://localhost:8004"))
    parser.add_argument("--retrieval-url", default=os.getenv("RETRIEVAL_URL", "http://localhost:8005"))
    parser.add_argument("--api-url", default=os.getenv("SEED_API_URL", "http://localhost/api"))
    parser.add_argument("--minio-container", default=os.getenv("MINIO_CONTAINER", "st-minio"))
    parser.add_argument("--output", default="")
    parser.add_argument("--skip-demo-ingest", action="store_true")
    parser.add_argument("--include-remote", action="store_true")
    return parser.parse_args()


async def main_async(args: argparse.Namespace) -> int:
    if args.mode == "offline":
        payload = await run_offline_reseed(args.database_url)
    elif args.mode == "full":
        payload = await run_full_reseed(
            database_url=args.database_url,
            knowledge_url=args.knowledge_url,
            retrieval_url=args.retrieval_url,
            api_url=args.api_url,
            minio_container=args.minio_container,
            skip_demo_ingest=args.skip_demo_ingest,
        )
    else:
        report = await build_inventory_report(
            database_url=args.database_url,
            neo4j_uri=os.getenv("NEO4J_URL", "bolt://localhost:7687"),
            neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
            neo4j_password=os.getenv("NEO4J_PASSWORD", "neo4j_pass"),
            qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            minio_endpoint=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
            minio_access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            minio_secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin123"),
            include_remote=args.include_remote,
        )
        payload = report.to_dict()

    text_output = json.dumps(payload, ensure_ascii=False, indent=2)
    print(text_output)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text_output, encoding="utf-8")

    validation = payload.get("inventory", payload).get("validation", {})
    if args.mode in {"offline", "full"} and validation.get("status") == "fail":
        return 1
    if args.mode == "full":
        failed = [step for step in payload.get("steps", []) if step.get("status") == "error"]
        if failed:
            return 1
    return 0


def main() -> int:
    args = parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
