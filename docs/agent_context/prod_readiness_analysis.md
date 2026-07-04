# Production-readiness analysis plan

**Дата:** 2026-07-04  
**Цель:** понять, чего проекту не хватает для полной сборки, стабильного запуска и прохождения всех сценариев.  
**Планка:** production-readiness, не только demo.  
**Ограничение:** live-запуск внешних models запрещен организаторами; все выводы по live model quality получают статус `blocked_by_policy`.

Этот документ задает план анализа. Он не заменяет `implementation_quality_report.md`, `audit_report.md`, `ml_mvp_status.md` и `top1_*`, а собирает их в один проверяемый контур.

## 1. Как писать отчет

Писать простым русским языком. Technical terms, metrics, DTO, models, endpoint names и service names оставлять на English: `SourceSpan`, `QueryIR`, `EvidenceBundle`, `RBAC`, `CI`, `e2e`, `hybrid retrieval`, `latency_ms_p95`.

Каждый вывод оформлять одинаково:

| Поле | Что писать |
|---|---|
| `What we checked` | Что именно проверили |
| `Current state` | Что сейчас есть в проекте |
| `Gap` | Чего не хватает |
| `Impact` | Чем это грозит продукту, demo или production |
| `Evidence` | Файл, тест, команда, endpoint или документ |
| `Next action` | Что нужно сделать дальше |

Статусы только такие:

| Status | Meaning |
|---|---|
| `pass` | Проверено и работает |
| `warn` | Работает частично или есть риск |
| `fail` | Проверено и не работает |
| `blocked` | Нельзя проверить без внешнего условия |
| `blocked_by_policy` | Нельзя проверять из-за запрета на live models |

## 2. Baseline

Первый шаг анализа фиксирует, от какой версии проекта делаются выводы.

Проверить:

- текущую ветку, commit SHA и `git status`;
- совпадение локального `dev` с `origin/dev`;
- список сервисов в `docker-compose.yml`;
- команды в `Makefile`;
- CI gates в `.github/workflows/ci.yml`;
- `.env.example` и наличие всех обязательных переменных;
- текущие отчеты: `mvp.md`, `contracts.md`, `implementation_quality_report.md`, `audit_report.md`, `ml_mvp_status.md`, `query_pipeline.md`, `top1_*`.

Выход baseline:

- список того, что уже заявлено как `pass`;
- список open gaps;
- список зон, где статус должен быть `blocked` или `blocked_by_policy`;
- список документов, которые расходятся с кодом.

## 3. Scenario matrix

Нужно построить matrix всех сценариев. Цель не в том, чтобы просто перечислить страницы UI, а в том, чтобы понять: может ли реальный пользователь пройти задачу от начала до конца.

Для каждого scenario указать:

- `User goal`;
- `UI entrypoint`;
- `API entrypoint`;
- `Required data`;
- `Expected result`;
- `Access behavior`;
- `Audit event`;
- `Current tests`;
- `Status`;
- `Gap`;
- `Next action`.

Обязательные happy-path scenarios:

| Scenario | Что должно быть доказано |
|---|---|
| Upload files / ZIP | Пользователь загружает corpus, получает `task_id`, видит статус |
| Ingestion report | Видны documents, tables, `SourceSpan`, entities, claims, warnings |
| Dictionary package | Можно загрузить и активировать `dictionary-package.v1` |
| Official question 1 | Вода, salts, numeric ranges, sources, limitations |
| Official question 2 | Catholyte circulation, aliases, equipment, flow speed |
| Official question 3 | Au/Ag/PGM, matte/slag, last 5 years, publications |
| Official question 4 | Mine water injection, Russia/foreign geography, economics |
| Source viewer | Source link открывает правильный `SourceSpan` с учетом access |
| Local graph | Query run показывает compact `GraphSubgraph` |
| Search | Search page/API возвращает evidence без synthesis |
| Export Markdown/JSON | Export содержит answer, evidence, sources, graph, warnings |
| Notification | User interests и notifications работают через real backend boundary |
| Audit log | Query, source open, export, upload пишутся в audit |
| RBAC | Admin, researcher, analyst, manager, external partner видят только свое |
| Reset/reseed | Stack можно сбросить и поднять без ручных правок |

Обязательные failure/degraded scenarios:

| Scenario | Что должно быть доказано |
|---|---|
| Empty evidence | Ответ не выдумывает facts, показывает degraded state |
| Access denied | Закрытый source не попадает в synthesis и source viewer |
| Parser failure | Ошибка файла не ломает весь ingestion batch |
| Missing active dictionary | Query/ingestion дают понятную ошибку или preflight |
| Empty Qdrant | Query возвращает controlled degraded response |
| Neo4j unavailable | Graph fallback не ломает весь query path, если это допустимо |
| Model timeout | Timeout дает controlled warning/error |
| Export access changed | Export revalidates source access |
| Disabled stream | `/query/stream` честно возвращает disabled state |

## 4. Subsystem audit

### Product and domain

Проверить, что продукт выглядит как evidence-first R&D knowledge platform, а не как chat over documents.

Проверить:

- покрытие 4 official questions;
- наличие gap/conflict scenarios;
- наличие domain terms, units, geography, time filters;
- понятность ответов для researcher, manager и external partner;
- нет ли hardcoded demo answers.

Типовые gaps, которые уже нужно проверить особенно внимательно:

- official questions имеют reviewed `expected_source_span_ids`; offline gate падает, если любой `official-*` набор пуст;
- live answer quality не подтверждена из-за запрета live models;
- gap/conflict behavior требует reviewed expectations.

### Data and ingestion

Проверить:

- `PDF`, `DOCX`, `PPTX`, `DOC`, `ZIP`;
- сохранение original files в MinIO;
- создание `NormalizedDocument`, `TableBlock`, `SourceSpan`;
- стабильность `SourceSpan.id`;
- extraction of numbers, units, aliases, geo, time;
- dictionary pinning;
- replayability: reset + seed дает тот же corpus state.

Результат должен ответить на вопрос: можно ли без ручных правок подготовить corpus для всех scenario tests.

### Knowledge, retrieval and query

Проверить:

- запись claims в Neo4j;
- индексацию chunks/table rows в Qdrant;
- `QueryIR` по official questions;
- `hybrid retrieval`: vector, graph, table, lexical, numeric, geo, time;
- `fusion`;
- `retrieval_trace`;
- verified/candidate/unsupported separation;
- access filtering before synthesis.

Особенно проверить текущие known gaps:

- graph/table/lexical fusion;
- geo/numeric constraints в Qdrant search;
- retrieval source identity drift из E5;
- `has_conflicts` / `conflicts` population;
- legacy indexing endpoint.

### Model and eval

Live model calls не запускать.

Проверить offline:

- deterministic fallback behavior;
- schema validation;
- `SourceSpan` requirement для confirmed facts;
- `unsupported_claim_rate` calculation в reports;
- `eval/pinned_demo_artifact.json`;
- `eval/regression_suites.json`;
- `eval/demo_quality_gate.py`.

Live quality status:

- `Current state`: offline gates exist;
- `Gap`: no permitted live report;
- `Status`: `blocked_by_policy`;
- `Next action`: после разрешения models выполнить live eval отдельно и сохранить только reports в `eval/reports/`.

### Security, RBAC and audit

Проверить:

- JWT/JWKS validation;
- roles: admin, researcher, analyst, manager, external partner;
- access before synthesis;
- source resolve access;
- export access revalidation;
- audit events: `query_created`, `answer_generated`, `source_opened`, `document_uploaded`, `document_exported`, `access_denied`, `admin_setting_changed`;
- RoleSwitcher production risk;
- rate limiting;
- secrets and default credentials.

Особенно важно: если closed document попал в model synthesis, это `P0 fail`.

### UI

Проверить:

- real vs mock mode;
- source resolver boundary;
- chat lifecycle;
- rendering of warnings, gaps, conflicts, degraded state;
- source viewer;
- export panel;
- notification UX;
- admin/audit pages;
- mobile and desktop layouts;
- отсутствие layout shifts и overlapping text.

Known risk:

- mock source catalog still affects UX boundaries;
- RoleSwitcher can override backend role if not isolated;
- streaming is feature-flagged and disabled by default.

### Export and notification

Проверить как production boundary, а не как demo shortcut.

Export:

- current HTTP export service;
- orchestrator export path;
- Markdown/JSON content;
- JSON-LD status;
- file storage;
- access revalidation;
- audit event.

Notification:

- current HTTP notification service;
- user interests storage;
- model `/notifications/match`;
- UI notification bell;
- trigger on new evidence/conflicts;
- audit or user-visible history.

Если service существует только с `/health` и `/ready`, это фиксировать как real gap, даже если часть logic есть в другом сервисе.

### Ops, CI and observability

Проверить:

- `docker compose up -d --build --wait`;
- migrations on clean volumes;
- `make reset-demo`;
- healthchecks;
- Prometheus `/metrics`;
- Grafana dashboards;
- logs with `X-Request-ID`;
- backup/restore scripts;
- CI backend, UI, coverage, e2e;
- performance smoke;
- documented runbook.

Production-readiness не может быть `pass`, если clean setup нельзя повторить без ручных правок.

## 5. Offline verification commands

Разрешенные проверки:

```powershell
python scripts/audit_repo.py
ruff check shared services scripts tests
$env:COVERAGE='1'; $env:COVERAGE_FAIL_UNDER='60'; python scripts/run_tests.py
```

```powershell
Set-Location ui
npm ci
npm test
npm run build
npm run lint
```

```powershell
Copy-Item .env.example .env
python scripts/generate_auth_keys.py
docker compose up -d --build --wait
docker compose exec -T auth_audit auth-seed-users
python scripts/seed_demo.py
$env:RUN_E2E='1'; python -m pytest -q tests/e2e
python eval/demo_quality_gate.py
```

Запрещенные проверки до отдельного разрешения:

```powershell
$env:RUN_MODEL_TESTS='1'; python scripts/run_tests.py
make eval-yandex-live
make test-yandex-live
python scripts/yandex_live_smoke.py
python scripts/eval_yandex_live.py
```

Если команда случайно требует live model call, анализ должен остановить эту часть и поставить `blocked_by_policy`.

## 6. Production readiness gates

Общий статус `production-ready: pass` запрещен, если не закрыты эти gates:

| Gate | Минимальный pass |
|---|---|
| Clean build | Docker stack builds and starts from clean volumes |
| Reset/reseed | Demo corpus and dictionaries load without manual DB edits |
| API health | All services return `/health` and `/ready` |
| Unit/integration | Backend tests pass with coverage gate |
| UI | `npm test`, `npm run build`, `npm run lint` pass |
| E2E | Upload/query/source/graph/search/export/audit smoke pass |
| Official scenarios | 4 official questions have evidence-backed answers |
| Access | `access_leak_rate == 0.0` |
| Source | Source links resolve correct accessible `SourceSpan` |
| Export | Markdown/JSON export contains required evidence fields via orchestrator/gateway |
| Audit | Required audit events are persisted |
| Eval | Offline quality gate passes; live quality is not claimed |
| Performance | Offline/perf smoke has trace; live `latency_ms_p95` remains blocked without live run |
| Ops | Logs, metrics, backup/restore and runbook exist |

## 7. Gap register format

Каждый gap записывать так:

| Field | Example |
|---|---|
| `id` | `PRD-P0-001` |
| `priority` | `P0` |
| `area` | `retrieval` |
| `scenario` | `official-004 geo query` |
| `status` | `warn` |
| `evidence` | `docs/agent_context/ml_mvp_status.md` |
| `impact` | `Geo answer can be incomplete` |
| `dependency` | `none` or `sync-required` |
| `acceptance criteria` | `geo constraints applied before rerank` |
| `task card` | link/id from `prod_readiness_task_cards.md` |

Priority rules:

- `P0`: blocks production-ready or honest full scenario pass.
- `P1`: high trust, security, quality or operations risk.
- `P2`: maintainability, UX, scalability, polish.
- `P3`: optional improvement.

## 8. Expected top gaps to verify

Не считать этот список финальным. Это стартовые hypotheses, которые нужно подтвердить или опровергнуть evidence.

| Gap | Expected priority |
|---|---|
| Live model quality report is unavailable by policy | `P0 blocked_by_policy` |
| Export microservice is not wired as real service boundary | `P0/P1` |
| Notification microservice is not wired as real service boundary | `P1` |
| Hybrid retrieval is incomplete against target spec | `P0/P1` |
| Geo/numeric filters are not fully enforced in Qdrant search | `P0/P1` |
| Official questions lack reviewed expected `SourceSpan` ids | `P0/P1` |
| UI production path still has mock/live boundary risks | `P1` |
| RoleSwitcher and client-side role override are production risks | `P1` |
| Access filtering fixtures are narrow | `P1` |
| Orchestrator service is too large and hard to evolve | `P2` |
| Automatic retry is absent by design | `P2` unless SLA requires it |
| Rate limiting is missing | `P1/P2` depending on exposure |

## 9. Final report structure

Итоговый отчет должен иметь такую структуру:

1. Executive summary.
2. Readiness score by area.
3. Scenario matrix.
4. P0 blockers.
5. P1 risks.
6. Subsystem findings.
7. Offline verification results.
8. Blocked-by-policy live model section.
9. Gap register.
10. Link to task cards.

В summary нельзя писать “готово”, если есть open `P0` или `blocked_by_policy` по обязательному gate.
