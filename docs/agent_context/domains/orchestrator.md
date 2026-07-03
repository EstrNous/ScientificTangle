# Домен: orchestrator

Порт 8002. Пайплайны ingestion и query.

## Ключевые файлы

- `services/orchestrator/app/service/service.py` — create_task, run_query
- `infra/postgres/orchestrator_db/` — IngestionTask, QueryRun, ExportJob
- `services/orchestrator/storage/` — Alembic

## Зависимости downstream

ingestion, retrieval, model, auth_audit (JWKS).
