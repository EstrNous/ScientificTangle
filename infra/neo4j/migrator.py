from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from neo4j import AsyncDriver, AsyncSession


SCHEMA_VERSION = "neo4j_mvp_v1"
CYTHER_FILES = ("constraints.cypher", "indexes.cypher", "schema_registry.cypher")


def infra_neo4j_dir() -> Path:
    here = Path(__file__).resolve().parent
    docker_path = Path("/app/infra/neo4j")
    if docker_path.exists():
        return docker_path
    return here


def split_cypher_statements(content: str) -> list[str]:
    statements: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        statements.append(stripped.rstrip(";"))
    return [statement for statement in statements if statement]


async def apply_cypher_file(session: AsyncSession, path: Path) -> int:
    if not path.exists() or path.stat().st_size == 0:
        return 0
    content = path.read_text(encoding="utf-8")
    statements = split_cypher_statements(content)
    for statement in statements:
        await session.run(statement)
    return len(statements)


async def record_schema_version(session: AsyncSession, version: str, status: str) -> None:
    await session.run(
        """
        MERGE (sv:SchemaVersion {version: $version})
        SET sv.applied_at = $applied_at,
            sv.status = $status
        """,
        version=version,
        applied_at=datetime.now(UTC).isoformat(),
        status=status,
    )


async def migrate_schema(driver: AsyncDriver, request_id: str | None = None) -> dict[str, int | str]:
    base_dir = infra_neo4j_dir()
    metadata = {"request_id": request_id} if request_id else None
    applied: dict[str, int] = {}
    async with driver.session(metadata=metadata) as session:
        for filename in CYTHER_FILES:
            applied[filename] = await apply_cypher_file(session, base_dir / filename)
        await record_schema_version(session, SCHEMA_VERSION, "applied")
    return {"schema_version": SCHEMA_VERSION, "applied": applied}


async def reset_graph(driver: AsyncDriver, request_id: str | None = None) -> None:
    metadata = {"request_id": request_id} if request_id else None
    async with driver.session(metadata=metadata) as session:
        await session.run("MATCH (n) DETACH DELETE n")
