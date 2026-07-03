# Домен: auth_audit

Порт 8001. Auth, RBAC, audit.

## Ключевые файлы

- `services/auth_audit/src/models/` — User, Role, Permission, AuditEvent
- `services/auth_audit/README.md` — обзор сервиса

## Архитектура

DB-per-Service: auth_db и audit_db в одном PostgreSQL-инстансе.
