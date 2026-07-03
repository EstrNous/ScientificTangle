# Домен: knowledge

Порт 8004. Граф, claims, entity resolution.

## Ключевые файлы

- `services/knowledge/app/` — schema registry, entities, claims
- `ontology/` — core_schema, domain packs, validation
- Neo4j adapters

## Принципы

Claim-based знание; не абсолютная истина без provenance.

## Текущий ingestion boundary

Structured extraction выполняется через Model Service. Запись в Neo4j пока представлена типизированным `StorageWriteResult` с `mode=mock` и warning `neo4j_adapter_pending`; mock не сохраняет факты.
