from __future__ import annotations

import json
import uuid
from pathlib import Path

import yaml
from neo4j import AsyncDriver

from infra.neo4j.migrator import migrate_schema, reset_graph

from .dto import BootstrapResultDTO


def repo_root() -> Path:
    docker_root = Path("/app")
    if (docker_root / "ontology").exists():
        return docker_root
    return Path(__file__).resolve().parents[3]


async def bootstrap_schema(driver: AsyncDriver, request_id: str | None = None) -> dict[str, int | str]:
    return await migrate_schema(driver, request_id=request_id)


async def reset_database(driver: AsyncDriver, request_id: str | None = None) -> None:
    await reset_graph(driver, request_id=request_id)


async def seed_schema_registry(driver: AsyncDriver, request_id: str | None = None) -> BootstrapResultDTO:
    migration = await migrate_schema(driver, request_id=request_id)
    root = repo_root()
    entity_types = 0
    relation_types = 0
    validation_rules = 0
    aliases = 0
    async with driver.session() as session:
        core_path = root / "ontology" / "core_schema.yaml"
        if core_path.exists():
            core = yaml.safe_load(core_path.read_text(encoding="utf-8"))
            for item in core.get("entity_types", []):
                await session.run(
                    """
                    MERGE (et:EntityType {type_name: $type_name})
                    SET et.description = $description,
                        et.is_abstract = false
                    """,
                    type_name=item["name"],
                    description=item.get("description", ""),
                )
                entity_types += 1
            for item in core.get("relation_types", []):
                await session.run(
                    """
                    MERGE (rt:RelationType {type_name: $type_name})
                    SET rt.source_type = $source_type,
                        rt.target_type = $target_type,
                        rt.description = $description
                    """,
                    type_name=item["name"],
                    source_type=item.get("source", ""),
                    target_type=item.get("target", ""),
                    description=item.get("description", ""),
                )
                relation_types += 1
        rules_path = root / "ontology" / "validation_rules.yaml"
        if rules_path.exists():
            rules = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
            for item in rules.get("rules", []):
                await session.run(
                    """
                    MERGE (vr:ValidationRule {rule_id: $rule_id})
                    SET vr.entity_type = $entity_type,
                        vr.expression = $expression,
                        vr.is_active = true
                    """,
                    rule_id=item["id"],
                    entity_type=item.get("entity", ""),
                    expression=item.get("check", ""),
                )
                validation_rules += 1
        aliases_path = root / "dictionaries" / "aliases_mvp.json"
        if aliases_path.exists():
            payload = json.loads(aliases_path.read_text(encoding="utf-8"))
            for entry in payload.get("aliases", []):
                canonical = entry["canonical"]
                entity_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"entity:{canonical}").hex[:16]
                await session.run(
                    """
                    MERGE (e:Entity {entity_id: $entity_id})
                    SET e.canonical_name = $canonical_name,
                        e.domain_type = 'Material',
                        e.created_at = coalesce(e.created_at, datetime())
                    """,
                    entity_id=entity_id,
                    canonical_name=canonical,
                )
                for alias_name in entry.get("aliases", []):
                    alias_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"alias:{canonical}:{alias_name}").hex[:16]
                    await session.run(
                        """
                        MERGE (a:Alias {alias_id: $alias_id})
                        SET a.name = $name,
                            a.type = 'synonym',
                            a.confidence = 1.0
                        WITH a
                        MATCH (e:Entity {entity_id: $entity_id})
                        MERGE (e)-[:HAS_ALIAS]->(a)
                        """,
                        alias_id=alias_id,
                        name=alias_name,
                        entity_id=entity_id,
                    )
                    aliases += 1
    applied = migration.get("applied", {})
    if not isinstance(applied, dict):
        applied = {}
    return BootstrapResultDTO(
        schema_version=str(migration.get("schema_version", "")),
        seeded_entity_types=entity_types,
        seeded_relation_types=relation_types,
        seeded_validation_rules=validation_rules,
        seeded_aliases=aliases,
        applied={key: int(value) for key, value in applied.items()},
    )
