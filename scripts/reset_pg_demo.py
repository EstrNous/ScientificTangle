#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DEFAULT_TABLES = (
    "export_artifacts",
    "notification_match_results",
    "extracted_entities",
    "review_decisions",
    "document_cascade_refs",
    "source_span_lookup",
    "audit_events",
    "role_permissions",
    "permissions",
    "roles",
    "query_runs",
    "ingestion_tasks",
    "export_jobs",
    "indexed_documents",
    "notifications",
    "user_interests",
    "chat_messages",
    "chat_sessions",
    "admin_settings",
    "service_state",
    "refresh_sessions",
    "users",
)


async def reset_tables(database_url: str, tables: tuple[str, ...]) -> None:
    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        for table in tables:
            await connection.execute(text(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE'))
    await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description="Truncate demo PostgreSQL tables without dropping volumes")
    parser.add_argument(
        "--database-url",
        default=os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://st_user:st_pass@localhost:5432/scientific_tangle",
        ),
    )
    parser.add_argument("--tables", nargs="*", default=list(DEFAULT_TABLES))
    args = parser.parse_args()
    asyncio.run(reset_tables(args.database_url, tuple(args.tables)))
    print("postgresql demo tables truncated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
