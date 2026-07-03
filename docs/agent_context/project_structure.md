# Структура проекта для агентов

Этот файл — общий навигационный контекст для Codex, Claude, Cursor, Antigravity, ZCode/Zed и других агентных систем.

## Обязательное правило синхронизации

Когда в проекте появляются новые значимые директории, сервисы, приложения, пакеты, контракты, схемы данных, миграции, инфраструктурные файлы или агентные инструкции, агент обязан обновить этот файл в том же коммите.

Если изменение локальное, временное или не должно быть частью архитектуры проекта, его нужно добавить в `.gitignore`, а не описывать здесь.

## Текущая структура

### Корневые файлы

- `README.md` — описание проекта; не менять без отдельного явного запроса.
- `.gitignore` — правила исключения локальных, временных и секретных файлов.
- `AGENTS.md` — главный файл правил для всех агентных систем.
- `CLAUDE.md` — адаптер правил для Claude Code.
- `ANTIGRAVITY.md` — адаптер правил для Antigravity.
- `ZCODE.md` — адаптер правил для ZCode/Zed-подобных агентов.
- `.cursor/rules/project.mdc` — always-on правила для Cursor.
- `.github/copilot-instructions.md` — инструкции для GitHub Copilot.
- `.zed/rules/project.md` — правила для Zed Agent.
- `docker-compose.yml` — полная локальная среда (сервисы + PostgreSQL + Neo4j + Qdrant + MinIO + Redis + nginx).
- `docker-compose.prod.yml` — production-оверрайды (ресурсы, логирование, реплики).
- `Makefile` — цели сборки и управления: up, down, build, logs, seed, e2e, eval, test и др.
- `.env.example` — шаблон переменных окружения для копирования в `.env`.

### Документация

- `docs/nauchny_klubok_top1_tz.md` — главный план, ТЗ и продуктово-технический контекст.
- `docs/02_architecture.md` — архитектурный документ: карта сервисов, хранилища, маршрутизация, healthcheck, структура сервиса.
- `docs/agent_prompts/system.md` — системный промпт строгой работы по ТЗ.
- `docs/agent_prompts/before_implementation.md` — чек перед имплементацией.
- `docs/agent_prompts/new_chat.md` — промпт для переноса работы в новый чат.
- `docs/agent_prompts/quality_gate.md` — финальная проверка качества перед завершением задачи.
- `docs/agent_context/project_structure.md` — этот файл, карта структуры проекта для агентов.
- `docs/agent_context/sync_rules.md` — правила синхронизации контекста между агентами.

### Общий код (`shared/`)

- `shared/pyproject.toml` — пакет `scientific-tangle-shared`, подключается как path dependency из каждого сервиса.
- `shared/contracts/` — Pydantic-модели DTO: NormalizedDocument, SourceSpan, TableBlock, Quantity, GeoContext, AccessPolicy, Claim, QueryIR, EvidenceItem, EvidenceBundle, AnswerPayload, ServiceInfo.
- `shared/utils/` — утилиты (generate_request_id).
- `shared/logging/` — единая конфигурация structlog (JSON, контекст сервиса).
- `shared/config/` — базовый класс ServiceSettings с подключениями ко всем хранилищам.

### Микросервисы (`services/`)

Каждый сервис содержит `app/` (код), `tests/` (тесты), `Dockerfile`, `pyproject.toml`.

| Директория | Порт | Назначение |
|-----------|------|-----------|
| `services/gateway/` | 8000 | API Gateway / BFF — внешние API, валидация DTO, request_id, streaming, маршрутизация |
| `services/auth_audit/` | 8001 | Auth / Security / Audit — роли, access policy, audit log, правила доступа |
| `services/orchestrator/` | 8002 | Orchestrator — пайплайны, состояние задач, retries, timeouts |
| `services/ingestion/` | 8003 | Ingestion — загрузка, парсинг, NormalizedDocument, классификация, метаданные |
| `services/knowledge/` | 8004 | Knowledge — Schema Registry, сущности, entity resolution, claims, граф |
| `services/retrieval/` | 8005 | Retrieval — Query IR, гибридный поиск, fusion, reranking, EvidenceBundle |
| `services/model/` | 8006 | Model — LLM, embeddings, reranking, structured extraction, caching |
| `services/export/` | 8007 | Export — Markdown, PDF, JSON, JSON-LD |
| `services/notification/` | 8008 | Notification — профиль интересов, сопоставление с источниками, уведомления |

### UI (`ui/`)

- `ui/package.json` — заготовка для фронтенд-приложения.

### Инфраструктура (`infra/`)

- `infra/postgres/init.sql` — SQL-схемы PostgreSQL: users, audit_log, ingestion_tasks, query_runs, exports, notifications, user_interests, service_state, admin_settings.
- `infra/orchestrator_db/` — модели и миграции Orchestrator (база `orchestrator_db`): IngestionTask, QueryRun, ExportJob. SQLAlchemy 2.0 async, Alembic.
- `infra/chat_ui_db/` — модели и миграции Gateway/BFF (база `chat_ui_db`): ChatSession, ChatMessage, AdminSetting, ServiceState. SQLAlchemy 2.0 async, Alembic.
- `infra/notification_db/` — модели и миграции Notification (база `notification_db`): UserInterest, Notification. SQLAlchemy 2.0 async, Alembic.
- `infra/neo4j/` — конфигурация Neo4j.
- `infra/qdrant/` — конфигурация Qdrant.
- `infra/minio/buckets.txt` — список бакетов MinIO.
- `infra/nginx/nginx.conf` — reverse proxy для маршрутизации запросов к сервисам.
- `infra/monitoring/prometheus.yml` — конфигурация Prometheus для сбора /metrics со всех сервисов.
- `infra/docker/` — базовые Docker-образы.
- `infra/scripts/` — скрипты эксплуатации.

### Онтология (`ontology/`)

- `ontology/core_schema.yaml` — базовая онтология: типы сущностей, связи, единицы измерения.
- `ontology/domain_pack_mining_metallurgy.yaml` — доменный профиль горно-металлургии.
- `ontology/validation_rules.yaml` — правила валидации данных.

### Справочники (`dictionaries/`)

- `dictionaries/materials/` — материалы (руды, минералы, сплавы).
- `dictionaries/equipment/` — оборудование (печи, мельницы, реакторы).
- `dictionaries/properties/` — свойства материалов.
- `dictionaries/units/` — единицы измерения.
- `dictionaries/experts/` — эксперты и исследователи.
- `dictionaries/tags/` — теги классификации.

### Оценка качества (`eval/`)

- `eval/gold_questions.json` — эталонные вопросы с ожидаемыми типами ответов и тегами.
- `eval/run_eval.py` — скрипт для запуска оценки через API.
- `eval/reports/` — отчёты оценки.

### Демо (`demo/`)

- `demo/seed_data/` — исходные файлы для загрузки в систему.
- `demo/official_questions.md` — официальные вопросы для демонстрации.
- `demo/screenshots/` — скриншоты интерфейса.

### Тесты (`tests/`)

- `tests/e2e/` — сквозные тесты.
- `tests/integration/` — интеграционные тесты.
- `tests/performance/` — нагрузочные тесты.

## Сервисы

### services/auth_audit/

Микросервис аутентификации, авторизации (RBAC) и аудита.

- `src/models/base.py` — общий `DeclarativeBase` (SQLAlchemy 2.0 Async) и `TimestampMixin` для auth_audit.
- `src/models/auth.py` — модели RBAC: `User`, `Role`, `Permission`, `UserRole`, `RolePermission`. База `auth_db`.
- `src/models/audit.py` — модель `AuditEvent`. База `audit_db`.
- `README.md` — описание сервиса, стек, схема баз, индексы.

Архитектура: DB-per-Service — каждая база (auth_db, audit_db) физически отдельная БД внутри одного PostgreSQL-инстанса.

## Базы данных (DB-per-Service в infra/)

### infra/orchestrator_db/

База данных оркестратора (база `orchestrator_db`). Управление задачами ингеста, запусками запросов и экспортом.

- `models.py` — модели: `IngestionTask`, `QueryRun`, `ExportJob`. Статусы через `StrEnum`. JSONB для report, query_ir, retrieval_trace.
- `database.py` — фабрика `create_database()` (async engine + sessionmaker).
- `config.py` — `OrchestratorDbSettings` (env prefix `ORCHESTRATOR_`).
- `alembic.ini` — конфигурация Alembic, `script_location = storage`.
- `storage/env.py` — окружение Alembic (async engine from config).
- `storage/versions/0001_create_orchestrator_tables.py` — стартовая миграция.

### infra/chat_ui_db/

База данных шлюза/BFF (база `chat_ui_db`). История чатов, системные настройки, состояние сервисов.

- `models.py` — модели: `ChatSession`, `ChatMessage` (FK на chat_sessions с CASCADE), `AdminSetting`, `ServiceState`. JSONB для setting_value.
- `database.py` — фабрика `create_database()` (async engine + sessionmaker).
- `config.py` — `ChatUiDbSettings` (env prefix `GATEWAY_`).
- `alembic.ini` — конфигурация Alembic, `script_location = storage`.
- `storage/env.py` — окружение Alembic (async engine from config).
- `storage/versions/0001_create_chat_ui_tables.py` — стартовая миграция.

### infra/notification_db/

База данных уведомлений (база `notification_db`). Профили интересов пользователей и уведомления.

- `models.py` — модели: `UserInterest` (unique index на user_id), `Notification` (index на is_read). JSONB для extracted_entities.
- `database.py` — фабрика `create_database()` (async engine + sessionmaker).
- `config.py` — `NotificationDbSettings` (env prefix `NOTIFICATION_`).
- `alembic.ini` — конфигурация Alembic, `script_location = storage`.
- `storage/env.py` — окружение Alembic (async engine from config).
- `storage/versions/0001_create_notification_tables.py` — стартовая миграция.

## Как поддерживать файл

- Пиши на русском.
- Описывай назначение, а не внутренние детали реализации.
- Не документируй временные артефакты, кеши, IDE-индексы и локальные данные.
- Если структура пока не финальная, фиксируй текущее состояние и помечай будущие зоны только после их появления в репозитории.
