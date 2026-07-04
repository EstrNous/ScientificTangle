# Матрица готовности фич ScientificTangle / НорСинтез

**Дата:** 2026-07-04  
**База:** `origin/dev` после этапов E0–E7 (no-live gates)  
**Источники:** `implementation_quality_report.md`, validation reports E0–E7, `audit_report.md`, `mvp.md`, `ml_mvp_status.md`, сверка с кодом.

Процент — оценка **готовности к production-ready 100%**, а не «есть ли код вообще».

Связанные документы:

- [`mvp.md`](../tz/mvp.md) — Definition of Done MVP
- [`implementation_quality_report.md`](implementation_quality_report.md) — сводка по сервисам
- [`nornikel_e7_bml_readiness_summary.md`](nornikel_e7_bml_readiness_summary.md) — финальный no-live статус Backend/ML

---

## Сводная шкала (по возрастанию готовности)

| # | Фича | Итого | Фронт | Бэк | Связь Ф↔Б |
|---|------|------:|------:|----:|----------:|
| 1 | Cloud deploy / HTTPS / prod-хостинг | **0%** | 0% | 0% | 0% |
| 2 | Export microservice (`services/export`) | **5%** | — | 5% | 0% |
| 3 | Notification microservice (`services/notification`) | **100%** | — | 100% | 0% |
| 4 | JSON-LD / PDF export | **20%** | 15% | 35% | 10% |
| 5 | Live eval и качество ответов | **25%** | 30% | 40% | 15% |
| 6 | Full-corpus gold dataset (`SourceSpan`) | **30%** | 10% | 45% | 20% |
| 7 | Backup/restore Qdrant + MinIO | **40%** | 0% | 50% | 30% |
| 8 | Runtime-уведомления (`ingestion_complete`, `interest_match`) | **98%** | 100% | 96% | 95% |
| 9 | Удаление документа (полный cascade) | **65%** | 80% | 60% | 55% |
| 10 | Audit CSV (server-side download) | **68%** | 75% | 70% | 60% |
| 11 | E2E в обязательном CI (stack + Playwright) | **60%** | 65% | 55% | 50% |
| 12 | Eval dashboard | **70%** | 75% | 65% | 70% |
| 13 | Strategic / Lab дашборды | **72%** | 80% | 70% | 65% |
| 14 | Уведомления (product path через gateway) | **75%** | 85% | 75% | 70% |
| 15 | Экспорт MD/JSON (orchestrator path) | **78%** | 85% | 80% | 75% |
| 16 | Review console | **80%** | 85% | 80% | 75% |
| 17 | Admin + audit log UI | **82%** | 88% | 80% | 78% |
| 18 | Профиль / интересы | **85%** | 90% | 85% | 82% |
| 19 | Поиск (`SearchPage`) | **83%** | 88% | 80% | 78% |
| 20 | Загрузка / ingestion UI | **87%** | 90% | 88% | 85% |
| 21 | Справочники (dictionaries) | **87%** | 90% | 88% | 85% |
| 22 | Source viewer / цитирование | **88%** | 92% | 88% | 85% |
| 23 | RBAC / access policy | **90%** | 88% | 93% | 88% |
| 24 | Граф (`GraphPage`) | **90%** | 92% | 90% | 88% |
| 25 | Чат / научный Q&A | **88%** | 90% | 90% | 87% |
| 26 | Hybrid retrieval | **85%** | 70% | 90% | 82% |
| 27 | Ingestion pipeline (бэк) | **88%** | — | 90% | 85% |
| 28 | Knowledge / Neo4j | **90%** | 75% | 93% | 88% |
| 29 | Model service (ML) | **92%** | 60% | 95% | 88% |
| 30 | Auth / JWT / audit (бэк) | **93%** | 85% | 95% | 90% |
| 31 | Gateway / BFF / chat persistence | **88%** | 85% | 92% | 88% |
| 32 | Infra / Docker / CI / observability | **85%** | 80% | 88% | 82% |
| 33 | E7 UI polish (health, empty states, PWA) | **88%** | 92% | 70% | 85% |

---

## Детали по каждой фиче

### 1. Cloud deploy / HTTPS — **0%**

| Слой | Сделано | До 100% не хватает |
|------|---------|-------------------|
| **Фронт** | Vite build, PWA manifest, OG meta (E7) | CDN, env-specific URLs, prod error tracking |
| **Бэк** | Docker Compose локально | K8s/VM, secrets manager, TLS, autoscaling |
| **Связь** | nginx в compose | WAF, rate limit на edge, CORS для prod-домена |

**Быстро → дорого:** задокументировать prod `.env` → HTTPS в nginx + Let's Encrypt → выделенный staging → полный cloud IaC.

---

### 2. Export microservice — **5%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | — | Не применимо (UI ходит в gateway/orchestrator) |
| **Бэк** | Только `/health` в `services/export/app/main.py`; схема `export_db` есть, не wired | HTTP API, worker/async jobs, MinIO artifacts, Alembic в compose CMD |
| **Связь** | Export идёт через orchestrator (`POST /export`) | Решение границы: orchestrator-owned vs отдельный сервис; proxy из gateway |

**Быстро → дорого:** зафиксировать boundary в docs (уже orchestrator-owned) → удалить/архивировать `export_db` drift → вынести jobs в `services/export` с тем же контрактом → async queue + retention runbook.

---

### 3. Notification microservice — **5%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | `NotificationBell`, poll `?since=` (E5) | — |
| **Бэк** | `services/notification` — только health; логика в gateway + `notification_db` | CRUD в микросервисе или официальный отказ от него |
| **Связь** | Gateway → PG + model `/v1/notifications/match` | Event bus: ingestion → match → persist |

**Быстро → дорого:** пометить сервис deprecated в domain docs → runtime hooks в orchestrator (см. фичу 8) → полноценный notification service с WebSocket/SSE.

---

### 4. JSON-LD / PDF export — **20%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | `ExportPanel`: JSON-LD/PDF disabled, честный backlog (E5) | Кнопки, progress, download |
| **Бэк** | Model `/v1/json-ld/enrich` готов; orchestrator — MD/JSON only | Wiring JSON-LD в export path; PDF renderer (server-side) |
| **Связь** | UI знает `format_status` | End-to-end: export job → artifact → download URL |

**Быстро → дорого:** включить JSON-LD через orchestrator + model endpoint → UI download → PDF (WeasyPrint/headless) → MinIO signed URLs.

---

### 5. Live eval и качество ответов — **25%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | `StrategicQualityPage` + `fetchEvalReportSummary`; blocked states | Live dashboard с реальными метриками |
| **Бэк** | `eval/run_eval.py`, `offline_quality_gate.py`, `demo_quality_gate.py`, pinned manifest | Pinned **live** report в `eval/reports/`; p50/p95; CI gate |
| **Связь** | Offline gate в Makefile | `EVAL_AUTH_TOKEN` автоматизация; live eval в CI (policy) |

**Быстро → дорого:** автогенерация `EVAL_AUTH_TOKEN` в seed → один manual live run + commit artifact → CI job с Yandex secrets → regression на каждый PR.

---

### 6. Full-corpus gold dataset — **30%** (`blocked_by_data`)

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | Review UI готов | Review всего корпуса в UI |
| **Бэк** | 4/4 official questions с reviewed `SourceSpan` (demo); `gold_questions.json`, fixtures | Нормализация **всего** корпуса до reviewed ids |
| **Связь** | Offline gate: official pass, full corpus `blocked_by_data` | Data review pipeline + обновление `eval/regression_suites.json` |

**Быстро → дорого:** список uncovered docs → batch review в Review Console → обновить fixtures → включить suite в offline gate.

---

### 7. Backup/restore Qdrant + MinIO — **40%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | — | Ops UI (опционально) |
| **Бэк** | PG: `backup_db.sh` / `restore_db.sh`; Neo4j partial (APOC) | Qdrant snapshot API; MinIO `mc mirror`; verify manifest |
| **Связь** | `seed_inventory.py` для verify counts | Restore smoke: PG + reseed vs full restore |

**Быстро → дорого:** runbook в docs (E7) → Qdrant snapshot script → MinIO backup → automated restore test в CI.

---

### 8. Runtime-уведомления — **55%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | Bell, poll, mark read, i18n types (E3/E5) | Toast на новые; deep-link document viewer |
| **Бэк** | `conflict_detected` из chat/query (E5); seed для `ingestion_complete`/`interest_match` | Hooks после ingestion complete + interest match через model |
| **Связь** | `GET /notifications?since=` работает | Orchestrator event → gateway `NotificationService.create` |

**Быстро → дорого:** hook в ingestion completion (orchestrator) → interest match после index → document-level resolve для `reference_type=document` → push/SSE.

---

### 9. Удаление документа — **65%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | Delete в Upload/Admin, optimistic rollback, 403/404 i18n (E3) | — |
| **Бэк** | `DELETE /documents/{id}`: PG tombstone, Neo4j, Qdrant deindex (E3) | **MinIO object delete** (B-E6-01, open) |
| **Связь** | Gateway proxy + audit | Полный cascade без warnings в response |

**Быстро → дорого:** вызов MinIO delete по `minio_object_refs` из migration `0009` → integration test → purge export artifacts по document_id.

---

### 10. Audit CSV server-side — **68%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | Client-side CSV в `AdminAuditPage` (E5) | Download с сервера для больших логов |
| **Бэк** | `audit_csv_exports` storage; pagination filters | `GET /audit/export.csv` endpoint |
| **Связь** | Filters → orchestrator | Тот же filter contract server/client |

**Быстро → дорого:** gateway endpoint + streaming CSV → UI переключить на server download → retention policy.

---

### 11. E2E в обязательном CI — **60%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | Playwright `@offline` scenarios 1–10 (E6); `build:e2e` | `@stack` job в GitHub Actions |
| **Бэк** | `test_official_questions_smoke.py` | Compose job: health + 1 official question |
| **Связь** | Checklist E6 | `RUN_UI_E2E=1` блокирует merge |

**Быстро → дорого:** vitest + offline gate в CI (есть) → Docker compose job → Playwright `@stack` nightly → mandatory on PR.

---

### 12. Eval dashboard — **70%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | Summary UI, blocked/offline states (E5) | Графики трендов, drill-down по question |
| **Бэк** | `/eval/report/summary`; reports на диске | API списка reports + diff между runs |
| **Связь** | `fetchEvalReportSummary` | Автообновление после `make eval` |

**Быстро → дорого:** список reports в API → UI table → сравнение с pinned artifact.

---

### 13. Strategic / Lab дашборды — **72%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | `StrategicCoveragePage`, `StrategicQualityPage`, `LabMatrixPage`, `LabInsightsPage`, Recharts | Empty/degraded states; mobile polish частично |
| **Бэк** | `gateway` analytics endpoints | Больше live метрик, не только demo aggregates |
| **Связь** | `fetchStrategicMetrics`, `fetchStrategicEvaluation` | Данные из реальных QueryRun, не static |

**Быстро → дорого:** привязать charts к `orchestrator_db` aggregates → degraded banner при пустых данных → e2e smoke.

---

### 14. Уведомления (product path) — **75%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | Bell, badge, poll, click → source (E3/E5) | Document viewer для `reference_type=document` |
| **Бэк** | CRUD list/read; conflict notifications; model match offline | Runtime events (фича 8) |
| **Связь** | Gateway ↔ `notification_db` | Полный lifecycle без seed |

**Быстро → дорого:** document resolve endpoint → runtime hooks → naming `source_opened` vs `source_viewed` (B-E6-04).

---

### 15. Экспорт MD/JSON — **78%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | `ExportPanel` → `POST /api/export`; evidence table; client fallback за flag (E5) | JSON-LD/PDF |
| **Бэк** | Orchestrator inline export; access re-check; audit; `ExportJob` в PG | Async jobs для больших export; retention |
| **Связь** | Production path через server | Убрать client-only fallback в prod |

**Быстро → дорого:** отключить client fallback при `VITE_USE_MOCK=false` → async job status polling → MinIO artifact URLs.

---

### 16. Review console — **80%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | `ReviewConsolePage`, filters, actions, flag `VITE_REVIEW_CONSOLE_ENABLED` (E2/E3) | Full corpus workflow |
| **Бэк** | Queue + decisions API; Neo4j candidates + PG (E2/E3) | Versioning facts API без review UI gap |
| **Связь** | Gateway → orchestrator `/review/*` | E2E review → reindex |

**Быстро → дорого:** включить flag в prod compose → e2e scenario review decision → fact versioning UI (top-1, L).

---

### 17. Admin + audit log — **82%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | Users/policies save (PATCH), dirty state, `AdminAuditPage` filters/drill-down (E3/E5) | Server CSV (фича 10) |
| **Бэк** | `PATCH /admin/*`, audit events, pagination | Rate limiting; server CSV |
| **Связь** | Persist + audit event on save | — |

**Быстро → дорого:** server CSV endpoint → унифицировать audit action names → admin e2e.

---

### 18. Профиль / интересы — **85%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | `ProfilePage`: load/save API, entities display (E3) | Уведомления при изменении интересов |
| **Бэк** | `GET/PUT /interests`; offline model extract | Runtime interest_match notifications |
| **Связь** | Gateway proxy | Interest change → re-match corpus |

**Быстро → дорого:** hook interest_match после save → UI «подписка активна» → batch re-match job.

---

### 19. Поиск — **83%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | Geo/year/numeric filters, pagination (E4) | Infinite scroll polish |
| **Бэк** | `GET /search` — **только dense vector**; hybrid fusion в `/v1/query` | Тот же fusion в search endpoint |
| **Связь** | `buildSearchQuery` → gateway | Parity search vs query retrieval |

**Быстро → дорого:** прокинуть search через тот же hybrid path → e2e search filters → source identity drift fix (B-E7-05).

---

### 20. Загрузка / ingestion UI — **87%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | `UploadPage`, stepper `task.stages[]`, warnings (E4) | Queue manager для множества файлов |
| **Бэк** | Orchestrator → ingestion → knowledge → retrieval | PDF/DOCX — текстовый путь; VL/OCR для сканов |
| **Связь** | Real API, delete (E3) | Ingestion complete notification |

**Быстро → дорого:** ingestion_complete notification → progress WebSocket → OCR path для сканов (L).

---

### 21. Справочники — **87%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | Admin dictionaries tab: list, activate (E4) | Upload wizard, diff между версиями |
| **Бэк** | `/dictionaries/*`; active preflight на query (E4) | Полный CRUD versioning |
| **Связь** | Warning при inactive dictionary | Block query без active dict (уже частично) |

**Быстро → дорого:** upload UI → version diff view → e2e dictionary activate → query.

---

### 22. Source viewer / цитирование — **88%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | `useSourceResolver`, highlight scroll, `SourceLockedPanel` 403 (E2/E4); mock убран из prod components | Orphan routes audit (E7 deferred) |
| **Бэк** | `POST /sources/{id}/resolve`, highlight fields, access_denied | Document-level resolve |
| **Связь** | Live path при `VITE_USE_MOCK=false` | Identity drift `document_id` vs `source_span_id` (B-E7-05) |

**Быстро → дорого:** fix identity mapping → document viewer route → e2e source resolve smoke (есть offline).

---

### 23. RBAC / access policy — **90%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | `RoleSwitcher` только dev/mock (E4); `RoleRoute` guards | Prod: только JWT session, без switcher |
| **Бэк** | RS256 JWT, RBAC, filter **до** synthesis/export; 35 тестов; `test_access_leak.py` | Rate limiting в gateway |
| **Связь** | `ensureAuth()`, env auto-login в compose | Убрать demo credentials из prod `.env` |

**Быстро → дорого:** скрыть RoleSwitcher в prod build → rate limit middleware → security audit checklist (E4 PRD).

---

### 24. Граф — **90%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | `GraphPage`, `react-force-graph-2d`, LocalGraph в чате | Performance на больших subgraph |
| **Бэк** | Knowledge 15 endpoints; subgraph по query | Graph-centric retrieval tuning |
| **Связь** | Gateway `/graph` | — |

**Быстро → дорого:** lazy load nodes → cap subgraph size в UI → perf smoke.

---

### 25. Чат / научный Q&A — **88%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | `ChatPage`, `AnswerRenderer`, evidence table, gaps/conflicts, streaming flag (E6 default off) | Streaming UX prod default |
| **Бэк** | Full pipeline: QueryIR → retrieval → gaps → subgraph → synthesis | Live quality unproven |
| **Связь** | `POST /chat/sessions/{id}/messages` → orchestrator | Chat persistence в `chat_ui_db` |

**Быстро → дорого:** enable streaming UX → live eval на 4 official → conflict/gap UI polish.

---

### 26. Hybrid retrieval — **85%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | `retrieval_trace` в ответе не всегда показан в UI | Channel breakdown в UI/debug |
| **Бэк** | В `/v1/query`: dense + lexical + table + graph + `fuse_channels`; geo/numeric/time в `build_filter` | `retrieval_planner` не отключает каналы по классу запроса; `/search` без fusion; docs drift |
| **Связь** | Orchestrator → retrieval `/v1/query` | Search parity; live eval на official questions |

> В коде fusion уже есть (`services/retrieval/app/api/query.py`); в `domains/retrieval.md` статус устарел.

**Быстро → дорого:** обновить docs → использовать `retrieval_plan.retriever_profiles` для selective channels → unified search → live eval metrics.

---

### 27. Ingestion pipeline — **88%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | Upload UI (см. фичу 20) | — |
| **Бэк** | Parsers, MinIO, NormalizedDocument, SourceSpan, index в Neo4j/Qdrant | Бинарные форматы, ZIP edge cases, MinIO purge |
| **Связь** | Orchestrator ingestion tasks | End-to-end без warnings |

**Быстро → дорого:** MinIO delete → parser tests на реальных PDF → ingestion notifications.

---

### 28. Knowledge / Neo4j — **90%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | Graph, conflicts in lab/review | Fact versioning review UI (top-1 backlog) |
| **Бэк** | `Neo4jKnowledgeAdapter`, claims, conflicts, gaps, 15 HTTP endpoints | Full versioning workflow |
| **Связь** | Orchestrator handoff | — |

**Быстро → дорого:** versioning API smoke → Review Console для facts → ontology change process.

---

### 29. Model service — **92%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | Косвенно через chat/export | Model status page (опционально) |
| **Бэк** | 13 v1 endpoints, Yandex + deterministic fallback, prompts/schemas, 31 тест | Live eval pin; VL/OCR |
| **Связь** | Все сервисы через httpx | — |

**Быстро → дорого:** pin live eval artifact → `RUN_MODEL_TESTS` в CI (optional) → VL path для сканов.

---

### 30. Auth / JWT — **93%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | Login/register/refresh, `authStore`, `ensureAuth()` | Forgot password flow completeness |
| **Бэк** | RS256, JWKS, refresh cookies, RBAC, audit, Docker secrets | Rate limiting |
| **Связь** | nginx `/api/auth/` → auth_audit | — |

**Быстро → дорого:** rate limit → refresh rotation audit → prod secret rotation runbook.

---

### 31. Gateway / BFF — **88%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | Единый `api/client.js` | — |
| **Бэк** | Chat, query, graph, admin, export, notifications, interests, review proxies | Orchestrator god-service (~940 строк) — deferred refactor |
| **Связь** | `chat_ui_db` persistence | — |

**Быстро → дорого:** thin integration tests → split orchestrator (External Owner) → BFF caching.

---

### 32. Infra / CI — **85%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | `ServiceHealthIndicator`, `/health/all` poll (E7) | — |
| **Бэк** | Compose 9 services + data stores; Prometheus/Grafana; Makefile | Cloud; mandatory stack e2e |
| **Связь** | nginx routing | — |

**Проверки:** 184 backend-теста, coverage 61%, ruff 20 pre-existing issues, offline quality `warn`.

**Быстро → дорого:** fix ruff I001/F401 → stack e2e CI → Qdrant/MinIO backup → cloud.

---

### 33. E7 UI polish — **88%**

| Слой | Сделано | До 100% |
|------|---------|---------|
| **Фронт** | `PageState` empty/error/degraded; health indicator; PWA/OG; mobile (E7 checklist) | Visual regression; full orphan routes |
| **Бэк** | `/health/all` | — |
| **Связь** | `healthStore` poll | — |

**Быстро → дорого:** пройти smoke checklist E7 → Playwright visual baseline → audit orphan routes.

---

## Топ backlog по «быстрому эффекту» (сквозной)

| Приоритет | Действие | Затраты | Поднимает |
|-----------|----------|---------|-----------|
| 1 | MinIO delete в `purge_downstream_refs` | S | Удаление документа 65→90% |
| 2 | Runtime `ingestion_complete` hook | S | Уведомления 55→75% |
| 3 | Server audit CSV endpoint | S | Audit 68→85% |
| 4 | Search → тот же hybrid path, что query | S | Поиск 83→92% |
| 5 | Обновить `domains/retrieval.md` под код | S | Документация / доверие |
| 6 | `interest_match` после save interests | M | Профиль + уведомления |
| 7 | JSON-LD через orchestrator+model | M | Export formats 20→60% |
| 8 | Playwright `@stack` в CI (nightly) | M | E2E 60→80% |
| 9 | Qdrant/MinIO backup scripts | M | Ops 40→70% |
| 10 | Live eval artifact + policy | M | Quality 25→70% |
| 11 | Full corpus SourceSpan review | L (`blocked_by_data`) | Gold dataset 30→90% |
| 12 | Orchestrator god-service split | L (deferred) | Maintainability |
| 13 | Cloud deploy / IaC | XL | Hosting 0→100% |

---

## Итог по зрелости продукта

**Ядро MVP (~85% чеклиста)** работает end-to-end: compose → seed → чат с evidence → RBAC → export MD/JSON через orchestrator. Этапы **E0–E7** закрыты в рамках no-live gates.

Главные разрывы до «100% production»:

- микросервисы **export/notification** как отдельные HTTP-сервисы — заглушки (логика в orchestrator/gateway);
- **live quality** — `blocked_by_policy`;
- **full corpus** — `blocked_by_data`;
- **MinIO purge**, **runtime notifications**, **stack E2E в CI**, **backup Qdrant/MinIO**.

---

## Закрытие MVP на 100%

Определение MVP — [`mvp.md`](../tz/mvp.md): команда проходит **полный end-to-end без ручных правок в БД и консоли** в момент демо.

Сейчас чеклист MVP закрыт примерно на **85%**. Ниже — что именно нужно довести до 100% **для MVP** (не для полного production). Top-1 фичи, cloud deploy, JSON-LD/PDF и отдельные microservices **не входят** в MVP, если явно не требуются в `mvp.md`.

### Критерий готовности MVP

| # | Требование MVP | Сейчас | Что сделать для 100% |
|---|----------------|--------|----------------------|
| M1 | Стек поднимается одной командой | ✅ | Зафиксировать в runbook: `cp .env.example .env` → `generate_auth_keys` → `docker compose up --build --wait` → все health green |
| M2 | UI работает с real API, не mock | ⚠️ | В demo/compose по умолчанию `VITE_USE_MOCK=false`; smoke: чат, source link, export без mock layer |
| M3 | Полный ingestion pipeline | ✅ | Прогнать upload ZIP на чистом стеке; убедиться, что stages в UI совпадают с orchestrator task |
| M4 | Claims в Neo4j, chunks в Qdrant | ✅ | После seed: `seed_inventory.py --mode offline` — counts > 0 для graph и vectors |
| M5 | Query IR + hybrid retrieval + fusion | ⚠️ | Прогнать 4 official questions; в `retrieval_trace` видны каналы dense/lexical/table/graph; исправить `/search`, если для MVP нужен тот же hybrid |
| M6 | Geo/numeric/time constraints | ⚠️ | На official-001/003/004: QueryIR парсит constraints; Qdrant `build_filter` применяет geo/numeric/time; ответ не выдумывает числа без `SourceSpan` |
| M7 | Ответ в UI: таблица, источники, локальный граф | ✅ | E2E smoke: клик по source → highlight; LocalGraph не пустой при наличии subgraph |
| M8 | ≥4 официальных вопроса с источниками | ⚠️ | Live eval на demo corpus + **pinned artifact** в репозитории; каждая ключевая строка с citation |
| M9 | Unsupported claims помечены | ✅ | UI: candidate vs confirmed; reason codes в `AnswerRenderer` |
| M10 | Роли + access policy | ⚠️ backend ✅ | Demo: external partner не видит confidential; **без RoleSwitcher** в prod path — только JWT login |
| M11 | Audit log | ✅ | Запрос, source view, export пишут audit; AdminAuditPage показывает события |
| M12 | Export Markdown/JSON | ⚠️ | Server path `POST /api/export` с evidence; без client-only fallback в demo mode |
| M13 | Воспроизводимый seed | ✅ | `make seed` / `seed_demo.py` на clean volumes без ручных SQL |
| M14 | Активный dictionary перед query | ⚠️ | Seed активирует dictionary; query без active dict даёт понятную ошибку в UI |

### Подробный план закрытия MVP (по блокам)

#### Блок A. Демо без ручных вмешательств (M1, M13, M14)

**Термины:**

- **Docker Compose** — описание всех контейнеров (БД, сервисы, UI) в одном файле; одна команда поднимает весь стек.
- **Healthcheck** — периодическая проверка «сервис жив»; compose ждёт green status перед зависимыми сервисами.
- **Seed** — скрипт начального наполнения: пользователи, demo-документы, индексы Neo4j/Qdrant, активный dictionary.

**Что сделать:**

1. Документировать и проверить сценарий **clean demo**: новые volumes → compose up → seed → 4 official questions без `docker exec` и ручного SQL.
2. Убедиться, что **active dictionary** создаётся seed'ом и активируется автоматически; в UI при отсутствии — явное сообщение, не пустой чат.
3. Добавить в CI (или pre-demo checklist) команду `python scripts/seed_inventory.py --mode offline` после seed — counts совпадают с ожиданием.

**Acceptance:** любой член команды на чистой машине повторяет demo по runbook за &lt;30 мин без правок в БД.

---

#### Блок B. Real API path в UI (M2, M10, M12)

**Термины:**

- **`VITE_USE_MOCK`** — флаг сборки UI: `false` = все запросы идут на gateway; `true` = локальные fake-ответы.
- **JWT session** — вход по логину/паролю, токен в заголовке; роль берётся с сервера, не из dev-переключателя.
- **RoleSwitcher** — dev-only переключатель ролей; в MVP demo не должен подменять реальный RBAC.

**Что сделать:**

1. В `docker-compose` для demo: `VITE_USE_MOCK=false`, реальные `VITE_AUTH_*` или login form.
2. Прогнать smoke: login → chat → source → export → search под ролями admin / researcher / external_partner.
3. Export только через **`POST /api/export`** (orchestrator); отключить client-side export fallback в production build.
4. Проверить `tests/integration/test_access_leak.py` — **access leak rate = 0** для external partner.

**Acceptance:** демо проходит на mock=false; external partner не видит restricted evidence в чате, поиске и export.

---

#### Блок C. Retrieval и качество ответов (M5, M6, M8)

**Термины:**

- **Query IR** (*Query Intermediate Representation*) — структурированное представление вопроса: сущности, geo/numeric/time constraints, лимиты; строится model service.
- **Hybrid retrieval** — поиск по нескольким каналам: dense vector (семантика), lexical (токены), table rows, graph evidence; затем **fusion** — объединение и дедупликация по `source_span_id`.
- **`retrieval_trace`** — JSON в ответе query: сколько кандидатов с каждого канала, какие фильтры применены; нужен для отладки и eval.
- **Pinned live eval artifact** — зафиксированный отчёт `eval/reports/*.json` после прогона 4 official questions на поднятом стеке с Yandex (или явный degraded mode); коммитится в репо как эталон качества.
- **`SourceSpan`** — точная ссылка на фрагмент документа (страница, offset, table row); без неё факт не может быть confirmed.

**Что сделать:**

1. Прогнать **4 official questions** из `demo/official_questions.md` через `eval/run_eval.py` или UI на seeded stack.
2. Зафиксировать **pinned artifact**: ответы содержат citations на reviewed demo `SourceSpan` ids (уже есть для demo corpus в E2).
3. Для каждого official question проверить в trace: сработали нужные каналы; geo/numeric/time filters не игнорируются в Qdrant (`build_filter` в `qdrant_adapter.py`).
4. Если MVP требует поиск как часть demo — выровнять **`/api/search`** с hybrid path из `/v1/query` (сейчас search — только vector).
5. Обновить `domains/retrieval.md` и `mvp.md` checklist — убрать устаревшие «fusion нет», если код подтверждён eval.

**Acceptance:**

- `python eval/offline_quality_gate.py` → official SourceSpan + QueryIR constraints **pass**;
- один **live eval report** в `eval/reports/` (после разрешения live policy) или явный team sign-off на deterministic fallback для demo;
- на demo каждый official question: ключевые утверждения со ссылкой на источник в UI.

---

#### Блок D. Evidence-first в UI (M7, M9)

**Термины:**

- **Confirmed claim** — утверждение с привязанным `SourceSpan` и прошедшее synthesis filter.
- **Candidate / unsupported** — гипотеза без достаточного evidence; показывается с **reason code** (почему не подтверждено).
- **Evidence table** — таблица найденных фрагментов с relevance score и ссылками на source viewer.

**Что сделать:**

1. E2E: из ответа чата клик по citation → source panel с highlight (или locked 403 для partner).
2. Убедиться, что gaps и conflicts отображаются в `AnswerRenderer`, а не скрываются.
3. Vitest/Playwright: сценарий «unsupported не рендерится как confirmed».

**Acceptance:** на official questions UI показывает таблицу evidence, граф (если есть subgraph), явные gaps для слабых мест.

---

#### Блок E. Export и audit (M11, M12)

**Термины:**

- **Export job** — запись в orchestrator PG: запрос экспорта query run в Markdown/JSON с повторной проверкой access к sources.
- **Audit event** — append-only лог действий: query_created, source_viewed, export_completed.

**Что сделать:**

1. Из чата: Export MD/JSON → файл содержит answer, evidence table, source ids, `QueryIR`, warnings.
2. Export под external partner **не включает** restricted sources (тест `test_export_query_run_fails_when_source_access_changed`).
3. В Admin Audit видны события запроса и экспорта.

**Acceptance:** export MD/JSON server-side на demo без client fallback; audit полный для demo-сценария.

---

### Что НЕ блокирует MVP 100%, но часто путают с MVP

| Item | Почему не MVP | Когда нужен |
|------|---------------|-------------|
| `services/export` как отдельный HTTP microservice | MVP допускает export через orchestrator | Масштабирование async jobs |
| `services/notification` microservice | Список/read уведомлений уже в gateway | Отдельная команда notifications |
| JSON-LD / PDF export | В MVP — Markdown/JSON | Top-1 / интеграции |
| Full corpus reviewed `SourceSpan` | MVP — 4 official + demo corpus | Production regression на всём корпусе |
| Live latency p95 | Не в MVP DoD | SLA production |
| Cloud / HTTPS | Локальный compose достаточен для MVP demo | Публичный стенд |
| MinIO delete on purge | MVP demo редко удаляет документы | Production data lifecycle |
| Orchestrator god-service refactor | Работает, техдолг | Долгосрочная эволюция |

---

### Минимальный чеклист «MVP 100% готов» (одна страница)

Выполнить на **чистом стеке** одним оператором:

- [ ] `docker compose up --build --wait` — все сервисы healthy
- [ ] `make seed` (или documented seed) — dictionary active, Neo4j/Qdrant counts > 0
- [ ] Login JWT (не RoleSwitcher) под admin, researcher, external_partner
- [ ] Official question 1–4 в чате — ответ с sources, без ручных правок БД
- [ ] Source click → highlight или 403 для partner
- [ ] Search с geo/year filter — результаты согласованы с access
- [ ] Export JSON server-side — evidence + audit event
- [ ] `python eval/offline_quality_gate.py` — pass/warn без silent fail
- [ ] (После live policy) pinned live eval artifact в `eval/reports/` или signed degraded demo

**Вердикт MVP 100%:** все пункты чеклиста зелёные; нет открытых ⚠️ в [`mvp.md`](../tz/mvp.md) checklist для обязательного pipeline и 4 official questions.

---

### Порядок работ (быстро → долго) именно для MVP

| Шаг | Задача | Оценка | Закрывает |
|-----|--------|--------|-----------|
| 1 | Runbook clean demo + seed inventory gate | S | M1, M13, M14 |
| 2 | Compose `VITE_USE_MOCK=false` + JWT demo users | S | M2, M10 |
| 3 | Export server-only path в demo build | S | M12 |
| 4 | Smoke 4 official questions + обновить mvp.md checklist | S | M5, M8 |
| 5 | Search hybrid parity (если search в demo) | S | M5 |
| 6 | E2E Playwright `@stack` сценарий official-001 | M | M7, M8 |
| 7 | Live eval + pin artifact (при разрешении Yandex) | M | M8 |
| 8 | Синхронизация domain docs с кодом retrieval | S | M5, M6 |

После шагов 1–6 MVP можно считать **функционально 100%** для no-live demo. Шаг 7 — **качественное** подтверждение ответов на live models, отдельно от функционального DoD.
