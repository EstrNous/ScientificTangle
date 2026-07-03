# Домен: auth_audit

Порт 8001. Auth, RBAC, audit.

## Ключевые файлы

- `services/auth_audit/app/` — HTTP API, security, service layer
- `infra/postgres/auth_audit_db/` — User, RefreshSession, репозиторий, seed
- `services/auth_audit/storage/` — Alembic-миграции
- `services/auth_audit/SERVICE_OVERVIEW.md` — обзор сервиса

## Архитектура

PostgreSQL (`scientific_tangle`), JWT RS256, JWKS, refresh rotation, structlog audit sink.
