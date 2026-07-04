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
- `Makefile` — цели сборки и управления: bootstrap, up, up-auth, down, build, logs, seed, ingest-demo, eval, eval-yandex-live, perf-smoke, test, test-yandex-live и др.
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
- `docs/agent_context/implementation_quality_report.md` — оценка реализации vs ТЗ по сервисам, стеку и gaps.
- `docs/agent_context/query_pipeline.md` — сквозной пайплайн запроса user → answer.
- `docs/agent_context/top1_parallel_execution_plan.md` — поэтапный план параллельной работы двух Backend/ML-специалистов и одного Frontend-специалиста.
- `docs/agent_context/nornikel_parallel_execution_plan.md` — параллельный план закрытия gaps НорСинтез/ScientificTangle по ролям Databases, Backend/ML, Frontend и Validator без live model calls.
- `docs/agent_context/nornikel_e0_db_baseline.md` — E0 storage baseline: PostgreSQL, MinIO, Neo4j, Qdrant, seed/reset gaps.
- `docs/agent_context/nornikel_e0_bml_contract_api_eval_baseline.md` — E0 baseline контрактов, API, eval inputs и dataset checklist для E2.
- `docs/agent_context/nornikel_e0_fe_ui_audit.md` — E0 UI audit: routes, stores, mock/live boundaries, frontend gaps E1–E7.
- `docs/agent_context/nornikel_e0_validation_report.md` — E0 validation report: merge gate, unified gaps, blockers перед E1.
- `docs/agent_context/nornikel_e1_db_storage_ownership.md` — E1 Databases: migrations `0008`/`0002`, ownership таблиц, индексы, seed/reset.
- `docs/agent_context/nornikel_e1_bml_no_live_policy.md` — E1 Backend/ML policy: no-live ограничения, контрактные skeleton routes и storage dependencies.
- `docs/agent_context/nornikel_e1_validation_report.md` — E1 validation report: merge gate, contract/UI integration checks, blockers перед E2.
- `docs/agent_context/nornikel_e2_db_storage_ownership.md` — E2 Databases: migration `0009`, review/source lookup, cascade delete metadata, fixtures.
- `docs/agent_context/nornikel_e2_bml_gold_dataset_report.md` — E2 Backend/ML: offline gold dataset, reviewed SourceSpan fixtures, reason codes.
- `docs/agent_context/nornikel_e2_validation_report.md` — E2 validation report: merge gate, dataset/source/review checks, blockers перед E3.
- `docs/agent_context/top1_e0_contract_audit.md` — аудит контрактов query path и freeze points для этапов E1–E4.
- `docs/agent_context/top1_e1_bm2_ml_policy.md` — E1 policy для классов запросов, retrieval planner rules, verification reason codes и synthesis/AnswerPayloadV2 expectations.
- `docs/agent_context/top1_e4_bm1_eval_regression.md` — E4 pinned demo artifact, eval suites и comparison gate для regression checks.
- `docs/agent_context/top1_e5_bm1_integration_eval.md` — E5 integration eval report по внешним backend merges, contract drift и обязательным fixes перед E6.
- `docs/agent_context/audit_report.md` — P0/P1 аудит репозитория и статусы инфраструктуры.
- `docs/agent_context/prod_readiness_analysis.md` — план глубокого production-readiness анализа: scenarios, gates, gaps и offline verification без live model calls.
- `docs/agent_context/prod_readiness_task_cards.md` — пул task cards для закрытия production-readiness gaps с зависимостями и acceptance criteria.

### Общий код (`shared/`)

- `shared/pyproject.toml` — пакет `scientific-tangle-shared`, подключается как path dependency из каждого сервиса.
- `shared/contracts/` — Pydantic-модели DTO, включая стабильный SourceSpan ID, QueryIR, EvidenceBundle, QueryRunPayload, SourcePayload, GraphSubgraph, SearchResultPayload, interests/notifications/review/export/delete/eval payloads и результаты записи Neo4j/Qdrant.
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

Gateway, Orchestrator и Ingestion используют слои по образцу `auth_audit`: HTTP-маршруты в `app/api`, зависимости в `app/core`, прикладная логика в `app/service`. Слой PostgreSQL для `auth_audit` и `orchestrator` — в `infra/postgres/*_db/`; Alembic-миграции остаются в `services/<name>/storage/`.

### UI (`ui/`)

Фронтенд-приложение Vite + React. Работает автономно на mock API (`VITE_USE_MOCK=true`).

- `ui/package.json` — зависимости и скрипты (`dev`, `build`, `preview`, `lint`).
- `ui/vite.config.js` — Vite, proxy `/api` → Gateway.
- `ui/tailwind.config.js`, `ui/postcss.config.js` — Tailwind CSS.
- `ui/index.html` — точка входа HTML.
- `ui/Dockerfile` — multi-stage: Vite build + nginx на порту 3000.
- `ui/nginx.conf` — конфигурация nginx внутри UI-контейнера.
- `ui/public/` — статические файлы для контейнера.
- `ui/.env.local.example` — шаблон переменных UI.
- `ui/src/main.jsx` — bootstrap React.
- `ui/src/app/` — `App.jsx`, `routes.jsx` (маршруты и RBAC).
- `ui/src/layout/` — `DashboardShell`, `TopBar`, `TabNav`.
- `ui/src/pages/` — ChatPage, GraphPage, StrategicPage, LabPage, AdminPage, UploadPage, SearchPage.
- `ui/src/components/shared/` — Loader, ErrorBoundary, RoleSwitcher, NotificationBell, PageShell, ProfileButton, DarkModeToggle.
- `ui/src/components/chat/` — чат, ответы, evidence, export.
- `ui/src/components/graph/` — граф, таблица сущностей, ingestion, dropzone.
- `ui/src/components/strategic/` — ManagerDashboard, EvaluationDashboard.
- `ui/src/components/lab/` — CoverageMatrix, GapConflictView.
- `ui/src/components/admin/` — SourceViewer, AuditLogTable.
- `ui/src/stores/` — authStore, localeStore, notificationStore, themeStore (Zustand).
- `ui/src/i18n/` — ru/en, synonyms.json.
- `ui/src/api/client.js` — mock/real переключатель.
- `ui/src/api/auth.js`, `ui/src/api/chat.js`, `ui/src/api/graph.js` — реальные API чата и графа.
- `ui/src/api/contracts/` — имена DTO (зеркало shared/contracts).
- `ui/src/api/mock/` — JSON demo-данные для экранов без backend.
- `ui/src/utils/graphFilters.js`, `ui/src/utils/graphSearch.js` — клиентская фильтрация графа.
- `ui/src/hooks/` — useRoleAccess.
- `ui/src/utils/reportExport.js` — экспорт MD/JSON/PDF.

### Инфраструктура (`infra/`)

- `infra/postgres/` — DB-per-service слои (auth_audit_db, orchestrator_db, chat_ui_db, export_db, notification_db); миграции через Alembic в `services/<name>/storage/` или `infra/postgres/<db>/storage/`.

- `infra/orchestrator_db/` — модели и миграции Orchestrator (база `orchestrator_db`): IngestionTask, QueryRun, ExportJob. SQLAlchemy 2.0 async, Alembic.
- `infra/chat_ui_db/` — модели и миграции Gateway/BFF (база `chat_ui_db`): ChatSession, ChatMessage, AdminSetting, ServiceState. SQLAlchemy 2.0 async, Alembic.
- `infra/notification_db/` — модели и миграции Notification (база `notification_db`): UserInterest, Notification. SQLAlchemy 2.0 async, Alembic.
- `infra/neo4j/` — схема Neo4j MVP: `constraints.cypher`, `indexes.cypher`, `migrator.py` (SchemaVersion, bootstrap при старте Knowledge).
- `infra/qdrant/` — описание Qdrant collection `st_evidence_v1`, payload indexes и access-aware retrieval.
- `infra/minio/buckets.txt` — список бакетов MinIO.
- `infra/nginx/nginx.conf` — reverse proxy (порт 80), маршрутизирует `/api/auth/` и JWKS в `auth_audit`, остальные внешние API — в Gateway.
- `infra/monitoring/prometheus.yml` — конфигурация Prometheus для сбора /metrics со всех сервисов.
- `infra/monitoring/grafana/` — provisioning datasource и SRE-дашборды Grafana.
- `infra/nginx/Dockerfile` — nginx с basic auth для `/grafana/`.
- `infra/docker/Dockerfile.python-service` — multistage Dockerfile для Python-сервисов (deps + runtime, shared).
- `infra/scripts/` — скрипты эксплуатации.
- `scripts/` — локальные MVP smoke/eval/seed scripts: demo seed, Yandex live smoke, official eval, performance smoke, `neo4j_smoke.py`.

### Онтология (`ontology/`)

- `ontology/core_schema.yaml` — базовая онтология: типы сущностей, связи, единицы измерения.
- `ontology/domain_pack_mining_metallurgy.yaml` — доменный профиль горно-металлургии.
- `ontology/validation_rules.yaml` — правила валидации данных.

### Справочники (`dictionaries/`)

- `dictionaries/aliases_mvp.json` — MVP-словарь алиасов для demo/eval.
- `dictionaries/units_mvp.json`, `dictionaries/geographies_mvp.json` — версионируемые seed-данные единиц и географии для demo-пакета справочников.
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
- `eval/run_eval.py` — скрипт для запуска оценки через API, выбора regression suite, опциональной нормализации raw eval documents через ingestion, расчёта evidence-first/top-1 метрик, comparison report и записи Markdown/JSON отчётов с dashboard-ready блоком.
- `eval/pinned_demo_artifact.json` — зафиксированный manifest входов demo/eval с sha256 и правилами обновления.
- `eval/regression_suites.json` — разбиение eval на official, hybrid retrieval, access filtering, unsupported claims и answer completeness suites.
- `eval/reports/` — отчёты оценки.

### Демо (`demo/`)

- `demo/seed_data/` — исходные файлы для загрузки в систему, включая `mvp_normalized_documents.json`.
- `demo/official_questions.md` — официальные вопросы для демонстрации.
- `demo/screenshots/` — скриншоты интерфейса.

### Тесты (`tests/`)

- `tests/e2e/` — сквозные тесты.
- `tests/integration/` — интеграционные тесты; `test_neo4j_smoke.py` — opt-in smoke Neo4j (`RUN_NEO4J_INTEGRATION=1`, `make test-neo4j-integration`).
- `tests/performance/` — нагрузочные тесты.

## Сервисы

### services/model/

Микросервис модельного слоя для evidence-first ML MVP.

- `app/api/v1.py` — локальные v1 endpoints для embeddings, structured extraction, Query IR, reranking/scoring, answer synthesis, prompt registry и schema registry.
- `app/contracts.py` — локальные Pydantic-модели model service: confirmed/candidate extraction layer, reason codes, unsupported warnings, conflict/gap/interest/notification/JSON-LD DTO и JSON Schema registry entries.
- `app/services.py` — модельные операции с Yandex provider через `.env`, task routing, in-memory cache и deterministic degraded fallback; confirmed outputs требуют `SourceSpan`, candidates получают reason codes.
- `app/yandex_client.py` — HTTP-клиент Yandex AI Studio для embeddings и text generation по `YANDEX_API_KEY` и `YANDEX_FOLDER_ID`.
- `app/prompt_registry.py` и `app/prompts/` — версионированные prompt templates для model outputs.
- `app/schema_registry.py` — registry JSON Schema для валидируемых model outputs.
- `tests/test_model_v1.py` — проверки evidence-first правил, Query IR constraints, candidate reason codes, answer synthesis, conflict/gap logic, interests, notifications и JSON-LD enrichment.

### ML integration slice

- `services/ingestion/app/api/documents.py` — internal text/table fallback normalization endpoint; task pipeline дополнительно нормализует сохранённые PDF, DOCX, PPTX, DOC и ZIP через реестр parser-адаптеров.
- `services/ingestion/app/api/dictionaries.py` — безопасное сохранение и проверка ZIP-пакета `dictionary-package.v1`.
- `services/knowledge/app/api/dictionaries.py` — версии справочников, атомарная активация и обогащение Query IR закреплённой версией.
- `services/knowledge/app/api/extraction.py` — internal handoff `NormalizedDocument` → model structured extraction → `Neo4jKnowledgeAdapter.write_bundle` с закреплённой версией справочника.
- `services/knowledge/app/api/graph.py` — bootstrap/reset/subgraph/neighbors/aliases/conflicts/gaps/entities/filter/measurements/evidence/claims-rank.
- `services/knowledge/adapters/` — `Neo4jKnowledgeAdapter`, DTO, mapper, Query IR compiler, graph operations.
- `services/retrieval/app/api/query.py` — internal Query IR, Qdrant bootstrap/index/reset, vector search с access filter и model rerank; `StorageWriteResult.mode=live`.
- `services/retrieval/app/qdrant_adapter.py` — live Qdrant adapter, collection `st_evidence_v1`.
- `services/retrieval/app/api/indexing.py` — legacy endpoint, не смонтирован в FastAPI app.
- `services/orchestrator/app/api/query.py` и `services/gateway/app/api/query.py` — тонкий query run/proxy path для eval-compatible ответа через `EvidenceBundle` и answer synthesis.

### services/auth_audit/

Микросервис аутентификации, авторизации (RBAC) и аудита.

- `app/api/` — `factory.py`, `auth.py`, `users.py`, `health.py`, `errors.py`, `cookies.py`.
- `storage/` — Alembic-миграции для БД auth_audit (metadata из `infra.postgres.auth_audit_db`).
- Слой PostgreSQL: `infra/postgres/auth_audit_db/` (модели, репозиторий, схемы, seed).

## Базы данных (DB-per-Service в infra/postgres/)

### infra/postgres/auth_audit_db/

База данных auth_audit (база `scientific_tangle`). Пользователи, роли, refresh-сессии.

- `models.py` — модели: `User`, `RefreshSession`, enum `Role`.
- `database.py` — фабрика `create_database()` (async engine + sessionmaker).
- `repository.py` — `AuthRepository`, `SqlAlchemyAuthRepository`.
- `schemas.py` — Pydantic-схемы запросов и ответов API.
- `seed.py` — сидирование пользователей из env (`AUTH_SEED_*`).
- `config.py` — `AuthAuditDbSettings` (env prefix `AUTH_AUDIT_`).
- `alembic.ini` — конфигурация Alembic (миграции пока в `services/auth_audit/storage/`).

### infra/postgres/orchestrator_db/

База данных оркестратора (база `scientific_tangle`, таблица версий `alembic_version_orchestrator`). Управление задачами ингеста, запусками запросов и экспортом.

- `models.py` — модели: `IngestionTask`, `QueryRun`, `ExportJob`, `ExportArtifact`, `IndexedDocument`, `ReviewDecision`, `SourceSpanLookup`, `DocumentCascadeRefs`, `AuditEvent`, RBAC-таблицы.
- `repository.py` — `IngestionTaskRepository` (create/get/set_report/mark_failed).
- `review_storage.py` — `ReviewStorageRepository` для review decisions, source span lookup и cascade refs.
- `e2_fixtures.py`, `seed_e2_fixtures.py` — offline fixtures E2 review/source/delete.
- `database.py` — `create_database()`, `get_session()`.
- `config.py` — `OrchestratorDbSettings` (env prefix `ORCHESTRATOR_`).
- Alembic: `services/orchestrator/alembic.ini`, миграции в `services/orchestrator/storage/versions/` (`0001` — ingestion_tasks, `0002` — query_runs/export_jobs, `0003` — совместимость query_runs с прежним init SQL, `0004` — полный сохраняемый результат query run).
- `0007_add_dictionary_pinning.py` добавляет тип ingestion-задачи и закреплённую версию справочника для задач и query run.
- `0008_add_core_storage_foundation.py` — `review_decisions`, `export_artifacts`, tombstone `indexed_documents`, cursor-индексы audit/export.
- `0009_add_review_source_delete_storage.py` — `source_span_lookup`, `document_cascade_refs` для E2 review/source/delete.

### infra/fixtures/e2/

Offline DB fixtures для review/source/delete без live models (`review_source_delete.json`).

### infra/postgres/chat_ui_db/

База данных шлюза/BFF (база `chat_ui_db`). История чатов, системные настройки, состояние сервисов.

- `models.py` — модели: `ChatSession`, `ChatMessage` (FK на chat_sessions с CASCADE), `AdminSetting`, `ServiceState`. JSONB для setting_value.
- `database.py` — фабрика `create_database()` (async engine + sessionmaker).
- `config.py` — `ChatUiDbSettings` (env prefix `GATEWAY_`).
- `alembic.ini` — конфигурация Alembic, `script_location = storage`.
- `storage/env.py` — окружение Alembic (async engine from config).
- `storage/versions/0001_create_chat_ui_tables.py` — стартовая миграция.

### infra/postgres/notification_db/

База данных уведомлений (база `notification_db`). Профили интересов пользователей и уведомления.

- `models.py` — модели: `UserInterest`, `Notification`, `ExtractedEntity`, `NotificationMatchResult`. JSONB для extracted_entities и match_payload.
- `database.py` — фабрика `create_database()` (async engine + sessionmaker).
- `config.py` — `NotificationDbSettings` (env prefix `NOTIFICATION_`).
- `alembic.ini` — конфигурация Alembic, `script_location = storage`.
- `storage/env.py` — окружение Alembic (async engine from config).
- `storage/versions/0001_create_notification_tables.py` — стартовая миграция.
- `storage/versions/0002_add_core_notification_storage.py` — `reference_type`, `extracted_entities`, `notification_match_results`, индексы poll/unread.

### services/gateway/

Внешний API для загрузки документов, чтения статуса ingestion-задач, чата, графа знаний и поиска. Проверяет JWT через JWKS, создаёт или принимает `request_id`, нормализует ошибки и передаёт запросы в Orchestrator. Chat history в `chat_ui_db`.

- `app/api/query.py` — query, runs, export, source, subgraph, search.
- `app/api/chat.py` — chat sessions и messages.
- `app/api/graph.py` — `GET /graph`, `GET /graph/catalog`.
- `app/service/analytics_service.py` — GraphPayload через knowledge/retrieval; strategic/lab dashboards.

### services/orchestrator/

Владелец состояния ingestion-задач. Сохраняет задачи в PostgreSQL, контролирует доступ владельца и администратора, вызывает Ingestion и хранит отчёт о загруженных источниках. Миграции находятся в `storage/`, образ собирается через собственный multistage `Dockerfile`.

### services/ingestion/

Принимает аутентифицированные исходные файлы, безопасно формирует объектные ключи, вычисляет SHA-256 и сохраняет данные в бакет MinIO `source-files`. Нормализует PDF, DOCX, PPTX, DOC и ZIP в `NormalizedDocument`, `SourceSpan` и `TableBlock`; для DOC использует LibreOffice headless. При частичном сбое хранения удаляет уже записанные объекты.

## Как поддерживать файл

- Пиши на русском.
- Описывай назначение, а не внутренние детали реализации.
- Не документируй временные артефакты, кеши, IDE-индексы и локальные данные.
- Если структура пока не финальная, фиксируй текущее состояние и помечай будущие зоны только после их появления в репозитории.
