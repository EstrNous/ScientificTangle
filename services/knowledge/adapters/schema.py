from __future__ import annotations

import json
import uuid
from pathlib import Path

import yaml
from neo4j import AsyncDriver

from infra.neo4j.migrator import migrate_schema, reset_graph

from .dto import BootstrapResultDTO
from .mapper import entity_id_for_name


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
    domain_entities = 0
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
        domain_path = root / "ontology" / "domain_pack_mining_metallurgy.yaml"
        if domain_path.exists():
            domain_pack = yaml.safe_load(domain_path.read_text(encoding="utf-8"))
            pack = domain_pack.get("domain_pack", {})
            for section, domain_type in (
                ("material_classes", "Material"),
                ("equipment_types", "Equipment"),
                ("process_types", "Process"),
            ):
                for group in domain_pack.get(section, []):
                    if not isinstance(group, dict):
                        continue
                    for key, payload in group.items():
                        examples = payload.get("examples", []) if isinstance(payload, dict) else []
                        names = [key, *examples] if isinstance(examples, list) else [key]
                        for name in names:
                            entity_id = entity_id_for_name(str(name), domain_type)
                            await session.run(
                                """
                                MERGE (e:Entity {entity_id: $entity_id})
                                SET e.canonical_name = $canonical_name,
                                    e.domain_type = $domain_type,
                                    e.created_at = coalesce(e.created_at, datetime())
                                """,
                                entity_id=entity_id,
                                canonical_name=str(name),
                                domain_type=domain_type,
                            )
                            domain_entities += 1
            profile_name = str(pack.get("name", "mining-metallurgy"))
            await session.run(
                """
                MERGE (sv:SchemaVersion {version: $version})
                SET sv.domain_pack = $domain_pack,
                    sv.applied_at = datetime(),
                    sv.status = 'domain_pack_seeded'
                """,
                version=f"domain_pack:{profile_name}",
                domain_pack=profile_name,
            )
        aliases_path = root / "dictionaries" / "aliases_mvp.json"
        if aliases_path.exists():
            payload = json.loads(aliases_path.read_text(encoding="utf-8"))
            for entry in payload.get("aliases", []):
                canonical = entry["canonical"]
                entity_id = entity_id_for_name(canonical, "Material")
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