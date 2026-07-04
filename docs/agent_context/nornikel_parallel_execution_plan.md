# ScientificTangle / НорСинтез — параллельный план закрытия gaps

Дата: 2026-07-04.
База: `dev` и исходный gap-анализ `nornikel-gap-analysis.md`.
Цель: закрыть все выявленные разрывы FE/BE/DB/ML без live model calls и без смешивания независимых работ в одну большую ветку.

## 0. Роли и границы

В работе участвуют 5 человек:

- `Databases` — PostgreSQL, Alembic, MinIO, Neo4j, Qdrant, seed/reset, индексы, data lifecycle, audit storage.
- `Backend/ML` — gateway/orchestrator API, model/retrieval integration в offline/mock режиме, contracts, eval, gold dataset, e2e fixtures.
- `Frontend` — UI pages, stores, API clients, source viewer, chat UX, admin/audit/export/notification screens.
- `Validator` — отдельный проверяющий между этапами. Он не берёт feature work роли, а проверяет merged `dev`, заводит маленькие fix cards, если этап не закрыт.
- `External Orchestrator Refactor Owner` — отдельный человек вне этого плана. Он занимается расформированием god object в `services/orchestrator/app/service/service.py`. Остальные роли не трогают этот рефакторинг и не начинают крупное дробление orchestrator service.

`Backend/ML` — роль, которой нужен весь dataset. Она отвечает за расширенный offline gold dataset, expected `SourceSpan`, official scenarios, reviewed fixtures и no-live eval reports. Live модели не используются: ни Yandex, ни другие внешние inference endpoints.

## 1. Жёсткие ограничения

- Следовать `AGENTS.md` и `docs/agent_context/task_router.md`.
- Работать только в `feat/*`; `dev` не менять локальными merge.
- Перед карточкой: `git fetch origin`; ветку создавать от свежего `origin/dev` или rebase feature-ветки на `origin/dev`.
- Следующий этап начинается только после merge в `dev` всех PR трёх ролей текущего этапа и PR валидатора этого этапа.
- В рамках одного этапа `Databases`, `Backend/ML` и `Frontend` работают независимо.
- Если задача зависит от ещё не смерженной ветки другой роли, агент останавливается и пишет dependency.
- Если работа требует изменения shared contracts, public API, миграций, ontology или security, это допустимо только если карточка прямо говорит об этом.
- `README.md` не менять без отдельного запроса.
- В коде не добавлять комментарии, кроме форматов/генераторов/миграций/линтеров/юридических требований.
- Не хардкодить demo-ответы, official answers или факты без `SourceSpan`.
- Не использовать live model calls. Все model-related проверки должны быть deterministic/offline/mock.

Запрещено до отдельного финального разрешения:

```powershell
$env:RUN_MODEL_TESTS='1'; python scripts/run_tests.py
make eval-yandex-live
make test-yandex-live
python scripts/yandex_live_smoke.py
python scripts/eval_yandex_live.py
```

Если команда или тест внезапно требует live model, агент останавливает эту часть и пишет `blocked_by_policy`.

## 2. Шаблон промпта для трёх технических ролей

```text
Следуй AGENTS.md и docs/agent_context/task_router.md.

Выполни C:\Users\petro\Downloads\Telegram Desktop\nornikel-gap-analysis.md:
- этап: E<N>
- роль: <Databases | Backend/ML | Frontend>
- ветка: feat/nornikel-e<N>-<db|bml|fe>-<slug>

Работай только в рамках своей карточки.
Не бери задачи других ролей и следующих этапов.
Не трогай рефакторинг god object в services/orchestrator/app/service/service.py: это работа External Orchestrator Refactor Owner.
Не используй live models. Если проверка требует live model call, останови эту часть и пометь blocked_by_policy.
Если задача зависит от несмёрженного PR другой роли, остановись и явно напиши dependency.

Перед работой:
- git fetch origin
- создай ветку от свежего origin/dev или rebase текущую feature-ветку на origin/dev

После реализации:
- прогони релевантные проверки
- сделай коммит одной строкой на русском в формате `feat: сделано то-то`
- push своей feat-ветки
- в dev не мержи
```

Пример:

```text
Следуй AGENTS.md и docs/agent_context/task_router.md.

Выполни C:\Users\petro\Downloads\Telegram Desktop\nornikel-gap-analysis.md:
- этап: E2
- роль: Backend/ML
- ветка: feat/nornikel-e2-bml-gold-dataset

Работай только в рамках своей карточки.
Не бери задачи других ролей и следующих этапов.
Не трогай рефакторинг god object в services/orchestrator/app/service/service.py.
Не используй live models.
Если задача зависит от несмёрженного PR другой роли, остановись и явно напиши dependency.

Перед работой:
- git fetch origin
- создай ветку от свежего origin/dev или rebase текущую feature-ветку на origin/dev

После реализации:
- прогони релевантные проверки
- сделай коммит одной строкой на русском в формате `feat: сделано то-то`
- push своей feat-ветки
- в dev не мержи
```

## 3. Шаблон промпта для валидатора

```text
Следуй AGENTS.md и docs/agent_context/task_router.md.

Проверь C:\Users\petro\Downloads\Telegram Desktop\nornikel-gap-analysis.md:
- этап: E<N>
- роль: Validator
- ветка: feat/nornikel-e<N>-validator

Работай только после того, как PR ролей Databases, Backend/ML и Frontend для этапа E<N> смержены в dev.
Начни от свежего origin/dev.
Не бери feature work следующего этапа.
Не используй live models. Все live quality checks пометь blocked_by_policy.
Не трогай рефакторинг god object в services/orchestrator/app/service/service.py.

Что сделать:
- проверить acceptance criteria этапа;
- прогнать минимальные релевантные проверки;
- составить validation report в docs/agent_context/;
- если есть маленькие интеграционные дефекты этапа, исправить только их;
- если дефект требует отдельной роли или следующего этапа, зафиксировать blocker/dependency.

После проверки:
- сделай коммит одной строкой на русском в формате `feat: проверен этап E<N>`
- push ветки
- в dev не мержи
```

## 4. Карта этапов и веток

| Этап | Databases | Backend/ML | Frontend | Validator gate |
|---|---|---|---|---|
| E0. Baseline и freeze | `feat/nornikel-e0-db-baseline` | `feat/nornikel-e0-bml-contract-audit` | `feat/nornikel-e0-fe-ui-audit` | `feat/nornikel-e0-validator` |
| E1. Persistent foundations | `feat/nornikel-e1-db-core-storage` | `feat/nornikel-e1-bml-core-api-contracts` | `feat/nornikel-e1-fe-api-foundation` | `feat/nornikel-e1-validator` |
| E2. Dataset, sources, review | `feat/nornikel-e2-db-review-source-data` | `feat/nornikel-e2-bml-gold-dataset` | `feat/nornikel-e2-fe-review-source-ui` | `feat/nornikel-e2-validator` |
| E3. User workflows | `feat/nornikel-e3-db-workflow-state` | `feat/nornikel-e3-bml-workflow-wiring` | `feat/nornikel-e3-fe-workflows` | `feat/nornikel-e3-validator` |
| E4. Evidence, RBAC, search | `feat/nornikel-e4-db-evidence-access` | `feat/nornikel-e4-bml-evidence-retrieval` | `feat/nornikel-e4-fe-evidence-access` | `feat/nornikel-e4-validator` |
| E5. Export, notifications, audit | `feat/nornikel-e5-db-product-events` | `feat/nornikel-e5-bml-export-notifications` | `feat/nornikel-e5-fe-export-notifications` | `feat/nornikel-e5-validator` |
| E6. Offline quality and CI | `feat/nornikel-e6-db-seed-reliability` | `feat/nornikel-e6-bml-offline-quality` | `feat/nornikel-e6-fe-e2e-hardening` | `feat/nornikel-e6-validator` |
| E7. Production polish | `feat/nornikel-e7-db-ops-docs` | `feat/nornikel-e7-bml-runbooks` | `feat/nornikel-e7-fe-polish` | `feat/nornikel-e7-validator` |

## 5. E0. Baseline и freeze

Цель: зафиксировать реальное состояние, не начать исправления поверх спорных контрактов и разнести gaps по владельцам.

### Databases

Ветка: `feat/nornikel-e0-db-baseline`.

Сделать:

- Проверить migrations, seed/reset scripts, PostgreSQL schemas, MinIO buckets, Neo4j labels/indexes, Qdrant collections.
- Зафиксировать, какие таблицы/коллекции нужны для review, interests, notifications, export jobs, document deletion, audit pagination.
- Найти existing migrations, которые уже закрывают parts of `UserInterest`, `ExportJob`, audit, review state.
- Не добавлять новые migrations на этом этапе, если можно ограничиться аудитом.

Выход:

- DB baseline report в `docs/agent_context/`.
- Список storage gaps по каждой фиче: review, interests, notifications, delete, export, admin save, audit, source spans.

### Backend/ML

Ветка: `feat/nornikel-e0-bml-contract-audit`.

Сделать:

- Проверить `shared/contracts`, gateway/orchestrator APIs, model offline endpoints, retrieval/source/export/notification endpoints.
- Зафиксировать, какие DTO уже есть и каких не хватает: `ReviewDecisionPayload`, interests payloads, notification match payload, delete result, export job payload, eval report payload, source payload with highlight fields.
- Проверить official questions, `eval/gold_questions.json`, `eval/pinned_demo_artifact.json`, `demo/official_questions.md`.
- Пометить все live model gates как `blocked_by_policy`.
- Определить список задач, где нужен весь dataset. Владельцем назначить `Backend/ML`.

Выход:

- Contract/API/eval baseline report.
- Dataset access checklist для E2: где лежит полный corpus, как reviewить expected `SourceSpan`, какие файлы нельзя коммитить.

### Frontend

Ветка: `feat/nornikel-e0-fe-ui-audit`.

Сделать:

- Проверить routes, stores, API clients, mock/live boundaries, RoleSwitcher, source resolver, NotificationBell, ExportPanel, AdminPage, ProfilePage, EvaluationDashboard, UploadPage, SearchPage, GraphPage, Lab/GapConflict views.
- Найти все direct imports из `api/mock/` в production components.
- Зафиксировать missing pages/components: `ReviewConsole`, dictionary version manager, ingestion queue, eval report dashboard, source highlight states.
- Не удалять mock layer на E0.

Выход:

- UI audit report с точными файлами.
- Список frontend gaps, разбитый по этапам E1-E7.

### Validator gate

Ветка: `feat/nornikel-e0-validator`.

Проверить:

- Все три baseline report merged в `dev`.
- Нет live model claims.
- Есть единая таблица gaps и owners.
- Нет изменений production behavior без необходимости.

Минимальные проверки:

- `git diff --check`.
- Проверка markdown links/paths вручную через `rg`.

## 6. E1. Persistent foundations

Цель: заложить storage/API/UI основы для фич с худшей связкой: interests, notifications, delete, admin save, export, review.

### Databases

Ветка: `feat/nornikel-e1-db-core-storage`.

Сделать:

- Добавить или довести migrations для:
  - `review_decisions`;
  - user interests and extracted entities, если их нет в нужной форме;
  - notification references: `reference_id`, `reference_type`, `type`, `status`, `read_at`;
  - export jobs/artifacts, если выбран async export path;
  - audit cursor fields/indexes;
  - document deletion state/tombstone, если нужен safe cascade.
- Добавить индексы под filters: user/status/date/type, document_id, source_span_id, export job owner.
- Обеспечить idempotent seed/reset для новых таблиц.
- Не менять ontology и security без явного решения.

Выход:

- Alembic migrations.
- DB tests или migration smoke.
- Документ с ownership: какая таблица принадлежит какому сервису.

### Backend/ML

Ветка: `feat/nornikel-e1-bml-core-api-contracts`.

Сделать:

- Добавить минимальные backward-compatible contracts для:
  - interests `GET/PUT`;
  - notification list/mark/read/match result;
  - delete document result;
  - export request/job/result;
  - review queue/decision;
  - eval report summary;
  - source payload highlight fields.
- Добавить gateway/orchestrator route skeletons только там, где есть storage foundation.
- Для model interactions использовать только offline/deterministic/mock path.
- Зафиксировать, что live quality не проверяется.

Выход:

- Shared contract changes с tests.
- OpenAPI/gateway contract tests по fixture.
- No-live model policy в соответствующем agent context report.

### Frontend

Ветка: `feat/nornikel-e1-fe-api-foundation`.

Сделать:

- Добавить API clients/helpers:
  - `api/interests`;
  - `api/notifications`;
  - `api/review`;
  - `api/export`;
  - `api/admin` PATCH helpers;
  - delete document helper with proper error mapping.
- Подготовить common async states: loading, optimistic update, rollback, toast/error.
- Подготовить feature flags для server export, live notifications, review console, source live mode.
- Не подключать UI flows, если backend contracts ещё не merged.

Выход:

- API abstraction layer без крупных UI изменений.
- Unit tests для clients/mappers, если есть соответствующий слой.

### Validator gate

Проверить:

- Migrations применяются на clean DB.
- Shared contracts backward-compatible.
- UI clients не ломают mock mode.
- `git diff --check`.
- Релевантные backend contract tests and UI tests.

## 7. E2. Dataset, sources, review

Цель: подготовить полный offline dataset/gold layer, source correctness и review workflow foundation.

### Databases

Ветка: `feat/nornikel-e2-db-review-source-data`.

Сделать:

- Реализовать review queue storage поверх Neo4j candidates + PG decision state.
- Подготовить source span lookup indexes and payload fields: `highlight_start`, `highlight_end`, `page`, `table_row_id`.
- Добавить cascade-safe metadata для document deletion: source spans, claims, vectors, graph nodes, MinIO object refs.
- Добавить fixtures для review/source/delete без live models.
- Не менять graph ontology без отдельного решения.

Выход:

- Storage/API-ready слой для review/source/delete.
- DB fixtures для E2/E3.

### Backend/ML

Ветка: `feat/nornikel-e2-bml-gold-dataset`.

Сделать:

- Получить доступ ко всему dataset и собрать расширенный offline gold dataset.
- Для 4 official questions выбрать reviewed expected `SourceSpan` candidates:
  - `official-001`: salts, Ca/Mg/Na 200-300 mg/l, dry residue <= 1000 mg/dm3;
  - `official-002`: catholyte circulation, nickel electrowinning, optimal flow speed;
  - `official-003`: Au/Ag/PGM distribution, matte/slag, last 5 years;
  - `official-004`: mine water injection, Russia/foreign practice, economics.
- Добавить gap/conflict/review fixtures без обращения к live models.
- Добавить reason codes for missing/weak/unsupported evidence.
- Обновить pinned offline artifact only if it contains no generated live answers.

Выход:

- Расширенный `eval/gold_questions.json` или отдельный reviewed fixture file.
- Dataset report: что покрыто, что candidate, что blocked_by_data.
- Offline tests that validate schema and expected source ids presence.

### Frontend

Ветка: `feat/nornikel-e2-fe-review-source-ui`.

Сделать:

- Создать `ReviewConsolePage` и route `/review` behind feature flag.
- Компоненты:
  - `CandidateTable`;
  - `ConflictDiffView`;
  - `ReviewActionBar`;
  - filters by type/status/date;
  - pending/approved/rejected/deferred states.
- Source viewer:
  - scroll/highlight by offsets;
  - locked source state for 403;
  - table row/cell source rendering.
- Не подключать destructive review actions, если backend endpoint ещё не merged.

Выход:

- Review/source UI foundation.
- Mock fixtures and tests for states.

### Validator gate

Проверить:

- Gold dataset не содержит hardcoded answer text from live models.
- Expected `SourceSpan` ids есть для official questions или gaps явно marked `blocked_by_data`.
- Source viewer states covered.
- Review console открывается только через expected flag/route.

## 8. E3. User workflows

Цель: закрыть реальные пользовательские workflows с худшей связкой: interests, notifications trigger, delete document, admin save, review actions.

### Databases

Ветка: `feat/nornikel-e3-db-workflow-state`.

Сделать:

- Довести persistence для:
  - interests profile and extracted entities;
  - notification match results;
  - review decisions;
  - document deletion tombstones/cascade status;
  - admin changes audit records.
- Добавить rollback-safe transaction boundaries для delete/review/admin operations.
- Добавить cursor pagination для audit/notification lists, если storage готов.

Выход:

- Integration storage tests.
- Seed data for workflow e2e.

### Backend/ML

Ветка: `feat/nornikel-e3-bml-workflow-wiring`.

Сделать:

- Реализовать:
  - `GET /api/interests`;
  - `PUT /api/interests`;
  - gateway proxy to offline/deterministic model extract;
  - `GET /api/notifications?since=`;
  - mark read / mark all read;
  - ingestion hook for `ingestion_complete`;
  - offline notification matching without live models;
  - `DELETE /api/documents/{document_id}`;
  - `POST /api/review/queue`;
  - `POST /api/review/decisions`;
  - admin PATCH response consistency and audit.
- Delete cascade: MinIO delete, knowledge purge, retrieval deindex, PG cleanup, audit.
- Review approve/reject must not promote unsupported claims to confirmed without source.

Выход:

- Backend integration tests for interests, notifications, delete, admin save, review.
- E2E-ready APIs.

### Frontend

Ветка: `feat/nornikel-e3-fe-workflows`.

Сделать:

- ProfilePage:
  - load interests from API;
  - save to API;
  - show extracted entities from response;
  - keep localStorage only as explicit mock fallback.
- NotificationBell:
  - incremental poll or stream fallback;
  - click opens source/document by `reference_id` and `reference_type`;
  - toast/badge for new unread notifications;
  - i18n titles by `type`, not backend hardcoded text.
- Upload/Admin:
  - document delete with optimistic remove and rollback;
  - 403/404 specific messages;
  - admin save per row or save all with diff.
- ReviewConsole:
  - wire queue and decision actions with rollback.

Выход:

- Working user workflows in real backend mode.
- UI tests for critical flows.

### Validator gate

Проверить:

- E2E smoke: interests save, notification list, delete document error handling, admin save persistence, review decision.
- No direct live model calls.
- No production-only reliance on seed/demo notifications.

## 9. E4. Evidence, RBAC, search

Цель: закрыть evidence-first correctness, source/live boundary, RBAC runtime, dictionaries, upload stages and search filters.

### Databases

Ветка: `feat/nornikel-e4-db-evidence-access`.

Сделать:

- Проверить and index access policy fields for documents/source spans/vectors/claims.
- Добавить fixtures:
  - public document;
  - internal document;
  - confidential document;
  - external partner user.
- Убедиться, что Qdrant payload supports numeric/geo/time filters, dictionary version, source type, table rows.
- Подготовить audit fields for access denied/source opened/search/export.

Выход:

- Access fixture pack.
- DB/retrieval storage smoke tests.

### Backend/ML

Ветка: `feat/nornikel-e4-bml-evidence-retrieval`.

Сделать:

- Проверить and complete:
  - source resolver live path;
  - `SourcePayload` highlight fields;
  - 403 with code `access_denied`;
  - retrieval filters for geo/numeric/time;
  - search pagination;
  - dictionary active preflight;
  - upload task stages and parse warnings;
  - conflicts in `QueryRunPayload`;
  - same conflict ids in chat and lab views.
- Ensure access filtering happens before synthesis and before export.
- For official questions run only offline QueryIR/retrieval/source checks.

Выход:

- Tests for access leak, source resolve, search filters, dictionary preflight, upload stages.
- Offline retrieval quality report with channel contribution: vector, lexical, table, graph, numeric, geo, time.

### Frontend

Ветка: `feat/nornikel-e4-fe-evidence-access`.

Сделать:

- Убрать direct `api/mock/` imports из production components; оставить mock только behind resolver/test boundary.
- Source refs через `useSourceResolver` / live adapter.
- RoleSwitcher только dev + mock; route guards by real auth role.
- SourcePanel locked state for 403.
- Search filters: geo, year range, numeric, pagination/infinite scroll.
- Admin dictionaries tab: list versions, active badge, activate button.
- Upload stepper from `task.stages[]`, parse warnings.
- Gap/Conflict row click opens sources; resolve/defer actions only if review API ready.

Выход:

- Production mode no longer leaks mock source catalog.
- UI supports access/search/dictionary/upload evidence states.

### Validator gate

Проверить:

- `VITE_USE_MOCK=false` smoke.
- external partner source/search/export access filtering.
- grep rule: no `api/mock` in production components except tests/dev boundary.
- dictionary upload/activate/query warning flow.

## 10. E5. Export, notifications, audit

Цель: сделать export/notification/audit честными product features, а не UI/service stubs.

### Databases

Ветка: `feat/nornikel-e5-db-product-events`.

Сделать:

- Finalize export jobs/artifacts storage or document orchestrator-owned export storage.
- Add MinIO bucket metadata for exports if backend chooses stored artifacts.
- Add audit cursor pagination and export CSV storage/query support.
- Add notification event indexes for incremental polling.
- Add retention/cleanup notes for export artifacts and notifications.

Выход:

- DB support for export/audit/notification product flows.
- Migration and storage tests.

### Backend/ML

Ветка: `feat/nornikel-e5-bml-export-notifications`.

Сделать:

- Выбрать and document authoritative export boundary:
  - short-term: orchestrator-owned export; or
  - full: `services/export` with jobs and MinIO artifacts.
- Server export:
  - Markdown;
  - JSON;
  - JSON-LD status explicit;
  - PDF status explicit;
  - evidence table;
  - source links;
  - graph;
  - gaps/conflicts;
  - confidence/warnings;
  - `QueryIR`;
  - `retrieval_trace`;
  - user role/access scope;
  - audit event.
- Notifications:
  - real event source from ingestion/review/query conflicts;
  - no seed-only production behavior;
  - `GET /notifications?since=`;
  - controlled no-live matching.
- Audit:
  - `query_created`;
  - `answer_generated`;
  - `source_opened`;
  - `document_uploaded`;
  - `document_deleted`;
  - `document_exported`;
  - `review_decision`;
  - `access_denied`;
  - `admin_setting_changed`.

Выход:

- Export/notification/audit integration tests.
- Boundary decision documented in `docs/agent_context/`.

### Frontend

Ветка: `feat/nornikel-e5-fe-export-notifications`.

Сделать:

- ExportPanel uses `POST /api/export` in production.
- Add JSON-LD option if backend exposes it; otherwise show unavailable state, not fake export.
- Poll export job or handle direct download URL.
- Client-side export only offline fallback behind flag.
- Notification center:
  - refresh/poll;
  - read/unread;
  - click target;
  - empty/error states.
- Audit page:
  - filters;
  - pagination;
  - CSV export;
  - event drill-down to run/source/document.
- EvaluationDashboard reads backend/pinned offline report, not hardcoded analytics.

Выход:

- Production export and notification UI use real backend.
- Audit/eval dashboards show real statuses.

### Validator gate

Проверить:

- Export JSON contains evidence and no restricted sources for external partner.
- Notification appears after offline-triggered event, not seed-only.
- Audit events visible with filters/pagination.
- PDF/JSON-LD are either implemented or honestly marked unavailable/backlog.

## 11. E6. Offline quality and CI

Цель: собрать no-live quality gate, E2E 1-10, clean seed/reset, regression reports.

### Databases

Ветка: `feat/nornikel-e6-db-seed-reliability`.

Сделать:

- Clean reset/reseed gate:
  - users;
  - dictionaries;
  - demo documents;
  - reviewed fixtures;
  - graph;
  - Qdrant;
  - MinIO;
  - notification/export/audit seed where appropriate.
- Add counts report: documents, tables, `SourceSpan`, claims, vectors, graph nodes, dictionary versions.
- Verify backup/restore scope for PostgreSQL, Neo4j, Qdrant, MinIO.

Выход:

- Repeatable seed report.
- Backup/restore gap report.

### Backend/ML

Ветка: `feat/nornikel-e6-bml-offline-quality`.

Сделать:

- No-live official scenario suite:
  - QueryIR constraints;
  - retrieval evidence;
  - expected `SourceSpan` presence;
  - access filtering;
  - source resolve;
  - export completeness;
  - audit events.
- Run or fix offline quality gates:
  - `eval/demo_quality_gate.py`;
  - regression suites that do not call live models;
  - E2E official questions smoke if it can run offline.
- Create final offline quality report:
  - pass/warn/fail;
  - `blocked_by_policy` for live answer quality and latency;
  - `blocked_by_data` if reviewed source expectations still incomplete.

Выход:

- Offline readiness report.
- CI/e2e jobs or Makefile targets for no-live gates.

### Frontend

Ветка: `feat/nornikel-e6-fe-e2e-hardening`.

Сделать:

- Playwright/Cypress or existing e2e coverage for:
  - interests save;
  - upload and task stages;
  - notification click to source;
  - source viewer highlight/403;
  - export;
  - admin save;
  - review decision;
  - search filters;
  - dictionary activate;
  - audit filtering.
- UI production build with `VITE_USE_MOCK=false`.
- Disable simulated lifecycle when real backend mode is active.
- Streaming flags: default prod behavior documented; fallback to non-streaming if stream unavailable.

Выход:

- E2E coverage for scenarios 1-10 where backend supports them.
- UI no-live demo checklist.

### Validator gate

Проверить:

- `ruff check shared services scripts tests`.
- `$env:COVERAGE='1'; $env:COVERAGE_FAIL_UNDER='60'; python scripts/run_tests.py` if feasible.
- `cd ui; npm ci; npm test; npm run build; npm run lint`.
- No-live e2e target.
- `python eval/demo_quality_gate.py` without live models.
- Any skipped command has explicit reason.

## 12. E7. Production polish

Цель: убрать demo-only хвосты, синхронизировать docs/runbooks и подготовить финальный handoff.

### Databases

Ветка: `feat/nornikel-e7-db-ops-docs`.

Сделать:

- Document database ownership, migrations, backup/restore, seed/reset, retention.
- Add runbook for common DB failures:
  - migration fail;
  - Qdrant empty;
  - Neo4j unavailable;
  - MinIO missing object;
  - stale dictionary.
- Verify cleanup policies for deleted docs and export artifacts.

Выход:

- DB/ops docs in `docs/agent_context/`.
- No structure drift.

### Backend/ML

Ветка: `feat/nornikel-e7-bml-runbooks`.

Сделать:

- Operator runbook:
  - clean setup;
  - seed;
  - health;
  - offline eval;
  - no-live restrictions;
  - where reports live;
  - how to interpret blocked_by_policy.
- Production readiness summary:
  - P0 closed/open;
  - P1 risks;
  - export/notification boundary;
  - live model final step explicitly deferred.
- Coordinate with External Orchestrator Refactor Owner only by documenting dependency, not by refactoring `service.py`.

Выход:

- Runbook and final readiness report.

### Frontend

Ветка: `feat/nornikel-e7-fe-polish`.

Сделать:

- Empty/error/degraded states across pages.
- Global service health indicator from `/health/all` or current health endpoint.
- PWA manifest, OG meta, logo alt for `НорСинтез`.
- Mobile/desktop smoke polish:
  - no overlapping text;
  - no layout shifts in chat/source/export/review;
  - warnings/gaps/conflicts visible.
- Remove user-facing fake/demo labels unless explicitly dev-only.

Выход:

- UI production polish.
- Final smoke screenshots or checklist if visual tests are unavailable.

### Validator gate

Проверить:

- Docs updated only where needed; if repo structure changed, update `docs/agent_context/project_structure.md`.
- No `README.md` changes unless explicitly requested.
- Final no-live readiness status is honest.
- Live model tasks are not included except as final deferred section.

## 13. Known feature coverage mapping

Этот план закрывает все пункты исходного gap-analysis:

| Gap | Где закрывается |
|---|---|
| Review Console | E1 contracts/storage, E2 UI/source, E3 actions, E5 audit |
| Профиль интересов | E1 API/storage, E3 backend/frontend flow |
| E2E interests → upload → notification | E3 workflow, E5 notifications, E6 e2e |
| Удаление документа | E1 storage/contracts, E2 cascade metadata, E3 delete API/UI |
| Export API | E1 contracts, E5 authoritative export, E6 quality |
| Admin save | E1 API client/contracts, E3 backend/UI/audit |
| Eval в UI | E5 dashboard, E6 offline quality |
| Streaming query UX | E4/E6 UI and backend fallback; live model latency deferred |
| Уведомления | E3 real flow, E5 product boundary |
| Source viewer/mock catalog | E2 source UI, E4 mock cleanup/access |
| Gap/Conflict view | E2 review UI, E4 conflicts in payload/source links |
| RBAC runtime | E4 access fixture/backend/UI |
| Dictionaries | E4 active dictionary UI/backend preflight |
| Upload | E4 task stages, E6 seed/e2e |
| Chat + scientific answer | E4 evidence/retrieval, E6 official offline gates |
| Search | E4 filters/pagination |
| Audit | E5 audit coverage/pagination/export |
| Strategic/Lab/Evaluation dashboards | E5 dashboards, E7 polish |
| Knowledge graph | E2 review/source, E4 conflict ids/graph evidence, E7 polish |
| Auth UI | E4 RoleSwitcher isolation, E7 polish |
| UI shell | E7 health/error states |
| Branding | E7 PWA/OG/alt/user-facing naming |

## 14. Minimal quality gate for every technical card

- `git diff --check`.
- `git status -sb` before commit.
- Relevant unit/integration/UI tests for touched area.
- If migrations changed: migration apply/rollback or documented migration smoke.
- If contracts changed: contract/schema tests.
- If UI changed: `npm test` or targeted test, plus `npm run build` when feasible.
- If tests are skipped: final answer must state exact reason.
- Commit one Russian line: `feat: сделано то-то`.
- Push only own `feat/*` branch. After rebase use `--force-with-lease` only for own feature branch.

## 15. Final deferred work outside this plan

Не включать в этапы E0-E7:

- live model eval;
- Yandex live smoke;
- live latency p95 claims;
- generated final answer quality from external models;
- large orchestrator god object refactor in `services/orchestrator/app/service/service.py`.

После E7 и отдельного разрешения можно создать новый финальный live-model plan:

- run live eval;
- compare offline vs live reports;
- update `eval/reports/`;
- mark live quality gates pass/warn/fail;
- only then claim live answer quality.
