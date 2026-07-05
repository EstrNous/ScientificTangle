# НорСинтез E5: validation report (Validator)

**Дата:** 2026-07-04  
**Ветка:** `feat/nornikel-e5-validator`  
**Этап:** E5 — Export, Notifications, Audit  
**База:** `origin/dev` @ `ee6176f` (после merge PR #89, #90, #91)

Связанные документы:

- [`nornikel_parallel_execution_plan.md`](nornikel_parallel_execution_plan.md)
- [`nornikel_e4_validation_report.md`](nornikel_e4_validation_report.md) — blockers E4→E5
- [`nornikel_e5_db_storage_ownership.md`](nornikel_e5_db_storage_ownership.md) — Databases deliverable
- [`nornikel_e5_bml_export_notifications_boundary.md`](nornikel_e5_bml_export_notifications_boundary.md) — Backend/ML boundary

---

## 1. Merge gate

| PR | Ветка | Merge в `dev` | Артефакт |
|----|-------|---------------|----------|
| #89 | `feat/nornikel-e5-db-product-events` | да (`7f371a9`) | migration `0012`, notification `0004`, `e5_fixtures`, `product_events_storage` |
| #90 | `feat/nornikel-e5-bml-export-notifications` | да (`f71935e`) | orchestrator `POST /export`, conflict notifications, audit events, boundary doc |
| #91 | `feat/nornikel-e5-fe-export-notifications` | да (`ee6176f`) | ExportPanel server path, NotificationBell poll/refresh, AdminAuditPage filters/CSV/drill-down, eval summary UI |

**Вердикт:** gate E5 для ролей Databases, Backend/ML, Frontend — **pass**. Validator может закрывать этап.

---

## 2. Проверки Validator gate (план E5)

| Критерий | Результат | Детали |
|----------|-----------|--------|
| Export JSON/Markdown содержит evidence | **pass** | `_export_document` + `_resolve_export_sources`; `test_export_query_run_returns_markdown_for_completed_run` |
| Нет restricted sources для external partner при export | **pass** | повторный source resolve с `access_roles`; `test_export_query_run_fails_when_source_access_changed` → `access_denied` audit |
| Notification после offline-triggered event (не seed-only) | **pass (partial)** | `conflict_detected` из chat/query conflicts (`test_conflict_notification_uses_query_run_reference_and_match_payload`); `ingestion_complete` / `interest_match` runtime — backlog |
| `GET /notifications?since=` | **pass** | gateway `notifications.py` + `NotificationService.list_notifications`; UI poll в `NotificationBell` |
| Audit events: filters + pagination | **pass** | `list_audit_events` offset/limit/action; `AdminAuditPage` PAGE_SIZE + load more; `test_list_audit_events_forwards_filters_to_orchestrator` |
| Audit CSV export | **pass (client)** | `downloadAuditCsv` + UI button; server `audit_csv_exports` storage готов, UI использует client-side CSV |
| Audit drill-down run/source/document | **pass** | `resolveAuditEventTarget`, `auditNavigation.test.js` |
| PDF / JSON-LD честно unavailable | **pass** | `format_status`: jsonld/pdf = backlog; ExportPanel disabled JSON-LD + PDF server unavailable |
| ExportPanel `POST /api/export` в production | **pass** | `requestExport` → `/export`; client fallback только за flag |
| EvaluationDashboard / eval summary из backend | **pass** | `fetchEvalReportSummary` → `/eval/report/summary`; pinned/offline `blocked_by_data` без hardcoded analytics |
| Feature work E6+ | **pass** | seed reliability, offline e2e, CI gates — не в E5 merges |
| God object `orchestrator/.../service.py` | **pass** | не трогался валидатором |

---

## 3. Quality checks

| Проверка | Результат | Примечание |
|----------|-----------|------------|
| `pytest services/orchestrator/tests/test_e5_*.py test_audit_api.py` + targeted export/audit in `test_query_service.py` | **pass** | 14 passed |
| `pytest services/gateway/tests/test_notification_service.py test_chat_service.py test_query.py test_admin_service.py` | **pass** | 10 passed |
| `pytest services/gateway/tests/test_openapi.py test_analytics_service.py` | **pass** | 10 passed |
| `pytest tests/integration/test_access_leak.py test_eval_runner.py test_demo_quality_gate.py` | **pass** | 11 passed |
| `python eval/demo_quality_gate.py` | **pass (blocked overall)** | pinned sha256 match; `live_eval_report` → `blocked_by_policy` |
| `git diff --check` | **pass** | на ветке валидатора (без локальных Makefile правок) |
| `cd ui && npm test` / `npm run build` | **skipped** | `npm` отсутствует в PATH; Docker `npm ci` → `ECONNRESET` |
| `make test-ui-docker` (vitest product/export/audit) | **skipped** | сеть Docker/npm registry |
| Live `alembic upgrade` + `seed_e5_fixtures.py` на PostgreSQL | **skipped** | нет seeded stack в среде валидатора |
| Full-stack `VITE_USE_MOCK=false` smoke | **skipped** | нет UI build + backend stack |
| Yandex live smoke | **blocked_by_policy** | план E0–E7 |
| Live eval / answer quality / latency p95 | **blocked_by_policy** | план E0–E7 |

### Spot-checks по E5 deliverables

| Claim | Проверка | Результат |
|-------|----------|-----------|
| Export boundary orchestrator-owned | `nornikel_e5_bml_export_notifications_boundary.md`, migration `0012` | **pass** |
| MinIO metadata для export artifacts | `e5_fixtures` validator, `EXPORTS_BUCKET_NAME` | **pass** |
| Product audit actions в fixtures | `test_product_audit_actions_cover_fixture_events` | **pass** |
| Audit CSV serialization | `test_audit_events_to_csv_contains_header_and_rows` | **pass** |
| Notification indexes для incremental poll | `test_e5_notification_storage_migration_revision_chain` | **pass** |
| Conflict notification payload | `reference_type=query_run`, match fields | **pass** |
| JSON-LD/PDF backlog в export | `_export_format_status`, ExportPanel UI | **pass** |
| Grep: no `api/mock` в production components | только `*.test.*` boundary | **pass** (наследие E4, без регрессии) |
| Eval UI без live claims | `blockedChecks` / `blocked_by_data` states | **pass** |

---

## 4. Закрытие E4 blockers в E5

| E4 blocker | E5 статус |
|------------|-----------|
| B-E5-01 Product notification events без seed-only | **partial** — `conflict_detected` из query; `ingestion_complete` / `interest_match` runtime delivery — open |
| B-E5-02 Notification cursor/`since` в gateway API | **closed** — `GET /notifications?since=` |
| B-E5-03 MinIO object delete в document purge | **open** — `purge_downstream_refs` без MinIO |
| B-E5-04 Notification click `reference_type=document` | **partial** — UI открывает source по document id; document-level resolve не гарантирован |
| B-E5-05 Authoritative export boundary | **closed** — orchestrator inline export + jobs/artifacts storage |
| B-E5-06 Audit pagination/CSV export | **closed** — offset pagination + client CSV; server CSV storage готов |
| B-E3-DATA-01 Full corpus reviewed `SourceSpan` ids | **blocked_by_data** (без изменений) |

---

## 5. Blockers и dependencies перед E6

### Blockers

| ID | Blocker | Owner | Этап |
|----|---------|-------|------|
| B-E6-01 | MinIO object delete при document purge | BML | E6/E7 |
| B-E6-02 | Runtime `ingestion_complete` / `interest_match` без seed-only (межсервисный event delivery) | BML | E6 |
| B-E6-03 | Server-side audit CSV download endpoint (storage есть, UI — client-only) | BML + FE | E6 (optional) |
| B-E6-04 | `source_opened` vs `source_viewed` naming в audit filters/docs | BML + FE | E7 polish |
| B-E6-05 | Retrieval source identity drift (`document_id` vs span id) | BML | E6 (`top1_e5_bm1_integration_eval.md`) |
| B-E3-DATA-01 | Full corpus normalized `SourceSpan` ids | BML + data | `blocked_by_data` |

### Dependencies

| ID | Dependency | Этап |
|----|------------|------|
| D-E6-01 | Clean seed/reset + repeatable counts report | E6 DB |
| D-E6-02 | Offline official scenario suite + `demo_quality_gate` CI | E6 BML |
| D-E6-03 | Playwright/e2e с `VITE_USE_MOCK=false` | E6 FE |
| D-E6-04 | Active dictionary preflight в live eval runbook | E6 BML |
| D-E7-01 | Retention/cleanup runbooks для export artifacts | E7 DB |

### Не входит в Validator / E5

| Item | Статус |
|------|--------|
| God object refactor `orchestrator/.../service.py` | deferred (External Orchestrator Refactor Owner) |
| Live model eval | `blocked_by_policy` |
| `services/export` как отдельный HTTP сервис | backlog до решения команды |

---

## 6. Мелкие интеграционные исправления (Validator)

Мелких дефектов этапа E5, требующих правки кода валидатором, не обнаружено. Все targeted offline/integration тесты проходят на `origin/dev` @ `ee6176f`.

---

## 7. Итог

| Вопрос | Ответ |
|--------|-------|
| E5 export/notification/audit product flows complete? | **да** — с partial на ingestion/interest runtime notifications и MinIO purge |
| Можно начинать E6? | **да** — offline quality / seed / e2e gate |
| Live quality | **blocked_by_policy** |
| External partner export leak smoke | **pass** (offline unit/integration) |
| Validator PR ready? | **да** — `feat/nornikel-e5-validator` |

**Вердикт этапа E5:** **pass** (export/notification/audit productization merged; offline CI/e2e — E6).
