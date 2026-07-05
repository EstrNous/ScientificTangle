# НорСинтез E3: validation report (Validator)

**Дата:** 2026-07-04  
**Ветка:** `feat/nornikel-e3-validator`  
**Этап:** E3 — User workflows  
**База:** `origin/dev` @ `0efaa0d` (после merge PR #81, #82, #83)

Связанные документы:

- [`nornikel_parallel_execution_plan.md`](nornikel_parallel_execution_plan.md)
- [`nornikel_e3_db_storage_ownership.md`](nornikel_e3_db_storage_ownership.md) — Databases (PR #81)
- [`nornikel_e2_validation_report.md`](nornikel_e2_validation_report.md) — blockers E2→E3

---

## 1. Merge gate

| PR | Ветка | Merge в `dev` | Артефакт |
|----|-------|---------------|----------|
| #81 | `feat/nornikel-e3-db-workflow-state` | да (`86600eb`) | migration `0010`, notification `0003`, workflow repositories, E3 fixtures |
| #82 | `feat/nornikel-e3-bml-workflow-wiring` | да (`514a451`) | `workflow.py`, interests/notifications/delete/review/admin APIs, cross-store purge |
| #83 | `feat/nornikel-e3-fe-workflows` | да (`0efaa0d`) | ProfilePage, NotificationBell, Upload/Admin delete+save, ReviewConsole actions |

**Вердикт:** gate E3 для ролей Databases, Backend/ML, Frontend — **pass**. Validator может закрывать этап.

---

## 2. Проверки Validator gate (план E3)

| Критерий | Результат | Детали |
|----------|-----------|--------|
| Interests save/load API + UI | **pass** | `GET/PUT /interests`, offline `/v1/interests/extract`, `interestsWorkflow.js`, ProfilePage |
| Notification list/poll/mark read | **pass** | `GET /notifications?since=`, read/read-all, NotificationBell incremental poll + i18n types |
| Delete document + error handling | **pass** | `DELETE /documents/{id}`, gateway proxy, Upload optimistic rollback, i18n `forbidden`/`not_found` |
| Admin save persistence | **pass** | `PATCH /admin/policies/{id}`, dirty state + per-row/save-all, audit event |
| Review decision wiring | **pass (after fix)** | gateway→orchestrator `/review/*`; UI mapper приведён к `ReviewDecisionPayload` |
| No direct live model calls в E3 wiring | **pass** | interests extract и notification matching — deterministic model endpoints |
| No production-only seed notifications | **partial** | runtime `ingestion_complete` hook не подключён; list/read работают с DB + seed/fixtures |
| Feature work E4+ | **pass** | RBAC runtime, mock cleanup, evidence/search — не в E3 merges |
| `services/orchestrator/app/service/service.py` god object | **pass** | не трогался валидатором; split PR #80 вне scope E3 |

---

## 3. Quality checks

| Проверка | Результат | Примечание |
|----------|-----------|------------|
| `pytest services/orchestrator/tests/test_e3_*.py` | **pass** | 9 passed |
| `pytest services/gateway/tests/test_documents.py test_notification_service.py test_admin_service.py test_openapi.py` | **pass** | 12 passed (с POST `/review/queue` assertion) |
| `pytest services/retrieval/tests/test_query_api.py` | **pass** | 3 passed (delete document index) |
| `pytest shared/tests/test_contracts.py tests/integration/test_reviewed_source_fixtures.py` | **pass** | 11 passed |
| `python eval/demo_quality_gate.py` | **pass (blocked overall)** | pinned sha256 match; live eval `blocked_by_policy` |
| `git diff --check` | **pass** | на ветке валидатора |
| `cd ui && npm test` / `npm run build` | **skipped** | `npm` отсутствует в PATH среды валидатора |
| Live `alembic upgrade` на PostgreSQL | **skipped** | нет Docker/PG в среде валидатора |
| E2E smoke interests→notification→delete (full stack) | **skipped** | нет поднятого стека в среде валидатора |
| Yandex live smoke | **blocked_by_policy** | план E0–E7 |
| Live eval / answer quality / latency p95 | **blocked_by_policy** | план E0–E7 |

### Spot-checks по E3 deliverables

| Claim | Проверка | Результат |
|-------|----------|-----------|
| Workflow storage `0010` + notification `0003` | `test_e3_storage_migration.py` | **pass** |
| E3 fixtures pack | `test_e3_fixtures.py`, `workflow_state.json` | **pass** |
| Review queue/decisions API | `workflow.py`, gateway `review.py` | **pass** |
| Delete cascade purge | retrieval `/v1/documents/{id}/index`, knowledge `/graph` | **pass** |
| Interests offline extract | `test_notification_service.py` mock model | **pass** |
| Admin PATCH + audit | `test_admin_service.py`, `workflow.py` | **pass** |
| UI review actions behind flag | `isReviewActionsEnabled()` | **pass** |
| Review decision DTO alignment | `productApi.js` serializer | **fixed** — было `candidate_id`/`approved`, контракт — `item_id`/`approve` |

---

## 4. Закрытие E2 blockers в E3

| E2 blocker | E3 статус |
|------------|-----------|
| B-E3-01 `GET/POST /api/review/*` wiring | **closed** |
| B-E3-02 `DELETE /api/documents/{id}` cross-store purge | **closed** |
| B-E3-03 Interests/notifications workflow APIs | **partial** — list/read/save OK; runtime event hooks — E5 |
| B-E3-04 Full raw corpus reviewed `SourceSpan` ids | **blocked_by_data** (без изменений) |

---

## 5. Blockers и dependencies перед E4

### Blockers

| ID | Blocker | Owner | Этап |
|----|---------|-------|------|
| B-E4-01 | Direct `api/mock/` import в `ReviewConsolePage` (`conflicts.json`) | FE | E4 |
| B-E4-02 | `SourcePayload` highlight fields в live resolver | BML | E4 |
| B-E4-03 | Notification click `reference_type=document` вызывает `/source/{document_id}` | FE + BML | E4 |
| B-E5-01 | Runtime `ingestion_complete` / interest_match без seed-only | BML | E5 |
| B-E5-02 | Notification cursor pagination в gateway (есть в `workflow_repository`, не в API) | BML | E5 |
| B-E5-03 | MinIO object delete в document purge | BML | E5 |
| B-E3-DATA-01 | Full corpus normalized `SourceSpan` ids | BML + data | `blocked_by_data` |

### Dependencies

| ID | Dependency | Этап |
|----|------------|------|
| D-E4-01 | Убрать mock catalog из production components | E4 FE |
| D-E4-02 | RBAC runtime + access_denied source panel | E4 |
| D-E5-01 | Product notification events from ingestion/review/query | E5 |
| D-E6-01 | Full seed/reset + offline e2e Playwright | E6 |

### Не входит в Validator / E3

| Item | Статус |
|------|--------|
| God object refactor `orchestrator/.../service.py` | deferred (External Orchestrator Refactor Owner) |
| Live model eval | `blocked_by_policy` |
| Pre-existing suite failures вне E3 scope | backlog |

---

## 6. Мелкие интеграционные исправления (Validator)

| Fix | Файл | Причина |
|-----|------|---------|
| Review decision serializer: `item_id`, `approve/reject/defer`, `source_span_ids` | `ui/src/api/mappers/productApi.js` | live API не принимал `candidate_id`/`approved` |
| Review queue item mapping из `ReviewQueueItem` | `ui/src/api/mappers/productApi.js` | `source_span_id`, `payload.candidate_*` не мапились |
| Mock review decisions совместимы с контрактом | `ui/src/api/mock/index.js` | mock/regression после смены serializer |
| Reload queue после успешного decision | `ui/src/pages/ReviewConsolePage.jsx` | live status `approved` ≠ mock `accepted` |
| OpenAPI assert POST `/review/queue` | `services/gateway/tests/test_openapi.py` | E3 добавил POST endpoint |
| E3 docs в навигации агентов | `project_structure.md`, `nornikel_e3_db_storage_ownership.md` | ownership + closed dependencies |

---

## 7. Итог

| Вопрос | Ответ |
|--------|-------|
| E3 user workflows foundation complete? | **да** — interests, notifications list, delete, admin save, review actions wired |
| Можно начинать E4? | **да** — с учётом blockers §5 (evidence/access/mock cleanup) |
| Live quality | **blocked_by_policy** |
| Runtime notification product flow | **partial** — seed/fixtures + conflict_detected; ingestion hook — E5 |
| Validator PR ready? | **да** — `feat/nornikel-e3-validator` |

**Вердикт этапа E3:** **pass** (user workflows merged; evidence/access/search — E4).
