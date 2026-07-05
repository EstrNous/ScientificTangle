# НорСинтез E2: validation report (Validator)

**Дата:** 2026-07-04  
**Ветка:** `feat/nornikel-e2-validator`  
**Этап:** E2 — Dataset, SourceSpan, Review  
**База:** `origin/dev` @ `c48d7c8` (после merge PR #76, #77, #78)

Связанные документы:

- [`nornikel_parallel_execution_plan.md`](nornikel_parallel_execution_plan.md)
- [`nornikel_e2_db_storage_ownership.md`](nornikel_e2_db_storage_ownership.md) — Databases (PR #76)
- [`nornikel_e2_bml_gold_dataset_report.md`](nornikel_e2_bml_gold_dataset_report.md) — Backend/ML (PR #77)
- [`nornikel_e1_validation_report.md`](nornikel_e1_validation_report.md) — blockers E1→E2

---

## 1. Merge gate

| PR | Ветка | Merge в `dev` | Артефакт |
|----|-------|---------------|----------|
| #76 | `feat/nornikel-e2-db-review-source-data` | да (`54c905e`) | migration `0009`, E2 fixtures, Neo4j/Qdrant highlight indexes |
| #77 | `feat/nornikel-e2-bml-gold-dataset` | да (`d34398f`) | `gold_questions.json`, `reviewed_source_fixtures.json`, regression suite |
| #78 | `feat/nornikel-e2-fe-review-source-ui` | да (`c48d7c8`) | `ReviewConsolePage`, source highlight/403, review components |

**Вердикт:** gate E2 для ролей Databases, Backend/ML, Frontend — **pass**. Validator может закрывать этап.

---

## 2. Проверки Validator gate (план E2)

| Критерий | Результат | Детали |
|----------|-----------|--------|
| Gold dataset без hardcoded live answers | **pass** | `gold_questions.json` содержит только `answer_outline`, questions и metadata; `pinned_demo_artifact.json` явно запрещает live answers |
| Expected `SourceSpan` ids для official questions | **pass** | 4/4 official questions: reviewed demo ids из `mvp_normalized_documents.json`; full corpus — `blocked_by_data` |
| Source viewer states | **pass** | highlight scroll (`SourceDocumentPanel`), table row (`SourceTableBlock`), locked 403 (`SourceLockedPanel`, `ReviewSourcePanel.test.jsx`) |
| Review console только через flag/route | **pass** | `VITE_REVIEW_CONSOLE_ENABLED` default `false`; `ReviewConsoleGate` → redirect `/chat`; tests pass |
| Feature work E3+ | **pass** | workflow wiring, delete API, live review actions — не в E2 merges |
| `services/orchestrator/app/service/service.py` | **pass** | не трогался |

---

## 3. Quality checks

| Проверка | Результат | Примечание |
|----------|-----------|------------|
| `python -m pytest tests/integration/test_reviewed_source_fixtures.py` | **pass** | 3 passed |
| `python -m pytest services/orchestrator/tests/test_e2_*.py` | **pass** | 6 passed (fixtures + migration chain) |
| `python -m pytest services/knowledge/tests/test_e2_review_source_storage.py` | **pass** | 2 passed |
| `python -m pytest shared/tests/test_contracts.py` | **pass** | 8 passed |
| `python -m pytest services/gateway/tests/test_openapi.py` | **pass** | 4 passed |
| `python eval/demo_quality_gate.py` | **pass (blocked overall)** | pinned sha256 match; live eval `blocked_by_policy` |
| Official span ids ↔ demo seed | **pass** | `fd41e40302889dc4`, `5bbd52f818e388f0`, `e68ad5f96111645c`, `133421dd573f9d94` — все в `mvp_normalized_documents.json` |
| `git diff --check` | **pass** | на `origin/dev` |
| `cd ui && npm test` / `npm run build` | **skipped** | `npm` отсутствует в PATH среды валидатора |
| Live `alembic upgrade` на PostgreSQL | **skipped** | нет Docker/PG в среде валидатора |
| Yandex live smoke | **blocked_by_policy** | план E0–E7 |
| Live eval / answer quality / latency p95 | **blocked_by_policy** | план E0–E7 |

### Spot-checks по E2 deliverables

| Claim | Проверка | Результат |
|-------|----------|-----------|
| `source_span_lookup`, `document_cascade_refs` | orchestrator migration `0009` | **pass** |
| Neo4j highlight props + review candidates query | `test_e2_review_source_storage.py` | **pass** |
| Reviewed fixtures + reason codes | `reviewed_source_fixtures.json` + integration tests | **pass** |
| `reviewed_sources` regression suite | `regression_suites.json` | **pass** |
| Review console behind flag | `uiFeatureFlags.js`, `ReviewConsoleGate` | **pass** |
| Review actions blocked in live mode | `isReviewActionsEnabled()` → `useMock` only | **pass** — до E3 |
| Gateway review API | `review.py` | **501** — storage E2 готов, wiring E3 (см. §6) |

---

## 4. Закрытие E1 blockers в E2

| E1 blocker | E2 статус |
|------------|-----------|
| B-E2-01 Review queue Neo4j + PG decision wiring | **partial** — storage + fixtures готовы; API endpoints — E3 BML |
| B-E2-02 Source highlight fields | **closed** — PG/Qdrant/Neo4j + UI highlight/table row |
| B-E2-03 Official reviewed `SourceSpan` ids | **closed (demo)** — reviewed demo seed; full corpus `blocked_by_data` |
| B-E3-03 Review console UI | **closed** — `ReviewConsolePage` + components + mock fixtures |

---

## 5. Blockers и dependencies перед E3

### Blockers

| ID | Blocker | Owner | Этап |
|----|---------|-------|------|
| B-E3-01 | `GET/POST /api/review/*` wiring к Neo4j candidates + PG decisions | BML | E3 |
| B-E3-02 | `DELETE /api/documents/{id}` cross-store purge | BML | E3 |
| B-E3-03 | Interests/notifications workflow APIs | BML + FE | E3 |
| B-E3-04 | Full raw corpus normalized `SourceSpan` ids | BML + data review | `blocked_by_data` |
| B-E4-01 | Direct `api/mock/` import в `ReviewConsolePage` (`conflicts.json`) | FE | E4 |
| B-E4-02 | `SourcePayload` highlight contract fields в live resolver | BML | E4 |

### Dependencies

| ID | Dependency | Этап |
|----|------------|------|
| D-E3-01 | Review decision persistence + queue list endpoint | E3 BML |
| D-E3-02 | Document deletion cascade execution | E3 BML |
| D-E3-03 | Profile interests save, NotificationBell live poll | E3 FE/BML |
| D-E6-01 | Full seed/reset Neo4j/Qdrant/MinIO + offline eval report | E6 |

### Не входит в Validator / E2

| Item | Статус |
|------|--------|
| God object refactor `orchestrator/.../service.py` | deferred |
| Live model eval | `blocked_by_policy` |
| Pre-existing suite failures (`test_chat_service`, orchestrator pipeline, retrieval access) | out of E2 scope — backlog |

---

## 6. Мелкие интеграционные исправления (Validator)

| Fix | Файл | Причина |
|-----|------|---------|
| Уточнено сообщение 501 review API: storage E2, wiring E3 | `services/gateway/app/api/review.py` | stale «E1» вводил в заблуждение после merge E2 DB |
| E2 docs в навигации агентов | `project_structure.md` | ownership + validation report |

---

## 7. Итог

| Вопрос | Ответ |
|--------|-------|
| E2 foundation complete? | **да** — gold dataset, source/review storage, review/source UI foundation |
| Можно начинать E3? | **да** — с учётом blockers §5 (workflow wiring) |
| Live quality | **blocked_by_policy** |
| Full corpus reviewed spans | **blocked_by_data** |
| Validator PR ready? | **да** — `feat/nornikel-e2-validator` |

**Вердикт этапа E2:** **pass** (dataset/source/review foundation merged; user workflows — E3).
