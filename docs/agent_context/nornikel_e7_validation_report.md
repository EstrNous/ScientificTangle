# НорСинтез E7: validation report (Validator)

**Дата:** 2026-07-04  
**Ветка:** `feat/nornikel-e7-validator`  
**Этап:** E7 — Production polish  
**База:** `origin/dev` @ `a852fd9` (после merge PR #98, #99, #100)

Связанные документы:

- [`nornikel_parallel_execution_plan.md`](nornikel_parallel_execution_plan.md)
- [`nornikel_e6_validation_report.md`](nornikel_e6_validation_report.md) — blockers E6→E7
- [`nornikel_e7_db_ops_ownership.md`](nornikel_e7_db_ops_ownership.md) — Databases deliverable
- [`nornikel_e7_db_ops_runbook.md`](nornikel_e7_db_ops_runbook.md) — Databases ops runbook
- [`nornikel_e7_bml_operator_runbook.md`](nornikel_e7_bml_operator_runbook.md) — Backend/ML operator runbook
- [`nornikel_e7_bml_readiness_summary.md`](nornikel_e7_bml_readiness_summary.md) — Backend/ML final no-live readiness
- [`nornikel_e7_fe_polish_checklist.md`](nornikel_e7_fe_polish_checklist.md) — Frontend polish checklist

---

## 1. Merge gate

| PR | Ветка | Merge в `dev` | Артефакт |
|----|-------|---------------|----------|
| #98 | `feat/nornikel-e7-bml-runbooks` | да (`e737c18`) | operator runbook, final no-live readiness summary |
| #99 | `feat/nornikel-e7-db-ops-docs` | да (`7292470`) | DB ops ownership, storage runbook, `project_structure.md` (DB) |
| #100 | `feat/nornikel-e7-fe-polish` | да (`a852fd9`) | health indicator, PWA/OG, `PageState`, polish checklist |

**Вердикт:** gate E7 для ролей Databases, Backend/ML, Frontend — **pass**. Validator может закрывать этап.

---

## 2. Проверки Validator gate (план E7)

| Критерий | Результат | Детали |
|----------|-----------|--------|
| DB ops docs: ownership, migrations, backup/restore, retention | **pass** | `nornikel_e7_db_ops_ownership.md`, `nornikel_e7_db_ops_runbook.md` |
| Operator runbook + honest no-live readiness | **pass** | `nornikel_e7_bml_operator_runbook.md`, readiness `warn` |
| UI polish: empty/error/degraded, health, PWA/OG, demo labels | **pass (code)** | `PageState`, `ServiceHealthIndicator`, `manifest.webmanifest`, OG meta |
| `project_structure.md` отражает новые E7 docs | **pass (fix)** | добавлены BML/FE entries валидатором |
| `README.md` без изменений | **pass** | E7 PR не меняли README |
| Final no-live readiness honest | **pass** | `overall_status: warn`; live checks → `blocked_by_policy` |
| Live model tasks только как deferred | **pass** | readiness summary §Deferred live-model tasks |
| Feature work post-E7 / live plan | **pass** | не в E7 merges |
| God object `orchestrator/.../service.py` | **pass** | не трогался валидатором |

---

## 3. Quality checks

| Проверка | Результат | Примечание |
|----------|-----------|------------|
| `ruff check shared services scripts tests` | **warn** | 20 pre-existing I001/F401 (B-E7-06); не E7 regressions |
| `$env:COVERAGE='1'; $env:COVERAGE_FAIL_UNDER='60'; python scripts/run_tests.py` | **pass** | all backend suites; aggregate coverage **61%** |
| `pytest tests/integration/test_demo_quality_gate.py tests/e2e/test_official_questions_smoke.py tests/performance/test_seed_inventory.py` | **pass** | 6 passed, 1 skipped |
| `python eval/demo_quality_gate.py` | **pass (blocked overall)** | `live_eval_report` → `blocked_by_policy` |
| `python eval/offline_quality_gate.py` | **pass (warn)** | `overall_status: warn`; live → `blocked_by_policy`; full corpus → `blocked_by_data` |
| `git diff --check` | **pass** | на ветке валидатора |
| `cd ui && npm ci && npm test && npm run build && npm run lint` | **skipped** | `npm` отсутствует в PATH |
| Playwright `@offline` / `@stack` e2e | **skipped** | нет npm / поднятого stack |
| `make reset-reseed` / `seed_inventory --include-remote` | **skipped** | PostgreSQL/Docker stack недоступен |
| Yandex live smoke | **blocked_by_policy** | план E0–E7 |
| Live eval / answer quality / latency p95 | **blocked_by_policy** | план E0–E7 |

### Spot-checks по E7 deliverables

| Claim | Проверка | Результат |
|-------|----------|-----------|
| Gateway `/health/all` endpoint | `services/gateway/app/api/health.py` | **pass** |
| UI health poll в production mode | `healthStore.js`, `DashboardLayout.jsx` | **pass** |
| Health indicator скрыт в mock mode | `ServiceHealthIndicator`, `useMock` guard | **pass** |
| PWA manifest + OG/Twitter meta | `manifest.webmanifest`, `index.html` | **pass** |
| Logo alt «НорСинтез» | `AppLogo.jsx` | **pass** |
| Empty/error states на product pages | `PageState` в chat/search/review/admin/audit/upload | **pass** |
| Grep: no `api/mock` в production components | только `*.test.*` boundary | **pass** (наследие E4) |
| Export JSON-LD/PDF backlog honest | E5 + E7 readiness | **pass** |
| Retention/cleanup policies verified | E7 ownership §7 | **pass** (manual purge documented) |
| Qdrant/MinIO backup runbooks | E7 DB runbook + E6 gaps cross-ref | **pass (documented gaps)** |

---

## 4. Закрытие E6 blockers в E7

| E6 blocker | E7 статус |
|------------|-----------|
| B-E7-01 Qdrant / MinIO backup-restore runbooks | **closed (documented)** — ops runbook + `mc mirror` recommendation; automated backup still open |
| B-E7-02 MinIO object delete при document purge | **open** — product-flow risk |
| B-E7-03 Runtime `ingestion_complete` / `interest_match` delivery | **open** — backlog в readiness summary |
| B-E7-04 Server-side audit CSV download | **open (optional)** — UI client-only path |
| B-E7-05 Retrieval source identity drift | **open** — `blocked_by_data` / BML backlog |
| B-E7-06 Pre-existing `ruff` I001/F401 | **open** — 20 issues |
| B-E6-04 `source_opened` vs `source_viewed` naming | **open** — оба alias в storage/UI; унификация не выполнена |
| B-E3-DATA-01 Full corpus reviewed `SourceSpan` ids | **blocked_by_data** (без изменений) |
| Scheduled export/notification purge jobs | **open** — documented manual ops only |

---

## 5. Deferred live-model tasks (post-E7)

Эти задачи **не входят** в E0–E7 и остаются `blocked_by_policy` до отдельного разрешения команды:

| Task | Статус |
|------|--------|
| Yandex live smoke | `blocked_by_policy` |
| Live eval official questions | `blocked_by_policy` |
| Live eval corpus regression suite | `blocked_by_policy` |
| Generated final answer quality | `blocked_by_policy` |
| Live p50/p95 latency | `blocked_by_policy` |
| Comparison offline vs live reports | `blocked_by_policy` |
| Live model prompt/model tuning claims | `blocked_by_policy` |
| God object refactor `orchestrator/.../service.py` | deferred (External Orchestrator Refactor Owner) |

---

## 6. Мелкие интеграционные исправления (Validator)

| Fix | Файл | Причина |
|-----|------|---------|
| Парсинг `/health/all` при HTTP 503 | `ui/src/api/health.js`, `health.test.js` | gateway возвращает peers в теле 503; axios бросал ошибку до парсинга |
| Индексация E7 BML/FE docs | `docs/agent_context/project_structure.md` | DB PR добавил только DB entries; BML/FE deliverables не были в структуре |

---

## 7. Итог

| Вопрос | Ответ |
|--------|-------|
| E7 production polish / ops handoff complete? | **да** — docs, runbooks, UI polish merged |
| No-live readiness honest? | **да** — `warn`, без live claims |
| Можно начинать post-E7 live-model plan? | **только после отдельного разрешения команды** |
| Live quality | **blocked_by_policy** |
| Offline quality overall | **warn** (ожидаемо: `blocked_by_data` для full corpus) |
| Validator PR ready? | **да** — `feat/nornikel-e7-validator` |

**Вердикт этапа E7:** **pass** (финальный no-live handoff: ops docs, runbooks, UI polish; live quality и full corpus — deferred).
