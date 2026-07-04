# Домен: orchestrator

Порт 8002. Пайплайны ingestion, query, export, audit.

## Ключевые файлы

- `services/orchestrator/app/service/service.py` — create_task, `_run_ingestion_pipeline`, `run_query`, `export_query_run`
- `services/orchestrator/app/api/ingestion.py` — `POST/GET /ingestion/tasks`
- `services/orchestrator/app/api/query.py` — `POST /query/run`, `GET /runs/{id}`, export, source, subgraph, search
- `infra/postgres/orchestrator_db/` — IngestionTask, QueryRun, ExportJob, audit_events
- `services/orchestrator/storage/` — Alembic

## Ingestion pipeline

```
upload → ingestion/normalize → knowledge/extract (Neo4j) → retrieval/documents/index (Qdrant)
```

Orchestrator требует `graph_write.mode=live` и `vector_write.mode=live`; иначе задача падает.

## Query pipeline

```
retrieval/v1/query → model gaps → knowledge/v1/graph/subgraph → model answers/synthesize → QueryRun в PG
```

## Export

```
gateway → orchestrator/export_query_run → export/v1/jobs → MinIO
```

Orchestrator остаётся authoritative owner для `ExportJob`/`export_artifacts` в `orchestrator_db`: повторно проверяет доступ к `SourceSpan`, пишет audit и сохраняет metadata артефакта. Export service рендерит Markdown/JSON/JSON-LD и кладёт artifact в MinIO.

## Зависимости downstream

ingestion, knowledge, retrieval, model, export; JWT через JWKS (auth_audit).

## Gaps

- `service.py` концентрирует ingestion + query + export (~940 строк) — кандидат на декомпозицию
- Internal export call пока без service-to-service auth
