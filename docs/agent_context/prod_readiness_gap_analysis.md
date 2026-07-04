# Анализ проекта против задания и ТЗ

**Дата:** 2026-07-04  
**Основа:** внешний файл `C:\Users\petro\Downloads\Научный клубок_ Аудит и Разработка Архитектуры (1).md` и репозиторное ТЗ `docs/nauchny_klubok_top1_tz.md`.  
**Цель:** простым языком зафиксировать, где мы уже закрываем задание, где сделали сильнее, чего еще не хватает и как это закрыть.

Technical terms оставлены на English: `SourceSpan`, `QueryIR`, `EvidenceBundle`, `RBAC`, `hybrid retrieval`, `CI`, `e2e`, `latency_ms_p95`, `JSON-LD`, `Qdrant`, `Neo4j`.

## Короткий вывод

Мы уже сделали больше, чем обычный MVP “чат по документам”. В проекте есть реальная microservice architecture, `shared/contracts`, ingestion, `SourceSpan`, `Neo4j`, `Qdrant`, `QueryIR`, `EvidenceBundle`, `RBAC`, audit, UI, eval tooling, Docker Compose, CI и top-1 документы.

Но по заданию и нашему ТЗ еще нельзя честно сказать “все закрыто”. Не потому что нет pipeline: pipeline как раз мощный и в коде уже реализован. Не хватает финального зафиксированного evidence report по всем сценариям на согласованном corpus и в разрешенном режиме запуска.

- official questions уже имеют real e2e gate через gateway/source/graph/search/export/audit и reviewed `expected_source_span_ids` в gold dataset;
- `hybrid retrieval` в коде реализован как dense + lexical + table + graph with `fusion`, planner trace, geo/numeric/time/source filters and access filtering; remaining work — доказать качество на official corpus and reports;
- export честно определён как MVP через orchestrator/gateway; `services/export` остаётся reserved boundary. Notification остаётся отдельным production feature gap;
- UI должен быть полностью production-safe без mock/source и role shortcuts в живом пути;
- live model quality сейчас нельзя проверять, потому что organizers запретили live model calls.

Итоговый статус: **инженерное ядро сильное, но production/top-1 readiness пока `warn`, а live answer quality — `blocked_by_policy`**.

## 1. Главная идея продукта

### Что требует задание

Задание говорит: это не должен быть просто chat over documents. Нужна доказуемая R&D knowledge map:

- answer;
- evidence table;
- links to sources;
- local graph;
- numeric parameters;
- geography;
- confidence;
- актуальность знания;
- conflicts;
- gaps;
- experts;
- recommendations.

### Что у нас есть

У нас уже есть основа именно knowledge platform:

- `NormalizedDocument`, `SourceSpan`, `TableBlock`;
- claims and evidence;
- `Neo4j` for graph;
- `Qdrant` for vector evidence;
- `QueryIR`;
- `EvidenceBundle`;
- answer synthesis;
- source links;
- local graph;
- warnings/gaps/conflicts pieces;
- UI pages for chat, graph, upload, search, admin/audit, dashboards;
- eval and quality reports.

### Где сделали круче базового ожидания

- Не ограничились одним backend: есть 9 services plus UI.
- Есть `shared/contracts`, то есть данные не плавают между сервисами как случайный JSON.
- Есть `auth_audit` с JWT/JWKS, а не простой auth stub.
- Есть CI with backend, UI and e2e.
- Есть pinned eval inputs и regression suites.
- Есть feature flags for top-1 query and stream.

### Чего не хватает

Нужно доказать, что вся эта архитектура работает именно на user scenarios, а не только существует в коде.

Ключевой gap: **нет финального отчета “official scenarios pass with evidence”**.

### Как закрыть

Сделать final readiness report:

1. Запустить clean stack.
2. Seed corpus and dictionaries.
3. Пройти 4 official questions.
4. Для каждого answer проверить sources, numbers, geography, warnings.
5. Сохранить report.
6. Если live models запрещены, пометить answer quality как `blocked_by_policy`, но все offline gates все равно прогнать.

## 2. MVP cutoff

### Что требует задание

MVP готов только если команда может пройти full end-to-end без ручных правок в базе и консоли.

Обязательный flow:

`upload -> parsing -> NormalizedDocument -> SourceSpan -> dictionaries -> entities -> numbers -> claims -> Neo4j -> Qdrant -> QueryIR -> hybrid retrieval -> verification -> answer in UI`.

### Что у нас есть

По актуальному коду в `dev`:

- stack поднимается через Docker Compose;
- ingestion pipeline есть;
- `SourceSpan` есть;
- claims пишутся в `Neo4j`;
- chunks/table rows пишутся в `Qdrant`;
- query path есть;
- UI показывает answer, evidence, sources, graph;
- RBAC/audit есть;
- export Markdown/JSON есть через orchestrator;
- CI/e2e есть.

Ключевые code evidence:

- `services/orchestrator/app/service/service.py` — полный ingestion and query pipeline, dictionary pinning, source/export access revalidation, audit events;
- `services/retrieval/app/api/query.py` — dense/lexical/table/graph retrieval, `fusion`, rerank, access filtering;
- `services/retrieval/app/qdrant_adapter.py` — Qdrant filters for access, source type, geo, numeric and time;
- `services/model/tests/test_model_v1.py` — QueryIR constraints, evidence layers, unsupported claims, conflicts, gaps, JSON-LD;
- `tests/e2e/test_official_questions_smoke.py` — real gateway e2e gate for official questions, source, graph, search, export and audit.

### Что сделано сильнее MVP

- Реальный `auth_audit`, а не auth stub.
- Реальные adapters to `Neo4j` and `Qdrant`.
- `model` service имеет 13 v1 endpoints.
- Есть top-1 staged plan and eval suites.
- Есть reliability tests for fallback, timeout and stream behavior.

### Чего не хватает

MVP pipeline по коду закрыт гораздо сильнее, чем описывали старые summary-docs. Без оговорок MVP/top-1 readiness пока не стоит считать закрытым по другой причине: нужно доказать качество на согласованных scenario gates.

- `hybrid retrieval` реализован в retrieval code, но нужен финальный report, что он дает нужное качество на official scenarios;
- в текущем `eval/gold_questions.json` official questions имеют заполненные reviewed `expected_source_span_ids`, а offline/e2e gates требуют non-empty наборы для strict run;
- final live eval report отсутствует из-за policy;
- `services/export` и notification service остаются не fully wired как отдельные boundaries; MVP export идёт через orchestrator/gateway.

### Как закрыть

Сделать MVP freeze gate:

| Gate | Что проверить |
|---|---|
| Clean run | `docker compose up -d --build --wait` на clean volumes |
| Seed | users, dictionaries, demo corpus |
| Query | 4 official questions |
| Evidence | каждое key statement has `SourceSpan` |
| Retrieval | dense + lexical + table + graph channels, `fusion`, numeric/geo/time/source filters, `retrieval_trace` |
| Access | external partner не видит closed evidence |
| Export | Markdown/JSON with evidence and no forbidden sources |
| Audit | query/source/export/upload events exist |

## 3. Official scenarios

### Что требует задание

Есть 4 official scenarios:

1. Desalination for concentrator water with sulfates/chlorides/Ca/Mg/Na 200-300 mg/l and dry residue <= 1000 mg/dm3.
2. Catholyte circulation for nickel electrowinning and optimal flow speed.
3. Au/Ag/PGM distribution between matte and slag during last 5 years.
4. Mine water injection into deep horizons in Russia and abroad with techno-economic metrics.

Top-1 scenarios:

5. Gap in knowledge.
6. Conflict or weak evidence.

### Что у нас есть

- `demo/official_questions.md`;
- `eval/gold_questions.json`;
- official questions `official-001` ... `official-004`;
- regression suites;
- answer completeness and quality metrics;
- demo quality gate;
- top-1 reports for eval and reliability.

### Где сделали круче

- Gold dataset содержит не только 4 official questions, но и corpus-derived regression questions.
- Есть suites: official, hybrid retrieval, access filtering, unsupported claims, answer completeness.
- Есть `eval/pinned_demo_artifact.json`, который защищает входы от случайного drift.

### Чего не хватает

Code-level e2e gate для official questions уже есть, reviewed `expected_source_span_ids` заполнены для строгого запуска.

Это значит:

- можно проверить, что answer вообще содержит evidence;
- можно проверить answer outline;
- можно проверить constraints;
- но нельзя строго сказать, что найден именно правильный source span.

Также не хватает live answer report, но это сейчас `blocked_by_policy`.

### Как закрыть

1. Вручную review demo corpus for each official question.
2. Для каждого official question expected source spans уже выбраны и закреплены.
3. Добавить их в `eval/gold_questions.json`.
4. Обновить pinned artifact через отдельный eval PR.
5. Прогонять official suite:
   - offline mode now;
   - live mode after organizer permission.

## 4. Evidence-first and SourceSpan

### Что требует задание

Ни одного confirmed fact без source and `SourceSpan`.

### Что у нас есть

- `SourceSpan` is shared contract;
- stable `SourceSpan.id`;
- `EvidenceItem.source_span`;
- `EvidenceBundle`;
- model service rejects confirmed artifacts without `SourceSpan`;
- UI shows evidence table and source links.

### Где сделали круче

Мы сделали `SourceSpan` не просто UI-ссылкой, а системным ID, который связывает ingestion, retrieval, graph, source viewer, export and tests.

### Чего не хватает

Нужно доказать в scenario tests:

- source link resolves correct span;
- inaccessible source не открывается;
- export не содержит закрытые sources;
- source ids в answer совпадают с indexed data;
- official questions have expected source spans.

Есть отдельный risk из E5: retrieval source identity drift. Его нужно либо закрыть, либо явно закрепить новый contract.

### Как закрыть

Добавить source regression gate:

- query returns answer with source span ids;
- each source span resolves through `/api/source/{source_span_id}`;
- external partner gets no forbidden source;
- export repeats same access checks;
- source viewer displays correct text/page/source type.

## 5. Hybrid retrieval

### Что требует задание

Поиск должен быть не только embeddings. Нужны:

- dense/vector search;
- graph search;
- table search;
- lexical search;
- aliases;
- numeric filters;
- geo filters;
- time filters;
- `fusion`;
- `reranking`;
- evidence verification.

### Что у нас есть

- `RetrievalPlan` классифицирует запросы как `semantic`, `numeric`, `geo`, `temporal`, `comparative`, `graph_centric`, `mixed`;
- planner выбирает profiles: `semantic`, `lexical`, `table`, `numeric`, `geo`, `time`, `graph`;
- `QdrantRetrievalStorageAdapter.build_filter` применяет access, source type, geo, numeric and time filters before results leave retrieval;
- `run_query` собирает dense, lexical, table and graph results;
- `fuse_channels` делает deterministic fusion and deduplicates `SourceSpan`;
- после fusion retrieval повторно проверяет access and resolves sources before rerank;
- model rerank получает только allowed evidence;
- `retrieval_trace` содержит channel counts, raw candidates, fused, accessible, reranked and planner dump;
- `build_points` индексирует table rows, lexical tokens, numeric min/max, units, geo bucket/country, published year and dictionary version.

Ключевые code evidence:

- `services/retrieval/app/retrieval_planner.py`;
- `services/retrieval/app/api/query.py`;
- `services/retrieval/app/qdrant_adapter.py`;
- `services/retrieval/tests/test_retrieval_planner.py`;
- `services/retrieval/tests/test_query.py`;
- `services/knowledge/adapters/graph_exact_search.py`;
- `services/knowledge/tests/test_graph_exact_search.py`.

### Где сделали круче

- Есть отдельный retrieval service.
- Есть `retrieval_trace`.
- Есть tests for planner and reliability.
- Есть graph exact search path behind top-1 flow.
- Есть RRF-like channel fusion, а не просто vector search.
- Access filtering повторяется до rerank and source resolve.

### Чего не хватает

Не хватает не реализации, а финальной доказательной обвязки:

- на official corpus нужен report, что selected channels реально помогают official questions;
- official reviewed expected source spans уже есть; нужен seeded report, чтобы измерить recall, not just static presence;
- для larger corpus нужен latency/quality report;
- для graph/table/lexical channels нужен понятный dashboard/report, где видно contribution каждого channel;
- time filter для official-003 нужно подтвердить на corpus with publication years.

### Как закрыть

Сделать retrieval quality report:

| Channel | Нужно доказать |
|---|---|
| vector | points returned from `Qdrant` |
| graph | graph evidence merged into `EvidenceBundle` |
| table | table rows can be retrieved as evidence |
| lexical | exact/domain terms influence ranking |
| numeric | ranges and units enforced |
| geo | Russia/foreign/practice country enforced |
| time | last 5 years enforced |
| fusion | trace shows final merged ranking |

Это не новая реализация с нуля. Это проверка уже реализованного code path на agreed corpus.

## 6. Geography

### Что требует задание

Geography — это не только country of publication. Нужно различать:

- country of practice;
- region/object;
- organization country;
- jurisdiction;
- experiment location;
- domestic vs foreign practice.

### Что у нас есть

- `GeoContext`;
- dictionaries for geographies;
- geo constraints in `QueryIR`;
- official-004 tags and expected geo constraints;
- gap suggestions can reason about geo coverage.
- retrieval code applies geo filters through `geo_bucket` and `geo_country`.

### Где сделали круче

Есть словари and dictionary pinning, то есть geography can become managed data, not hardcoded code.

### Чего не хватает

Geo enforcement в retrieval code есть: Qdrant filter смотрит `geo_bucket` and `geo_country`, а planner выбирает `geo` profile. Остался gap не в кодовой способности, а в доказательстве качества на official-004 and reviewed corpus.

### Как закрыть

1. Add geo fixture with Russia and foreign practice.
2. Проверить `QueryIR.geo_filter` and `filters.geo_constraints`.
3. Проверить Qdrant payload filter and `retrieval_trace`.
4. Проверить answer table has domestic/foreign separation.
5. Проверить warning if geo evidence is incomplete.

## 7. Numbers, units and intervals

### Что требует задание

Система должна понимать numeric constraints:

- concentration;
- temperature;
- speed;
- productivity;
- economics;
- date intervals;
- unit conversions and tolerance.

### Что у нас есть

- `Quantity`;
- numeric constraints in `QueryIR`;
- units dictionaries;
- extraction of numbers and units;
- eval expected numeric constraints;
- `Numeric Correctness` metric.
- retrieval code applies unit and numeric range filters through `units`, `numeric_min`, `numeric_max`.

### Где сделали круче

Есть normalized contracts and eval metrics for numbers, not only plain text parsing.

### Чего не хватает

Numeric enforcement в retrieval code есть: Qdrant filter uses `units`, `numeric_min`, `numeric_max`. Самый важный remaining gap — подтвердить на official-001 with 200-300 mg/l and <=1000 mg/dm3, что нужные evidence are found and irrelevant ranges do not dominate.

### Как закрыть

1. Build numeric fixture for official-001.
2. Проверить QueryIR extraction.
3. Проверить Qdrant payload numeric fields and filter.
4. Проверить retrieval excludes irrelevant ranges in report.
5. Проверить answer table shows values and units.
6. Проверить no unit mismatch without warning.

## 8. Claim-based knowledge and fact versioning

### Что требует задание

Graph must store claims, observations, measurements, provenance, conditions, dates, confidence, versions and history.

### Что у нас есть

- claim-based graph path;
- claims in `Neo4j`;
- provenance with `SourceSpan`;
- conflicts/gaps endpoints;
- some versioning/data structures.

### Где сделали круче

Мы уже не храним “истину” как flat facts. Архитектура ближе к claim-based model.

### Чего не хватает

Top-1 checklist требует visible fact versioning or review console. У нас это не полностью productized:

- review console не является полноценным workflow;
- versioning facts не виден пользователю как clear scenario;
- E2E-9 "new source updates/conflicts old claim" не доказан.

### Как закрыть

Сделать minimal review/version scenario:

1. Add source A with claim.
2. Add source B with updated/conflicting claim.
3. Graph creates new version or conflict.
4. UI/API shows both claims and conditions.
5. Export includes conflict/gap context.

## 9. Security, RBAC and audit

### Что требует задание

Нужны roles, access levels, audit events and restrictions for external partners.

MVP roles:

- admin;
- researcher;
- external partner.

Top-1 roles can include:

- analyst;
- manager;
- reviewer;
- auditor.

### Что у нас есть

- `auth_audit`;
- JWT/JWKS;
- roles;
- access filter before synthesis;
- source access checks;
- export access revalidation;
- audit events;
- tests for auth and access.

### Где сделали круче

Задание в backend задачах допускало auth stub. У нас auth is real: JWT, refresh, JWKS, user roles, password policy.

### Чего не хватает

Нужно расширить access confidence:

- more fixtures by role;
- external partner scenarios;
- access denied audit;
- source/search/graph/export all checked;
- RoleSwitcher cannot override backend role in production UI;
- rate limiting missing or not proven.

### Как закрыть

1. Build access fixture pack:
   - public document;
   - internal document;
   - confidential document;
   - external partner.
2. Run same query as admin/researcher/external partner.
3. Check answer evidence, source resolve, graph, search, export.
4. Hide or isolate RoleSwitcher in production mode.
5. Add rate limiting decision.

## 10. Audit log

### Что требует задание

Audit log должен фиксировать:

- `query_created`;
- `answer_generated`;
- `source_opened`;
- `document_uploaded`;
- `document_exported`;
- `review_decision`;
- `access_denied`;
- `admin_setting_changed`.

### Что у нас есть

- audit storage in backend;
- query audit;
- source viewed audit;
- export audit;
- admin/audit UI/API pieces.

### Где сделали круче

Audit не просто UI mock: он backed by PostgreSQL pieces and service flows.

### Чего не хватает

Нужно сделать audit coverage matrix:

- какие events реально пишутся;
- какие only planned;
- какие видны в admin UI;
- какие есть в tests.

Вероятные gaps:

- `answer_generated`;
- `review_decision`;
- `admin_setting_changed`;
- `access_denied` across all routes.

### Как закрыть

Add audit e2e:

1. Upload document.
2. Run query.
3. Open source.
4. Export.
5. Trigger denied access.
6. Check audit table/API/UI.

## 11. Export

### Что требует задание

MVP:

- Markdown;
- JSON.

Top-1:

- PDF;
- `JSON-LD`;
- evidence bundle;
- source links;
- graph;
- gaps;
- conflicts;
- confidence;
- `QueryIR`;
- `retrieval_trace`;
- user role and access scope.

### Что у нас есть

- Markdown/JSON through orchestrator;
- gateway export endpoint;
- source access revalidation;
- audit event;
- export content includes answer, evidence, sources, graph, gaps, conflicts, warnings, `QueryIR`, `retrieval_trace`, role/access scope and `latency_ms`;
- export service skeleton as reserved boundary.

### Где сделали круче

Export path already thinks about access revalidation, which is important and often missed.

### Чего не хватает

MVP export boundary is explicit: product scenario works through orchestrator/gateway; export service exists as a reserved future boundary and is not the real production boundary.

Also:

- PDF not implemented as backend service;
- `JSON-LD` not wired through final export service;
- MinIO storage for exported files not fully established;
- UI/backend boundary should be made explicit: authoritative export should be backend export, client-side export can remain convenience only.

### Как закрыть

Choose one path:

**Path A, recommended short-term:** keep export in orchestrator.

- Document export service as reserved boundary.
- Make Markdown/JSON complete and tested.
- Keep access revalidation.
- Mark PDF/JSON-LD as top-1 backlog.

**Path B:** implement real export service.

- Add HTTP API to `services/export`;
- use `export_db`;
- store files in MinIO;
- call model JSON-LD endpoint;
- gateway/orchestrator proxy consistently.

## 12. Notifications and user interests

### Что требует задание

Top-1 product should have:

- user interest profile;
- notification matching;
- notification center;
- new document triggers notification.

### Что у нас есть

- notification service skeleton;
- `notification_db`;
- gateway notification API pieces;
- UI notification store/bell;
- model matching endpoint.

### Где сделали круче

Есть database layer and model endpoint. Это больше, чем просто UI stub.

### Чего не хватает

Не хватает end-to-end scenario:

`user interest -> new evidence/document -> match -> persisted notification -> UI notification -> mark read`.

### Как закрыть

1. Decide owner:
   - notification service owns interest and notification lifecycle.
2. Add endpoints:
   - interests CRUD;
   - list notifications;
   - mark read.
3. Wire matching:
   - on ingestion or query event;
   - call model `/notifications/match`;
   - persist result.
4. Add UI smoke.

## 13. UI and demo story

### Что требует задание

UI must show:

- upload and processing status;
- chat;
- search filters;
- source viewer;
- evidence table;
- local graph;
- gaps;
- conflicts;
- experts;
- dashboards;
- export;
- admin access/audit.

### Что у нас есть

Есть много UI pages and components:

- ChatPage;
- UploadPage;
- SearchPage;
- GraphPage;
- Admin/Audit;
- dashboards;
- source components;
- answer renderer;
- warnings and reason code pieces.

### Где сделали круче

UI выглядит не как bare chat. Есть dashboard and graph direction, i18n, tests, state stores.

### Чего не хватает

Нужно prove production mode:

- no mock source catalog in live path;
- RoleSwitcher not production risk;
- source viewer opens real source;
- gaps/conflicts visible on real payloads;
- export and notification use real backend;
- mobile layout clean.

### Как закрыть

1. Run UI with `VITE_USE_MOCK=false`.
2. Walk through final demo story:
   - upload;
   - question;
   - evidence;
   - source;
   - graph;
   - gap/conflict;
   - export;
   - audit.
3. Capture failures as UI P0/P1 cards.

## 14. Dashboards, evaluation and performance trace

### Что требует задание

Top-1 should show:

- manager dashboard;
- evaluation dashboard;
- performance trace;
- metrics: `SourceSpan Citation Coverage`, `Numeric Correctness`, `Evidence Recall@k`, `Unsupported Claim Rate`, `Entity Linking F1`, `Retrieval Latency`, `Answer Completeness`, `Geo Correctness`, `Access Filtering Correctness`, `Conflict Detection Accuracy`, `Gap Precision`, `Export Completeness`, `p50/p95 latency`, `query trace completeness`.

### Что у нас есть

- eval scripts;
- eval reports;
- regression suites;
- analytics/dashboard pieces;
- `retrieval_trace`;
- perf/reliability report;
- CI e2e.

### Где сделали круче

Evaluation is not just an idea: repo contains eval runner, suites, quality gate and pinned artifact.

### Чего не хватает

- UI evaluation dashboard is not final;
- live `p50/p95` blocked by no live model calls;
- official expected source spans reviewed and pinned;
- conflict/gap precision needs reviewed data;
- performance trace must be demonstrated in UI or report.

### Как закрыть

1. Keep offline eval now.
2. Mark live metrics as `blocked_by_policy`.
3. Add final report once models allowed.
4. Make dashboard read latest eval report or include static report link.

## 15. Architecture and service boundaries

### Что требует задание

Microservice boundaries should be real:

- Gateway;
- Auth/Security/Audit;
- Orchestrator;
- Ingestion;
- Knowledge;
- Retrieval;
- Model;
- Export;
- Notification.

### Что у нас есть

All services exist in repo and compose.

### Где сделали круче

Core services are much more than skeletons. Especially:

- auth;
- ingestion;
- knowledge;
- retrieval;
- model;
- orchestrator;
- gateway.

### Чего не хватает

Export and notification are the weak boundaries.

Also orchestrator is large and owns many workflows. This is okay short-term, but production maintenance risk.

### Как закрыть

1. Decide explicitly:
   - export in orchestrator now, service later;
   - notification service real now or backlog.
2. Avoid pretending stubs are production features.
3. Split orchestrator later by runners:
   - ingestion runner;
   - query runner;
   - export runner;
   - notification/event runner.

## 16. Data scale and reliability

### Что требует задание

Target architecture should handle fast evidence retrieval, with initial answer/evidence in 3-5 seconds for preprocessed data and future scale up to 1M entities.

### Что у нас есть

- precompute-on-ingestion principle;
- Qdrant;
- Neo4j indexes;
- caching;
- timeout/fallback tests;
- performance smoke scripts.

### Где сделали круче

Reliability tests already cover several degraded cases: timeout, empty evidence, disabled stream, fallback warnings.

### Чего не хватает

- no live `latency_ms_p95` because models are blocked;
- no large-corpus benchmark;
- retry policy is absent by design;
- alerting policy not final.

### Как закрыть

1. Keep offline reliability tests.
2. Add seeded performance smoke without live model calls.
3. After permission, run live latency suite.
4. Decide retry policy:
   - fail-fast;
   - limited retry;
   - circuit breaker.

## 17. What we should not do

Согласно заданию, нельзя:

- hardcode official answers;
- claim performance without trace;
- claim live model quality without live run;
- bypass access checks;
- treat candidates as confirmed facts;
- change contracts/security/migrations without sync;
- start big new features before closing MVP gates.

Для нас это означает:

- не коммитить live model answers into pinned artifact;
- не маскировать export/notification stubs;
- не писать “production-ready pass” при open P0;
- не делать UI-only success without backend evidence.

## 18. Пул работ по приоритету

### P0: обязательно до честного top-1 readiness

| ID | Work | Why |
|---|---|---|
| `P0-01` | Clean assembly gate | Нужно доказать clean build/start/seed/reset |
| `P0-02` | Official source spans | Без expected `SourceSpan` ids нет strict evidence recall |
| `P0-03` | Official scenario report | Нужно показать 4 official questions against metrics |
| `P0-04` | Access regression pack | Закрытые sources не должны попадать в synthesis |
| `P0-05` | Source viewer live smoke | Evidence-first требует correct source open |
| `P0-06` | Export Markdown/JSON completeness | Closed for MVP via orchestrator/gateway; export service remains reserved boundary |
| `P0-07` | Hybrid retrieval quality report | Regression gates есть; нужен seeded report по official corpus and channel contribution |

### P1: сильно влияет на доверие и product strength

| ID | Work | Why |
|---|---|---|
| `P1-01` | Geo/numeric/time quality proof | Enforcement есть; нужен proof на official scenarios and corpus |
| `P1-02` | UI production cleanup | Убрать mock/dev risks from live path |
| `P1-03` | RoleSwitcher dev-only | Client role override is production risk |
| `P1-04` | Notification end-to-end | Top-1 feature currently incomplete |
| `P1-05` | Audit coverage matrix | Нужно доказать required audit events |
| `P1-06` | Observability and alerts | Нужна эксплуатационная понятность |
| `P1-07` | Backup/restore scope | Production data must be recoverable |

### P2: усиливает продукт и поддержку

| ID | Work | Why |
|---|---|---|
| `P2-01` | PDF/JSON-LD export | Top-1 polish |
| `P2-02` | Review console/fact versioning UI | Claim-based trust |
| `P2-03` | Evaluation dashboard UI | Quality visible to jury/users |
| `P2-04` | Orchestrator decomposition | Maintainability |
| `P2-05` | Operator runbook | Easier handoff and support |

## 19. Рекомендуемый порядок

1. Закрыть clean assembly gate.
2. Закрыть official questions source expectations.
3. Закрыть source/access/export audit.
4. Доказать `hybrid retrieval` channels and constraints.
5. Привести UI production path к real backend.
6. Принять honest boundary decision for export and notification.
7. Сделать final offline readiness report.
8. После разрешения organizers выполнить live model eval and update status.

## Финальный вердикт

По заданию мы уже сделали сильную архитектурную основу и местами пошли дальше MVP: real auth, real graph/vector storage, contracts, CI, eval, reliability. Это хороший фундамент для top-1.

Но оставшиеся gaps лежат в доказанности сценариев:

- official answers must be evidence-checked;
- retrieval уже hybrid in code; нужно доказать quality and channel contribution on agreed corpus;
- access and source correctness must be proven end-to-end;
- export and notification boundaries must be honest;
- live model quality cannot be claimed until organizers allow live model calls.

Если закрыть P0 из этого документа, проект можно будет гораздо честнее позиционировать как top-1-ready system, а не просто сильный prototype.
