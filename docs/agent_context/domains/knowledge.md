# Домен: knowledge

Порт 8004. Граф, claims, entity resolution.

## Ключевые файлы

- `services/knowledge/app/` — API extraction/graph/health, lifespan Neo4j
- `services/knowledge/adapters/` — `Neo4jKnowledgeAdapter`, schema bootstrap, mapper, graph operations
- `infra/neo4j/` — constraints, indexes, migrator
- `ontology/` — core_schema, domain packs, validation
- `dictionaries/aliases_mvp.json` — seed aliases

## Принципы

Claim-based знание; не абсолютная истина без provenance.

## Текущий ingestion boundary

Structured extraction выполняется через Model Service. Подтверждённые артефакты пишутся в Neo4j через `Neo4jKnowledgeAdapter`; `StorageWriteResult.mode=live` при успешной записи.
