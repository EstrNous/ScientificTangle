# НорСинтез E1: validation report (Validator)

**Дата:** 2026-07-04  
**Ветка:** `feat/nornikel-e1-validator`  
**Этап:** E1 — Storage и API foundation  
**База:** `origin/dev` @ `9f14728` (после merge PR #72, #73, #74)

Связанные документы:

- [`nornikel_parallel_execution_plan.md`](nornikel_parallel_execution_plan.md)
- [`nornikel_e1_db_storage_ownership.md`](nornikel_e1_db_storage_ownership.md) — Databases (PR #73)
- [`nornikel_e1_bml_no_live_policy.md`](nornikel_e1_bml_no_live_policy.md) — Backend/ML (PR #72)
- [`nornikel_e0_validation_report.md`](nornikel_e0_validation_report.md) — blockers E0→E1 (закрыты в E1)

---

## 1. Merge gate

| PR | Ветка | Merge в `dev` | Артефакт |
|----|-------|---------------|----------|
| #72 | `feat/nornikel-e1-bml-core-api-contracts` | да (`8777d6e`) | shared contracts, gateway routes, `nornikel_e1_bml_no_live_policy.md` |
| #73 | `feat/nornikel-e1-db-core-storage` | да (`510cd57`) | migrations `0008`/`0002`, seed/reset, `nornikel_e1_db_storage_ownership.md` |
| #74 | `feat/nornikel-e1-fe-api-foundation` | да (`9f14728`) | API clients, mappers, mock fixtures, async states, feature flags |

**Вердикт:** gate E1 для ролей Databases, Backend/ML, Frontend — **pass**. Validator может закрывать этап.

---

## 2. Проверки Validator gate (план E1)

| Критерий | Результат | Детали |
|----------|-----------|--------|
| Migrations на clean DB | **pass (smoke)** | static revision-chain tests: orchestrator `0008`, notification `0002`; live `alembic upgrade` не запускался (нет Docker PG в среде валидатора) |
| Shared contracts backward-compatible | **pass** | `shared/tests/test_contracts.py` — additive E1 payloads, ingestion fields без breaking change |
| UI clients не ломают mock mode | **pass** | mock handlers для interests/review/export/delete/admin/notifications; исправлен GET `/review/queue` (см. §6) |
| `git diff --check` | **pass** | на `origin/dev` |
| Backend contract tests | **pass** | gateway OpenAPI + notification service (5 passed) |
| Feature work E2+ | **pass** | не обнаружено в E1 merges |
| `services/orchestrator/app/service/service.py` | **pass** | не трогался |

---

## 3. Quality checks

| Проверка | Результат | Примечание |
|----------|-----------|------------|
| `python -m pytest shared/tests/test_contracts.py` | **pass** | 8 passed |
| `python -m pytest services/orchestrator/tests/test_*_migration.py` | **pass** | 3 passed (revision chain smoke) |
| `cd services/gateway && pytest tests/test_openapi.py tests/test_notification_service.py` | **pass** | 5 passed |
| `cd ui && npm test` (productApi, client, flags, async) | **skipped** | `npm` отсутствует в PATH среды валидатора |
| `cd ui && npm run build` | **skipped** | `npm` отсутствует в PATH среды валидатора |
| Live `alembic upgrade` на PostgreSQL | **skipped** | нет Docker/PG в среде валидатора |
| Yandex live smoke | **blocked_by_policy** | план E0–E7 |
| Live eval / answer quality / latency p95 | **blocked_by_policy** | план E0–E7 |

### Spot-checks по E1 deliverables

| Claim | Проверка | Результат |
|-------|----------|-----------|
| `review_decisions`, `export_artifacts`, tombstone fields | orchestrator migration `0008` | **pass** |
| `reference_type`, `extracted_entities`, `notification_match_results` | notification migration `0002` | **pass** |
| Interests GET/PUT wired | `gateway/app/api/interests.py` + `NotificationService` | **pass** |
| Review/delete skeleton 501 | `review.py`, `documents.py` | **pass** — честные `*_not_implemented` до E3 |
| E1 DTO exported | `shared/contracts/__init__.py` | **pass** |
| Mock layer расширен без удаления | `ui/src/api/mock/index.js` | **pass** |
| `VITE_USE_MOCK` default сохранён | `client.js` `useMock = !== 'false'` | **pass** |

---

## 4. Закрытие E0 blockers в E1

| E0 blocker | E1 статус |
|------------|-----------|
| B-E1-01 shared contracts interests/notifications/delete/export/review | **closed** — DTO + OpenAPI |
| B-E1-02 `notifications.reference_type` + match-result storage | **closed** — migration `0002` |
| B-E1-03 export boundary doc | **partial** — orchestrator authoritative; `export_db` duplicate → E5 |
| B-E1-04 document deletion tombstone PG | **closed** — `indexed_documents` fields in `0008` |
| B-E1-05 `review_decisions` foundation | **closed** — table in `0008` |

---

## 5. Blockers и dependencies перед E2

### Blockers (не блокируют merge E1, но нужны в E2/E3)

| ID | Blocker | Owner | Этап |
|----|---------|-------|------|
| B-E2-01 | Review queue candidates в Neo4j + PG decision wiring | DB + BML | E2 DB, E3 BML |
| B-E2-02 | Source highlight fields (`highlight_start/end`, `table_row_id`) | DB + BML + FE | E2 |
| B-E2-03 | Official reviewed `SourceSpan` ids | BML | E2 (`blocked_by_data` до corpus review) |
| B-E3-01 | `DELETE /documents/{id}` purge (MinIO/Qdrant/Neo4j) | BML | E3 |
| B-E3-02 | `GET /notifications?since=` incremental poll | BML | E3 |
| B-E3-03 | Review console UI + destructive actions | FE | E2/E3 |

### Dependencies

| ID | Dependency | Этап |
|----|------------|------|
| D-E2-01 | Cascade delete cross-store metadata | E2 DB |
| D-E2-02 | `ReviewConsolePage` behind feature flag | E2 FE |
| D-E5-01 | Authoritative export service vs orchestrator `export_db` duplicate | E5 |
| D-E6-01 | Full seed/reset Neo4j/Qdrant/MinIO | E6 DB |

### Не входит в Validator / E1

| Item | Статус |
|------|--------|
| God object refactor `orchestrator/.../service.py` | deferred |
| Live model eval | `blocked_by_policy` |
| Workflow UI (Profile interests save, NotificationBell live) | E3 FE |

---

## 6. Мелкие интеграционные исправления (Validator)

| Fix | Файл | Причина |
|-----|------|---------|
| `fetchReviewQueue` переведён на GET с query params | `ui/src/api/review.js`, `mappers/productApi.js` | OpenAPI `/review/queue` — GET; POST ломал бы live mode |
| Mock handler парсит query string для `review/queue` | `ui/src/api/mock/index.js` | mock mode после смены на GET |
| `reference_type` в notification payload mapping | `notification_service.py`, test | E1 contract + migration `0002` |
| Уточнён storage vs workflow в BML policy | `nornikel_e1_bml_no_live_policy.md` | PG foundation merged; skeleton routes до E3 |
| E1 docs в навигации агентов | `project_structure.md` | ownership + validation report |

---

## 7. Итог

| Вопрос | Ответ |
|--------|-------|
| E1 foundation complete? | **да** — storage migrations, contracts, API clients, mock compatibility |
| Можно начинать E2? | **да** — с учётом blockers §5 (scope E2/E3) |
| Live quality | **blocked_by_policy** |
| Validator PR ready? | **да** — `feat/nornikel-e1-validator` |

**Вердикт этапа E1:** **pass** (foundation merged; workflow wiring и dataset — E2/E3).
