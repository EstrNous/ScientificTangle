# Auth / Audit Service

Микросервис аутентификации, авторизации (RBAC) и аудита.

## Ответственность

- Управление пользователями, ролями, разрешениями.
- Журналирование действий в `audit_events`.
- Проверка прав доступа к документам (access_level, allowed_roles).

## Базы данных

Сервис работает с двумя физическими базами внутри одного PostgreSQL-инстанса:

| База | Таблицы | Назначение |
|------|---------|-----------|
| `auth_db` | `users`, `roles`, `permissions`, `user_roles`, `role_permissions` | Ролевая модель, пользователи |
| `audit_db` | `audit_events` | Аудит-лог запросов, действий, экспорта |

## Стек

- Python 3.11+
- SQLAlchemy 2.0 (строго Async)
- Asyncpg
- Alembic
- Pydantic v2

## Модели SQLAlchemy

Все модели находятся в `src/models/`:

- `base.py` — общий `DeclarativeBase` и `TimestampMixin`.
- `auth.py` — `User`, `Role`, `Permission`, `UserRole`, `RolePermission`.
- `audit.py` — `AuditEvent`.

## Предопределённые роли (seed)

Роли не реализованы через PG ENUM — используются строки с валидацией на уровне приложения:

`admin`, `researcher`, `analyst`, `manager`, `external_partner`, `project_owner`, `reviewer`, `auditor`

## Миграции

```bash
cd services/auth_audit/alembic
alembic upgrade head
```

## Индексы

- `ix_audit_events_user_id` — FK на users
- `ix_audit_events_request_id` — поиск по request_id
- `ix_audit_events_status` — фильтрация по статусу
- `ix_audit_events_timestamp` — временной диапазон
- `ix_audit_events_action` — фильтрация по типу действия
- `uq_user_roles_user_role` — уникальность пары user+role
- `uq_role_permissions_role_perm` — уникальность пары role+permission
