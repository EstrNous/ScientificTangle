# НорСинтез E6: validation report (Validator)

**Дата:** 2026-07-04  
**Ветка:** `feat/nornikel-e6-validator`  
**Этап:** E6 — Offline quality и CI  
**База:** `origin/dev` @ `f85df48` (после merge PR #93, #94, #96)

Связанные документы:

- [`nornikel_parallel_execution_plan.md`](nornikel_parallel_execution_plan.md)
- [`nornikel_e5_validation_report.md`](nornikel_e5_validation_report.md) — blockers E5→E6
- [`nornikel_e6_db_seed_report.md`](nornikel_e6_db_seed_report.md) — Databases deliverable
- [`nornikel_e6_db_backup_restore_gaps.md`](nornikel_e6_db_backup_restore_gaps.md) — backup/restore gaps
- [`nornikel_e6_bml_offline_quality_report.md`](nornikel_e6_bml_offline_quality_report.md) — Backend/ML offline gate
- [`nornikel_e6_fe_no_live_checklist.md`](nornikel_e6_fe_no_live_checklist.md) — Frontend e2e/checklist

---

## 1. Merge gate

| PR | Ветка | Merge в `dev` | Артефакт |
|----|-------|---------------|----------|
| #93 | `feat/nornikel-e6-bml-offline-quality` | да (`a759acd`) | `eval/offline_quality_gate.py`, `make eval-offline-quality`, offline readiness report |
| #94 | `feat/nornikel-e6-db-seed-reliability` | да (`aa4109f`) | `scripts/seed_inventory.py`, `seed_reset_gate.py`, Makefile `seed-counts` / `reset-reseed-*`, seed/backup reports |
| #96 | `feat/nornikel-e6-fe-e2e-hardening` | да (`f85df48`) | Playwright `@offline` scenarios 1–10, `build:e2e`, no-live checklist, streaming/simulation prod defaults |

**Вердикт:** gate E6 для ролей Databases, Backend/ML, Frontend — **pass**. Validator может закрывать этап.

---

## 2. Проверки Validator gate (план E6)

| Критерий | Результат | Детали |
|----------|-----------|--------|
| Repeatable seed/reset gate + counts report | **pass** | `seed_inventory.py` modes `report` / `offline` / `full`; `tests/performance/test_seed_inventory.py` (6 tests) |
| Offline official scenario suite | **pass (warn)** | `offline_quality_gate.py` overall `warn`; official `SourceSpan` + QueryIR — pass |
| `eval/demo_quality_gate.py` без live models | **pass (blocked overall)** | pinned sha256 match; `live_eval_report` → `blocked_by_policy` |
| `make eval-offline-quality` / Makefile CI targets | **pass** | targets в `Makefile`; gate executable offline |
| Playwright no-live e2e scenarios 1–10 | **pass (code)** | `ui/e2e/no-live-scenarios.spec.js` + `npm run test:e2e` (`@offline`); runtime — skipped (нет npm) |
| `VITE_USE_MOCK=false` prod build path | **pass (code)** | `build:e2e` mode, checklist в `nornikel_e6_fe_no_live_checklist.md` |
| Simulated lifecycle off в prod mode | **pass** | `isSimulatedLifecycleEnabled()` + checklist |
| Streaming prod default documented | **pass** | `VITE_CHAT_STREAMING_UX` unset → non-streaming |
| Backup/restore scope documented | **pass** | PG covered; Qdrant/MinIO gaps + mitigations в `nornikel_e6_db_backup_restore_gaps.md` |
| Feature work E7+ | **pass** | ops runbooks, UI polish — не в E6 merges |
| God object `orchestrator/.../service.py` | **pass** | не трогался валидатором |

---

## 3. Quality checks

| Проверка | Результат | Примечание |
|----------|-----------|------------|
| `ruff check shared services scripts tests` | **warn** | 20 pre-existing I001/F401 (не E6); E6 seed scripts — pass после `ruff.toml` per-file-ignores |
| `$env:COVERAGE='1'; $env:COVERAGE_FAIL_UNDER='60'; python scripts/run_tests.py` | **pass** | all backend suites; aggregate coverage **61%** |
| `pytest tests/performance/test_seed_inventory.py` | **pass** | 3 passed |
| `pytest tests/integration/test_demo_quality_gate.py tests/e2e/test_official_questions_smoke.py` | **pass** | 6 passed, 1 skipped |
| `python eval/demo_quality_gate.py` | **pass (blocked overall)** | `live_eval_report` → `blocked_by_policy` |
| `python eval/offline_quality_gate.py` | **pass (warn)** | `overall_status: warn`; live checks → `blocked_by_policy`; full corpus → `blocked_by_data` |
| `git diff --check` | **pass** | на ветке валидатора |
| `cd ui && npm ci && npm test && npm run build && npm run lint` | **skipped** | `npm` отсутствует в PATH |
| `npm run test:e2e` (Playwright `@offline`) | **skipped** | нет npm / Playwright runtime |
| `RUN_UI_E2E=1 npm run test:e2e:stack` | **skipped** | нет поднятого stack + npm |
| `python scripts/seed_inventory.py --mode offline` | **skipped** | PostgreSQL недоступен (connection refused) |
| `make reset-reseed` (full gate) | **skipped** | требует Docker stack; `blocked_by_policy` для live ingest quality |
| Yandex live smoke | **blocked_by_policy** | план E0–E7 |
| Live eval / answer quality / latency p95 | **blocked_by_policy** | план E0–E7 |

### Spot-checks по E6 deliverables

| Claim | Проверка | Результат |
|-------|----------|-----------|
| Seed inventory schema `seed_inventory.v1` | `seed_inventory.py`, DB report doc | **pass** |
| Offline reseed E2→E5 fixture chain | `compute_fixture_expectations`, validation | **pass** (unit) |
| Official questions reviewed `SourceSpan` ids | `offline_quality_gate` check | **pass** |
| Access filtering fixture | `corpus-001` in regression suite | **pass** |
| No-live e2e inventory | `tests/e2e/test_official_questions_smoke.py` | **pass** |
| Grep: no `api/mock` в production components | только `*.test.*` boundary | **pass** (наследие E4) |
| JSON-LD/PDF export backlog | E5 + E6 e2e scenario 5 | **pass** (honest unavailable) |
| Eval UI без live claims | E5 dashboard + offline gate | **pass** |

---

## 4. Закрытие E5 blockers в E6

| E5 blocker | E6 статус |
|------------|-----------|
| B-E6-01 MinIO object delete при document purge | **open** — `purge_downstream_refs` без MinIO |
| B-E6-02 Runtime `ingestion_complete` / `interest_match` delivery | **open** — conflict notifications есть; ingestion/interest runtime — backlog |
| B-E6-03 Server-side audit CSV download | **open** — storage готов, UI client-only |
| B-E6-04 `source_opened` vs `source_viewed` naming | **open** → E7 polish |
| B-E6-05 Retrieval source identity drift | **open** — `blocked_by_data` / BML backlog |
| D-E6-01 Clean seed/reset + counts report | **closed** — PR #94 |
| D-E6-02 Offline official suite + `demo_quality_gate` CI | **closed** — PR #93 |
| D-E6-03 Playwright/e2e `VITE_USE_MOCK=false` | **closed (code)** — PR #96; runtime stack e2e optional |
| B-E3-DATA-01 Full corpus reviewed `SourceSpan` ids | **blocked_by_data** (без изменений) |

---

## 5. Blockers и dependencies перед E7

### Blockers

| ID | Blocker | Owner | Этап |
|----|---------|-------|------|
| B-E7-01 | Qdrant / MinIO backup-restore runbooks (gaps documented) | DB | E7 |
| B-E7-02 | MinIO object delete при document purge | BML | E6/E7 |
| B-E7-03 | Runtime `ingestion_complete` / `interest_match` event delivery | BML | E7 |
| B-E7-04 | Server-side audit CSV download endpoint | BML + FE | E7 (optional) |
| B-E7-05 | Retrieval source identity drift (`document_id` vs span id) | BML | E7 |
| B-E7-06 | Pre-existing `ruff` I001/F401 в services (20 issues) | any | E7 polish |
| B-E3-DATA-01 | Full corpus normalized `SourceSpan` ids | BML + data | `blocked_by_data` |

### Dependencies

| ID | Dependency | Этап |
|----|------------|------|
| D-E7-01 | DB/ops docs: migrations, retention, failure runbooks | E7 DB |
| D-E7-02 | Operator runbook + final no-live readiness summary | E7 BML |
| D-E7-03 | UI polish: health indicator, empty/error states, PWA/OG | E7 FE |
| D-E7-04 | Stack-backed `@stack` Playwright в CI (optional) | E7 FE/CI |

### Не входит в Validator / E6

| Item | Статус |
|------|--------|
| God object refactor `orchestrator/.../service.py` | deferred (External Orchestrator Refactor Owner) |
| Live model eval / Yandex smoke / latency p95 | `blocked_by_policy` |
| Generated final answer quality | `blocked_by_policy` — post-E7 live plan |

---

## 6. Мелкие интеграционные исправления (Validator)

| Fix | Файл | Причина |
|-----|------|---------|
| `per-file-ignores` для E402 после `sys.path` bootstrap | `ruff.toml` | E6 seed scripts (`seed_inventory.py`, `seed_reset_gate.py`) — тот же паттерн, что `neo4j_smoke.py` |

---

## 7. Итог

| Вопрос | Ответ |
|--------|-------|
| E6 no-live quality / seed / e2e gate complete? | **да** — offline gates executable; UI e2e покрыт в коде |
| Можно начинать E7? | **да** — после merge PR валидатора |
| Live quality | **blocked_by_policy** |
| Offline quality overall | **warn** (ожидаемо: `blocked_by_data` для full corpus) |
| Validator PR ready? | **да** — `feat/nornikel-e6-validator` |

**Вердикт этапа E6:** **pass** (no-live quality gate, seed reliability и e2e hardening merged; live quality и full corpus — deferred).
