# Production-readiness task cards

**Дата:** 2026-07-04  
**Назначение:** пул подробных работ по результатам production-readiness analysis.  
**Правило:** карточки можно брать независимо только если у них `Can run independently: yes`. Если указано `sync-required`, перед реализацией нужна синхронизация команды.

Писать карточки простым русским языком. Technical terms оставлять на English: `SourceSpan`, `QueryIR`, `EvidenceBundle`, `RBAC`, `CI`, `e2e`, `hybrid retrieval`, `latency_ms_p95`.

## Dependency rules

| Marker | Meaning |
|---|---|
| `independent` | Можно выполнять без ожидания других карточек |
| `sync-required` | Нужна синхронизация, потому что затрагиваются contracts, public API, migrations, ontology или security |
| `blocked_by_policy` | Нельзя завершить без разрешения live model calls |
| `blocked_by_data` | Нужны reviewed fixtures или corpus decisions |

## E0. Analysis freeze

### PRD-E0-001: Зафиксировать baseline

**Priority:** `P0`  
**Mode:** `independent`  
**Can run independently:** yes  
**Goal:** зафиксировать точную версию проекта, на которой делается анализ.

**Why it matters:** без baseline любой вывод быстро становится спорным.

**Inputs:** `git status`, `git rev-parse HEAD`, `docker-compose.yml`, `Makefile`, `.github/workflows/ci.yml`, `.env.example`.

**Changes expected:** добавить baseline section в `prod_readiness_analysis.md`.

**Acceptance criteria:**

- указан branch и commit SHA;
- указано, clean ли worktree;
- перечислены build/test/e2e commands;
- указано, какие live model checks запрещены.

**Tests/checks:** не нужны, это documentation-only.

### PRD-E0-002: Собрать scenario matrix

**Priority:** `P0`  
**Mode:** `independent`  
**Can run independently:** yes  
**Goal:** составить matrix всех happy-path и failure scenarios.

**Inputs:** `docs/tz/mvp.md`, `demo/official_questions.md`, `eval/gold_questions.json`, `query_pipeline.md`, UI routes, gateway/orchestrator endpoints.

**Changes expected:** таблица scenarios в `prod_readiness_analysis.md`.

**Acceptance criteria:**

- есть upload, ingestion, dictionary, 4 official questions, source, graph, search, export, notification, audit, RBAC, reset/reseed;
- есть failure scenarios: empty evidence, access denied, parser failure, timeout, missing dictionary, empty Qdrant, source access drift;
- у каждого scenario есть `Status`, `Evidence`, `Gap`, `Next action`.

**Tests/checks:** `git diff --check`.

### PRD-E0-003: Свести gap register

**Priority:** `P0`  
**Mode:** `independent`  
**Can run independently:** yes  
**Goal:** создать единый список gaps вместо разрозненных заметок.

**Inputs:** `implementation_quality_report.md`, `audit_report.md`, `ml_mvp_status.md`, `top1_*`.

**Changes expected:** gap register с `P0/P1/P2/P3`.

**Acceptance criteria:**

- каждый gap имеет `id`, `priority`, `area`, `scenario`, `evidence`, `impact`, `dependency`, `acceptance criteria`;
- known gaps export, notification, hybrid retrieval, UI mock boundary, RoleSwitcher, live eval, access fixtures отражены явно;
- нет claims без evidence.

**Tests/checks:** `git diff --check`.

## E1. Assembly gates

### PRD-E1-001: Clean build and startup gate

**Priority:** `P0`  
**Mode:** `independent`  
**Can run independently:** yes  
**Goal:** доказать, что проект собирается и стартует с clean volumes.

**Inputs:** `docker-compose.yml`, `.env.example`, `Makefile`, service Dockerfiles.

**Changes expected:** если анализ только документальный, зафиксировать result. Если gate падает, создать отдельные fix cards.

**Acceptance criteria:**

- `Copy-Item .env.example .env`;
- `python scripts/generate_auth_keys.py`;
- `docker compose up -d --build --wait`;
- все services healthy или причина fail записана;
- нет ручных DB edits.

**Tests/checks:** `docker compose ps`, `/health`, `/ready`, `docker compose logs` for failed services.

### PRD-E1-002: Reset and seed gate

**Priority:** `P0`  
**Mode:** `independent`  
**Can run independently:** yes  
**Goal:** доказать, что demo corpus можно загрузить повторяемо.

**Inputs:** `scripts/seed_demo.py`, `demo/seed_data/`, `eval/pinned_demo_artifact.json`, dictionary APIs.

**Acceptance criteria:**

- clean reset выполняется без ручных правок;
- users seeded;
- active dictionary создан и активирован;
- demo documents indexed into Neo4j and Qdrant;
- seed result содержит counts по documents, tables, `SourceSpan`, claims.

**Tests/checks:** `python scripts/seed_demo.py` in no-live/fallback mode, health endpoints, Qdrant/Neo4j smoke if available.

### PRD-E1-003: CI and coverage gate

**Priority:** `P0`  
**Mode:** `independent`  
**Can run independently:** yes  
**Goal:** подтвердить, что локальные проверки соответствуют CI.

**Inputs:** `.github/workflows/ci.yml`, `scripts/run_tests.py`, `ui/package.json`.

**Acceptance criteria:**

- `ruff check shared services scripts tests` passes;
- `COVERAGE=1 COVERAGE_FAIL_UNDER=60 python scripts/run_tests.py` passes;
- `cd ui && npm ci && npm test && npm run build && npm run lint` passes;
- если что-то падает, создана `P0` или `P1` fix card.

**Tests/checks:** команды выше.

### PRD-E1-004: Offline quality gate

**Priority:** `P0`  
**Mode:** `blocked_by_policy` for live quality, `independent` for offline gate  
**Can run independently:** no  
**Goal:** отделить offline quality от live model quality.

**Inputs:** `eval/demo_quality_gate.py`, `eval/pinned_demo_artifact.json`, `eval/regression_suites.json`.

**Acceptance criteria:**

- `python eval/demo_quality_gate.py` runs;
- pinned input integrity is checked;
- suite inventory is checked;
- without live report итог честно `blocked`, not `pass`;
- report says live model quality is `blocked_by_policy`.

**Tests/checks:** `python eval/demo_quality_gate.py`.

## E2. Scenario closure

### PRD-E2-001: Official questions offline scenario audit

**Priority:** `P0`  
**Mode:** `blocked_by_policy` for live answers, `independent` for offline structure  
**Can run independently:** no  
**Goal:** проверить, готова ли система к 4 official questions без утверждения live quality.

**Inputs:** `demo/official_questions.md`, `eval/gold_questions.json`, `eval/regression_suites.json`.

**Acceptance criteria:**

- для каждого official question указаны expected entities, numeric/geo/time constraints, answer outline;
- gaps по empty `expected_source_span_ids` зафиксированы;
- offline QueryIR/retrieval checks, если доступны без live models, выполнены;
- live answer quality marked `blocked_by_policy`.

**Tests/checks:** offline eval runner commands only if they do not call external models.

### PRD-E2-002: Source viewer and citation audit

**Priority:** `P0`  
**Mode:** `independent` unless public API changes are needed  
**Can run independently:** yes  
**Goal:** доказать, что source links открывают правильный accessible `SourceSpan`.

**Inputs:** gateway `/source/{source_span_id}`, orchestrator source resolve, retrieval source resolve, UI source resolver.

**Acceptance criteria:**

- source link from chat resolves live source when `VITE_USE_MOCK=false`;
- inaccessible source returns controlled 404/403 and audit event;
- export revalidates the same source access;
- remaining mock dependencies listed.

**Tests/checks:** gateway/orchestrator source tests, UI sourceResolver tests, e2e source smoke.

### PRD-E2-003: RBAC and access audit

**Priority:** `P0`  
**Mode:** `sync-required` if security behavior changes  
**Can run independently:** no  
**Goal:** доказать, что access filtering happens before synthesis.

**Inputs:** auth_audit, gateway, orchestrator, retrieval tests, `tests/integration/test_access_leak.py`.

**Acceptance criteria:**

- admin sees allowed internal/confidential data according to policy;
- external partner does not see restricted evidence;
- restricted evidence is not sent to model synthesis;
- `access_leak_rate == 0.0`;
- RoleSwitcher production risk documented or fixed in separate card.

**Tests/checks:** `tests/integration/test_access_leak.py`, retrieval access tests, e2e role smoke.

### PRD-E2-004: Export scenario audit

**Priority:** `P0`  
**Mode:** `sync-required` if export service boundary changes  
**Can run independently:** no  
**Goal:** понять, достаточно ли текущего export path для production-ready.

**Inputs:** gateway `/export`, orchestrator export, `services/export`, `infra/postgres/export_db`.

**Acceptance criteria:**

- Markdown and JSON export include answer, evidence table, source links, graph, gaps, conflicts, confidence, `QueryIR`, `retrieval_trace`, user role, warnings;
- export writes audit event;
- export revalidates source access;
- service boundary status is explicit: orchestrator-owned or export-service-owned;
- JSON-LD gap is documented if not implemented.

**Tests/checks:** orchestrator export tests, gateway export smoke, e2e export smoke.

### PRD-E2-005: Notification scenario audit

**Priority:** `P1`  
**Mode:** `sync-required` if notification service API changes  
**Can run independently:** no  
**Goal:** понять, является ли notification реальной product feature или только UI/service stub.

**Inputs:** `services/notification`, `infra/postgres/notification_db`, gateway notifications API, model notification matching.

**Acceptance criteria:**

- user interests can be created/read/updated;
- notifications can be listed and marked read;
- matching source is clear: model endpoint, orchestrator event, or scheduled job;
- UI bell uses real data in production mode;
- service boundary status is explicit.

**Tests/checks:** gateway notification tests, notification service tests, UI notificationStore tests.

## E3. Retrieval and answer quality closure

### PRD-E3-001: Hybrid retrieval gap closure plan

**Priority:** `P0/P1`  
**Mode:** `sync-required` if contracts or APIs change  
**Can run independently:** no  
**Goal:** определить, чего не хватает до target `hybrid retrieval`.

**Inputs:** retrieval service, knowledge graph exact search, `top1_e1_bm2_ml_policy.md`, `top1_e0_contract_audit.md`.

**Acceptance criteria:**

- current vector, graph, table, lexical, numeric, geo, time channels listed;
- missing channels marked with evidence;
- `fusion` behavior described;
- `retrieval_trace` shows selected channels and filters;
- official question impact documented.

**Tests/checks:** retrieval planner tests, graph exact search tests, offline query pipeline tests.

### PRD-E3-002: Geo/numeric/time filter audit

**Priority:** `P0/P1`  
**Mode:** `independent` unless QueryIR contract changes  
**Can run independently:** yes  
**Goal:** проверить, применяются ли constraints до rerank/synthesis.

**Inputs:** `QueryIR`, retrieval Qdrant payload, model gap suggestions, official questions.

**Acceptance criteria:**

- numeric constraints from official-001 are parsed;
- time constraint from official-003 is parsed;
- geo constraints from official-004 are parsed;
- constraints are enforced or gap is explicit;
- no unsupported fact promoted to confirmed answer.

**Tests/checks:** model QueryIR tests, retrieval query tests, eval metrics if offline.

### PRD-E3-003: Unsupported, gap and conflict behavior audit

**Priority:** `P1`  
**Mode:** `blocked_by_data` if reviewed expectations are missing  
**Can run independently:** no  
**Goal:** проверить, что система честно показывает uncertainty.

**Inputs:** model contracts, orchestrator scientific query, `EvidenceBundle`, answer renderer.

**Acceptance criteria:**

- unsupported claims have reason codes;
- gaps are visible in backend response and UI;
- conflicts are not mixed across incomparable conditions;
- candidate facts are not rendered as confirmed facts;
- reviewed fixtures needed for strict accuracy are listed.

**Tests/checks:** model tests, orchestrator scientific query tests, UI AnswerRenderer tests.

## E4. Production hardening

### PRD-E4-001: Security hardening audit

**Priority:** `P1`  
**Mode:** `sync-required` for security changes  
**Can run independently:** no  
**Goal:** найти production security gaps.

**Inputs:** auth_audit service, shared security, gateway auth, nginx, `.env.example`.

**Acceptance criteria:**

- default credentials and demo secrets are identified;
- JWT/JWKS behavior documented;
- refresh/session behavior documented;
- missing rate limiting assessed;
- RoleSwitcher production exposure assessed;
- external partner access path verified.

**Tests/checks:** auth tests, security tests, manual config review.

### PRD-E4-002: Observability and operations audit

**Priority:** `P1`  
**Mode:** `independent`  
**Can run independently:** yes  
**Goal:** понять, сможет ли оператор понять, что система сломалась.

**Inputs:** Prometheus config, Grafana dashboards, service logs, `/metrics`, `X-Request-ID`.

**Acceptance criteria:**

- all services expose metrics;
- request_id visible across gateway/orchestrator/retrieval/model;
- query run stores `latency_ms` and `retrieval_trace`;
- alerts/gaps are listed;
- logs do not leak secrets.

**Tests/checks:** health/metrics smoke, log review, query trace review.

### PRD-E4-003: Backup and restore audit

**Priority:** `P1/P2`  
**Mode:** `independent`  
**Can run independently:** yes  
**Goal:** проверить, можно ли восстановить данные.

**Inputs:** PostgreSQL, Neo4j, Qdrant, MinIO, scripts `backup_db.sh`, `restore_db.sh`.

**Acceptance criteria:**

- backup scope is documented;
- restore steps are documented;
- missing Qdrant/MinIO backup path is recorded if absent;
- restore smoke scenario defined.

**Tests/checks:** dry-run or documented command review.

### PRD-E4-004: Performance audit without live models

**Priority:** `P1`  
**Mode:** `blocked_by_policy` for live latency, `independent` for offline reliability  
**Can run independently:** no  
**Goal:** отделить offline reliability от live latency claims.

**Inputs:** `scripts/perf_smoke.py`, `scripts/query_reliability.py`, E6 perf report.

**Acceptance criteria:**

- offline reliability scenarios pass;
- timeout behavior documented;
- `latency_ms_p95` live gate marked `blocked_by_policy`;
- no performance claim is made without trace.

**Tests/checks:** performance tests that do not call external models.

## E5. Product polish and runbooks

### PRD-E5-001: UI production cleanup plan

**Priority:** `P1/P2`  
**Mode:** `sync-required` if API/auth behavior changes  
**Can run independently:** no  
**Goal:** убрать риски demo-only UX из production path.

**Inputs:** UI source resolver, authStore, RoleSwitcher, chat answer flow.

**Acceptance criteria:**

- `VITE_USE_MOCK=false` path audited;
- RoleSwitcher is dev-only or risk documented;
- source resolver has live path;
- warnings/gaps/conflicts/degraded states render clearly;
- mobile/desktop smoke checklist exists.

**Tests/checks:** UI tests, build, manual browser smoke if implementation follows.

### PRD-E5-002: Operator runbook

**Priority:** `P2`  
**Mode:** `independent`  
**Can run independently:** yes  
**Goal:** дать понятную инструкцию запуска и диагностики без знания кода.

**Inputs:** Makefile, compose, health endpoints, seed/eval scripts.

**Acceptance criteria:**

- clean setup steps;
- reset/reseed steps;
- health troubleshooting;
- where to find logs;
- what statuses mean;
- what cannot be claimed without live models.

**Tests/checks:** runbook reviewed against real commands.

### PRD-E5-003: Documentation drift cleanup

**Priority:** `P2`  
**Mode:** `independent` unless structure changes  
**Can run independently:** yes  
**Goal:** синхронизировать agent docs with current implementation.

**Inputs:** `project_structure.md`, domain docs, reports, code structure.

**Acceptance criteria:**

- stale claims removed or marked;
- export/notification status consistent everywhere;
- CI/e2e status consistent everywhere;
- new analysis docs listed in `project_structure.md`.

**Tests/checks:** `rg` for contradictory statuses, `git diff --check`.

## Final delivery checklist

Перед завершением анализа:

- `prod_readiness_analysis.md` содержит baseline, scenario matrix, subsystem findings, gap register.
- `prod_readiness_task_cards.md` содержит detailed cards with dependencies.
- Все live model checks помечены `blocked_by_policy`.
- Нет утверждений `production-ready: pass`, если есть open P0.
- `project_structure.md` обновлен.
- `git diff --check` выполнен.
