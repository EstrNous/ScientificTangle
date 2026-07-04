# НорСинтез E4: validation report (Validator)

**Дата:** 2026-07-04  
**Ветка:** `feat/nornikel-e4-validator`  
**Этап:** E4 — Evidence, RBAC, Search  
**База:** `origin/dev` @ `5a01ab4` (после merge PR #85, #86, #87)

Связанные документы:

- [`nornikel_parallel_execution_plan.md`](nornikel_parallel_execution_plan.md)
- [`nornikel_e3_validation_report.md`](nornikel_e3_validation_report.md) — blockers E3→E4
- [`top1_e4_bm1_eval_regression.md`](top1_e4_bm1_eval_regression.md) — eval regression baseline (BML, вне Nornikel PR)

---

## 1. Merge gate

| PR | Ветка | Merge в `dev` | Артефакт |
|----|-------|---------------|----------|
| #85 | `feat/nornikel-e4-db-evidence-access` | да (`9de5198`) | migration `0011`, `infra/fixtures/e4/evidence_access.json`, E4 seed/audit helpers |
| #86 | `feat/nornikel-e4-bml-evidence-retrieval` | да (`44b52c7`) | access filter before synthesis/export, search filters, dictionary preflight, conflicts in payload |
| #87 | `feat/nornikel-e4-fe-evidence-access` | да (`5a01ab4`) | mock cleanup, `useSourceResolver`, search filters, dictionaries tab, upload stages, locked source panel |

**Вердикт:** gate E4 для ролей Databases, Backend/ML, Frontend — **pass**. Validator может закрывать этап.

---

## 2. Проверки Validator gate (план E4)

| Критерий | Результат | Детали |
|----------|-----------|--------|
| `VITE_USE_MOCK=false` smoke | **skipped** | `npm`/`node` отсутствуют в PATH среды валидатора |
| External partner source/search/export access filtering | **pass** | `test_query.py` access_denied + payload filter; `test_export_query_run_fails_when_source_access_changed`; `e4_fixtures` expectations |
| Grep: no `api/mock` в production components | **pass** | импорты только в `*.test.*` и `client.test.js` mock boundary |
| Dictionary upload/activate/query warning flow | **pass** | OpenAPI `/dictionaries/*`; `test_query_requires_active_dictionary_before_creating_run`; `DictionaryVersionTable`, `uploadTaskStages.js` |
| Source resolver live + 403 locked panel | **pass** | `mapSourcePayload` highlight fields; `SourceLockedPanel`, `ReviewSourcePanel`, `SourceDocumentContext` |
| Search filters geo/year/numeric/pagination | **pass** | `SearchPage`, `buildSearchQuery`, `e4EvidenceAccess.test.js` |
| RoleSwitcher только dev/mock | **pass** | `isDevRoleSwitcherEnabled()` = `useMock \|\| DEV`; `TopBar` guard |
| Review conflicts без mock catalog | **pass** | `reviewConflicts.js`, `ReviewConsolePage` без `api/mock/conflicts.json` |
| Feature work E5+ | **pass** | product export/notifications/audit pagination — не в E4 merges |
| God object `orchestrator/.../service.py` | **pass** | не трогался валидатором |

---

## 3. Quality checks

| Проверка | Результат | Примечание |
|----------|-----------|------------|
| `pytest services/orchestrator/tests/test_e4_*.py` | **pass** | 6 passed |
| `pytest services/retrieval/tests/test_e4_access_payload_smoke.py` + access tests | **pass** | 5 passed |
| `pytest services/orchestrator/tests/test_query_service.py` (export access, dictionary) | **pass** | 2 targeted passed |
| `pytest services/gateway/tests/test_chat_service*.py` | **pass (after fix)** | `_map_query_response` требует `principal` с E4 |
| `pytest services/gateway/tests/test_openapi.py test_graph.py` | **pass** | 5 passed |
| `pytest tests/integration/test_access_leak.py test_eval_runner.py test_demo_quality_gate.py` | **pass** | 11 passed |
| `python eval/demo_quality_gate.py` | **pass (blocked overall)** | pinned sha256 match; live eval `blocked_by_policy` |
| `git diff --check` | **pass** | на ветке валидатора |
| `cd ui && npm test` / `npm run build` | **skipped** | `npm` отсутствует в PATH |
| Live `alembic upgrade` + E4 fixtures seed на PostgreSQL | **skipped** | нет Docker/PG в среде валидатора |
| Full-stack `VITE_USE_MOCK=false` smoke | **skipped** | нет UI build + backend stack |
| Yandex live smoke | **blocked_by_policy** | план E0–E7 |
| Live eval / answer quality / latency p95 | **blocked_by_policy** | план E0–E7 |

### Spot-checks по E4 deliverables

| Claim | Проверка | Результат |
|-------|----------|-----------|
| E4 access fixture pack | `load_e4_fixture`, `validate_e4_fixture` | **pass** — public/internal/confidential + external_partner |
| Qdrant filter fields | `QDRANT_FILTER_FIELDS`, `test_e4_fixture_qdrant_payloads_cover_filter_fields` | **pass** |
| Migration `0011` evidence access | `test_e4_storage_migration_revision_chain` | **pass** |
| Source resolve 403 `access_denied` | `test_resolve_source_returns_access_denied_for_existing_restricted_source` | **pass** |
| Export re-check access at export time | `test_export_query_run_fails_when_source_access_changed` | **pass** |
| Active dictionary preflight on query | `test_query_requires_active_dictionary_before_creating_run` | **pass** |
| Simulation lifecycle без `api/mock` | `runSimulatedAnswerLifecycle.js` → `simulation/answerLifecycleFixtures.js` | **pass** |
| Conflicts/gaps in query payload mapping | `test_chat_service_live.py` conflicts + auth_context | **pass** |

---

## 4. Закрытие E3 blockers в E4

| E3 blocker | E4 статус |
|------------|-----------|
| B-E4-01 `api/mock/` в `ReviewConsolePage` | **closed** — `reviewConflicts.js` |
| B-E4-02 `SourcePayload` highlight fields в live resolver | **closed** — contract + `mapSourcePayload` |
| B-E4-03 Notification `reference_type=document` → `/source/{document_id}` | **partial** — UI намеренно открывает source; API `/source/{source_span_id}` — document-level resolve не гарантирован |
| B-E5-01 Runtime `ingestion_complete` без seed-only | **open** — E5 |
| B-E5-02 Notification cursor pagination в gateway API | **open** — E5 |
| B-E5-03 MinIO object delete в document purge | **open** — E5 |
| B-E3-DATA-01 Full corpus reviewed `SourceSpan` ids | **blocked_by_data** (без изменений) |

---

## 5. Blockers и dependencies перед E5

### Blockers

| ID | Blocker | Owner | Этап |
|----|---------|-------|------|
| B-E5-01 | Product notification events (`ingestion_complete`, interest_match) без seed-only | BML | E5 |
| B-E5-02 | Notification cursor pagination в gateway (storage есть, API — нет) | BML | E5 |
| B-E5-03 | MinIO object delete в document purge | BML | E5 |
| B-E5-04 | Notification click `reference_type=document` — нужен document viewer или span id в payload | FE + BML | E5 |
| B-E5-05 | Authoritative export boundary (orchestrator vs `services/export`) | BML | E5 |
| B-E5-06 | Audit pagination/CSV export | DB + BML + FE | E5 |
| B-E3-DATA-01 | Full corpus normalized `SourceSpan` ids | BML + data | `blocked_by_data` |

### Dependencies

| ID | Dependency | Этап |
|----|------------|------|
| D-E5-01 | `POST /api/export` production path + evidence table в JSON | E5 |
| D-E5-02 | Real notification source from ingestion/review/query conflicts | E5 |
| D-E5-03 | Audit events drill-down в UI | E5 |
| D-E6-01 | Full seed/reset + offline e2e Playwright | E6 |
| D-E6-02 | Live eval suites на seeded stack | E6 (`blocked_by_policy` до разрешения) |

### Не входит в Validator / E4

| Item | Статус |
|------|--------|
| God object refactor `orchestrator/.../service.py` | deferred (External Orchestrator Refactor Owner) |
| Live model eval | `blocked_by_policy` |
| `test_orchestrator_ingestion_offline.py` collection ImportError | pre-existing backlog вне E4 scope |

---

## 6. Мелкие интеграционные исправления (Validator)

| Fix | Файл | Причина |
|-----|------|---------|
| `AuthenticatedPrincipal` в `test_map_query_response_builds_ui_payload` | `services/gateway/tests/test_chat_service.py` | E4 добавил обязательный `principal` в `_map_query_response` |

---

## 7. Итог

| Вопрос | Ответ |
|--------|-------|
| E4 evidence/RBAC/search foundation complete? | **да** — access fixtures, retrieval filters, mock cleanup, dictionaries, upload stages, locked source |
| Можно начинать E5? | **да** — с учётом blockers §5 (export/notification/audit product flows) |
| Live quality | **blocked_by_policy** |
| External partner leak smoke | **pass** (offline unit/integration) |
| Validator PR ready? | **да** — `feat/nornikel-e4-validator` |

**Вердикт этапа E4:** **pass** (evidence/access/search merged; export/notification/audit productization — E5).
