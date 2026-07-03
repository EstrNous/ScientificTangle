# Структура проекта для агентов

Этот файл — общий навигационный контекст для Codex, Claude, Cursor, ZCode/Zed и других агентных систем.

## Обязательное правило синхронизации

Когда в проекте появляются новые значимые директории, сервисы, приложения, пакеты, контракты, схемы данных, миграции, инфраструктурные файлы или агентные инструкции, агент обязан обновить этот файл в том же коммите.

Если изменение локальное, временное или не должно быть частью архитектуры проекта, его нужно добавить в `.gitignore`, а не описывать здесь.

## Текущая структура

### Корневые файлы

- `README.md` — описание проекта; не менять без отдельного явного запроса.
- `.gitignore` — правила исключения локальных, временных и секретных файлов.
- `AGENTS.md` — hard rules (L0) для всех агентных систем.
- `CLAUDE.md` — указатель для Claude Code.
- `ZCODE.md` — указатель для ZCode/Zed.
- `.cursor/rules/project.mdc` — always-on L0 для Cursor.
- `.github/copilot-instructions.md` — инструкции для GitHub Copilot.
- `.zed/rules/project.md` — правила для Zed Agent.
- `docker-compose.yml` — полная локальная среда (сервисы + PostgreSQL + Neo4j + Qdrant + MinIO + Redis + nginx), включая запуск миграций `auth_audit` и `orchestrator`, а также подключение внешних RSA-секретов.
- `docker-compose.prod.yml` — production-оверрайды (ресурсы, логирование, реплики).
- `Makefile` — цели сборки и управления: up, up-auth, down, build, logs, seed, e2e, eval, test и др.
- `.env.example` — шаблон переменных окружения для копирования в `.env`.

### Документация

- `docs/nauchny_klubok_top1_tz.md` — полное ТЗ (читать выборочно).
- `docs/tz/` — сжатые выдержки: `index.md`, `mvp.md`, `agent_constraints.md`, `contracts.md`.
- `docs/agent_context/git_workflow.md` — ветки, rebase, PR, конфликты; без локального merge в `dev`.
- `docs/agent_context/task_router.md` — маршрутизация контекста по типу задачи.
- `docs/agent_context/rules_full.md` — расширенные правила (L1).
- `docs/agent_context/domains/` — краткий контекст по сервисам.
- `docs/02_architecture.md` — архитектурный документ: карта сервисов, хранилища, маршрутизация, healthcheck, структура сервиса.
- `docs/agent_prompts/every_chat.md` — эталонная строка для каждого чата
- `docs/agent_prompts/system.md` — системный промпт строгой работы по ТЗ.
- `docs/agent_prompts/before_implementation.md` — чек перед имплементацией.
- `docs/agent_prompts/new_chat.md` — промпт для переноса работы в новый чат.
- `docs/agent_prompts/quality_gate.md` — финальная проверка качества перед завершением задачи.
- `docs/agent_context/project_structure.md` — этот файл, карта структуры проекта для агентов.
- `docs/agent_context/sync_rules.md` — правила синхронизации контекста между агентами.
- `docs/agent_context/ml_mvp_status.md` — текущий статус ML MVP, открытые gaps и позиция по VL/OCR.

### Общий код (`shared/`)

- `shared/pyproject.toml` — пакет `scientific-tangle-shared`, подключается как path dependency из каждого сервиса.
- `shared/contracts/` — Pydantic-модели DTO, включая NormalizedDocument, SourceSpan, QueryIR, EvidenceBundle, AnswerPayload, UserRole, StoredSource, IngestionReport и IngestionTaskPayload.
- `shared/utils/` — утилиты (generate_request_id).
- `shared/logging/` — единая конфигурация structlog (JSON, контекст сервиса).
- `shared/config/` — базовый класс ServiceSettings с подключениями ко всем хранилищам.
- `shared/security/` — повторно используемая проверка access token через RS256/JWKS.
- `shared/web/` — единый request_id, зависимости аутентификации и нормализованные API-ошибки.
- `shared/metrics/` — Prometheus RED-метрики и `/metrics` для всех сервисов.

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
| `services/model/` | 8006 | Model — embeddings, structured extraction, Query IR, reranking/scoring, answer synthesis, prompt/schema registry |
| `services/export/` | 8007 | Export — Markdown, PDF, JSON, JSON-LD |
| `services/notification/` | 8008 | Notification — профиль интересов, сопоставление с источниками, уведомления |

Gateway, Orchestrator и Ingestion используют слои по образцу `auth_audit`: HTTP-маршруты находятся в `app/api`, сборка зависимостей — в `app/core`, работа с БД — в `app/db`, прикладная логика — в `app/service`, миграции — в `storage`.

### UI (`ui/`)

- `ui/package.json` — заготовка для фронтенд-приложения Next.js.
- `ui/Dockerfile` — nginx-skeleton на порту 3000 для Sync 2.
- `ui/public/index.html` — стартовая страница skeleton.
- `ui/nginx.conf` — конфигурация nginx внутри UI-контейнера.

### Инфраструктура (`infra/`)

- `infra/postgres/init.sql` — SQL-схемы PostgreSQL: users, audit_log, ingestion_tasks, query_runs, exports, notifications, user_interests, service_state, admin_settings.
- `infra/neo4j/` — конфигурация Neo4j.
- `infra/qdrant/` — конфигурация Qdrant.
- `infra/minio/buckets.txt` — список бакетов MinIO.
- `infra/nginx/nginx.conf` — reverse proxy (порт 80), маршрутизирует `/api/auth/` и JWKS в `auth_audit`, остальные внешние API — в Gateway.
- `infra/monitoring/prometheus.yml` — конфигурация Prometheus для сбора /metrics со всех сервисов.
- `infra/monitoring/grafana/` — provisioning datasource и SRE-дашборды Grafana.
- `infra/nginx/Dockerfile` — nginx с basic auth для `/grafana/`.
- `infra/docker/Dockerfile.python-service` — multistage Dockerfile для Python-сервисов (deps + runtime, shared).
- `infra/scripts/` — скрипты эксплуатации (seed, reset-demo — в разработке).

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

- `eval/gold_questions.json` — эталонные MVP-вопросы с ожидаемыми сущностями, числовыми, географическими и временными constraints.
- `eval/gold_mining.py` — dev-only генератор corpus-derived gold candidates из `NormalizedDocument` и `SourceSpan`.
- `eval/yandex_disk_corpus.py` — dev-only загрузчик публичного корпуса с Яндекс.Диска в локальную ignored-директорию.
- `eval/run_eval.py` — скрипт для запуска оценки через API, расчёта evidence-first/top-1 метрик и записи Markdown/JSON отчётов.
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

### services/model/

Микросервис модельного слоя для evidence-first ML MVP.

- `app/api/v1.py` — локальные v1 endpoints для embeddings, structured extraction, Query IR, reranking/scoring, answer synthesis, prompt registry и schema registry.
- `app/contracts.py` — локальные Pydantic-модели model service: confirmed/candidate extraction layer, reason codes, unsupported warnings, conflict/gap/interest/notification/JSON-LD DTO и JSON Schema registry entries.
- `app/services.py` — модельные операции с Yandex provider через `.env` и deterministic degraded fallback; confirmed outputs требуют `SourceSpan`, candidates получают reason codes.
- `app/yandex_client.py` — HTTP-клиент Yandex AI Studio для embeddings и text generation по `YANDEX_API_KEY` и `YANDEX_FOLDER_ID`.
- `app/prompt_registry.py` и `app/prompts/` — версионированные prompt templates для model outputs.
- `app/schema_registry.py` — registry JSON Schema для валидируемых model outputs.
- `tests/test_model_v1.py` — проверки evidence-first правил, Query IR constraints, candidate reason codes, answer synthesis, conflict/gap logic, interests, notifications и JSON-LD enrichment.

### services/auth_audit/

Микросервис аутентификации, авторизации (RBAC) и аудита.

- `src/models/base.py` — общий `DeclarativeBase` (SQLAlchemy 2.0 Async) и `TimestampMixin` для auth_audit.
- `src/models/auth.py` — модели RBAC: `User`, `Role`, `Permission`, `UserRole`, `RolePermission`. База `auth_db`.
- `src/models/audit.py` — модель `AuditEvent`. База `audit_db`.
- `README.md` — описание сервиса, стек, схема баз, индексы.

Архитектура: DB-per-Service — каждая база (auth_db, audit_db) физически отдельная БД внутри одного PostgreSQL-инстанса.

### services/gateway/

Внешний API для загрузки документов и чтения статуса ingestion-задач. Проверяет JWT через JWKS, создаёт или принимает `request_id`, нормализует ошибки и передаёт запросы в Orchestrator.

### services/orchestrator/

Владелец состояния ingestion-задач. Сохраняет задачи в PostgreSQL, контролирует доступ владельца и администратора, вызывает Ingestion и хранит отчёт о загруженных источниках. Миграции находятся в `storage/`, образ собирается через собственный multistage `Dockerfile`.

### services/ingestion/

Принимает аутентифицированные исходные файлы, безопасно формирует объектные ключи, вычисляет SHA-256 и сохраняет данные в бакет MinIO `source-files`. При частичном сбое удаляет уже записанные объекты.

## Как поддерживать файл

- Пиши на русском.
- Описывай назначение, а не внутренние детали реализации.
- Не документируй временные артефакты, кеши, IDE-индексы и локальные данные.
- Если структура пока не финальная, фиксируй текущее состояние и помечай будущие зоны только после их появления в репозитории.
