# Домен: knowledge

Порт 8004. Граф, claims, entity resolution.

## Ключевые файлы

- `services/knowledge/app/api/extraction.py` — `POST /v1/documents/extract`
- `services/knowledge/app/api/graph.py` — 14 graph endpoints (bootstrap, reset, subgraph, neighbors, conflicts, gaps, entities, …)
- `services/knowledge/adapters/neo4j_adapter.py` — live Neo4j adapter (write, subgraph, conflicts, measurements)
- `services/knowledge/adapters/neo4j_storage_adapter.py` — обёртка StorageWriteResult
- `infra/neo4j/` — constraints, indexes, migrator
- `ontology/` — core_schema, domain packs, validation
- `dictionaries/aliases_mvp.json` — seed aliases

## Принципы

Claim-based знание; не абсолютная истина без provenance. Локальный граф ограничен идентификаторами доказательств конкретного query run.

## Текущий статус (2026-07-04)

**Реализовано:**

- Structured extraction через Model Service → `Neo4jKnowledgeAdapter.write_bundle`
- При успешной записи: `StorageWriteResult.mode=live`
- Graph API: subgraph по claim/entity/source_span IDs, conflicts, gaps, resolve-alias, claims/rank
- Bootstrap schema при старте (constraints/indexes из `infra/neo4j/`)

**Fallback:**

- Если Neo4j недоступен — `PendingKnowledgeStorageAdapter`, warning `neo4j_adapter_pending`; orchestrator падает ingestion pipeline при `mode != live`

## Зависимости

Neo4j, model (structured extraction), Redis (config).
