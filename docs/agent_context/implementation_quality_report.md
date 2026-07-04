# Отчёт о качестве реализации ScientificTangle

**Дата:** 2026-07-04  
**Статус проекта:** post-MVP — основной путь end-to-end работает; остаётся закрыть product gaps и production hardening  
**Методология:** анализ кода, тестов, CI, инфраструктуры и сверка с [`mvp.md`](../tz/mvp.md), [`ml_mvp_status.md`](ml_mvp_status.md), [`audit_report.md`](audit_report.md).

Этот документ **дополняет**, а не заменяет `audit_report.md` и `ml_mvp_status.md`.

**Пайплайн запроса (детально):** [`query_pipeline.md`](query_pipeline.md).  
**Матрица фич:** [`feature_readiness_matrix.md`](feature_readiness_matrix.md).

---

## 1. Резюме для продукта

ScientificTangle — evidence-first платформа доказательной карты R&D знаний горно-металлургической отрасли. Архитектура: **9 Python-микросервисов**, **React UI**, **shared contracts**, полный Docker-стек (PostgreSQL, Neo4j, Qdrant, MinIO, Redis, Prometheus/Grafana, nginx).

### Сводка по зонам (оценка готовности к production-ready 100%)

| Зона | Готово | Не хватает | Что реально осталось |
|------|--------|------------|----------------------|
| **MVP функционально** | ~90% | ~10% | Основной путь работает; не закрыты PDF export, часть notification loop и часть UI-polish |
| **Production readiness** | ~82% | ~18% | Rate limiting, более жёсткий внешний периметр, актуальная документация, пара product gaps |
| **UI** | ~78% | ~22% | Mock не дефолт (`VITE_USE_MOCK=false` в compose); `sourceResolver` всё ещё переключается на `mockAdapter` при `VITE_USE_MOCK=true` — риск демо-источников при ошибочной сборке |
| **Export** | ~86% | ~14% | Markdown/JSON/JSON-LD через `gateway → orchestrator → export → MinIO`; PDF не реализован |
| **Notification** | ~82% | ~18% | Interests, conflict events, list/read wired; нет автоматического уведомления после загрузки/обработки документа |
| **Auth / security** | ~94% | ~6% | JWT/RBAC/service-token есть; нет rate limiting и production hardening внешнего периметра |
| **CI / Ops** | ~86% | ~14% | Ruff, coverage gate 60%, e2e compose job есть; остаётся укрепить prod-периметр compose и регламент pre-release |
| **Docs / agent context** | обновляется | — | Синхронизация с кодом (в т.ч. закрытый internal service auth) |
| **Архитектура orchestrator** | ~80% | ~20% | Работает; `OrchestratorService` крупный (~1240 строк) — сложен для эволюции |

### Вердикт

**MVP pipeline реализован (~90% чеклиста)** и превосходит типичный хакатон-MVP: microservices, единые контракты, evidence-first, реальные Neo4j и Qdrant, export/notification как HTTP-сервисы. Главные разрывы post-MVP: **PDF export**, **post-ingestion notification delivery**, **rate limiting / edge hardening**, **риск mock path в UI при неверном флаге**, **live eval artifact**, **декомпозиция orchestrator**.

Кодовая база готова к итеративному доведению **без архитектурного перелома**.

### Топ-5 сильных сторон

1. **Evidence-first дисциплина** — confirmed claims только с `SourceSpan`; candidate layer с reason codes; Pydantic-контракты в `shared/contracts`.
2. **Зрелый model service** — 13 v1 endpoints, prompt/schema registry, eval dataset, Yandex routing с explicit degraded fallback.
3. **Реальные хранилища** — Neo4jKnowledgeAdapter, Qdrant `st_evidence_v1` с `mode=live`.
4. **Production-oriented infra** — DB-per-service, Alembic, Docker secrets для JWT, `INTERNAL_SERVICE_TOKEN` для межсервисных вызовов, Prometheus/Grafana, nginx, `scripts/audit_repo.py`.
5. **Auth slice** — RS256 JWT, JWKS, refresh, RBAC, audit; internal service auth на export/notification internal routes.

### Топ-5 рисков

1. **Post-ingestion notifications** — `ingestion_complete` / `interest_match` есть в seed и i18n, но runtime hook из orchestrator не подключён.
2. **PDF export** — формат не в `ExportService`; UI может показывать disabled state.
3. **Внешний периметр** — нет rate limiting в gateway/nginx; compose secrets требуют hardening для публичного стенда.
4. **Orchestrator god-service** — ingestion + query + export + audit в одном модуле.
5. **Качество ответов не зафиксировано live artifact** — offline gates есть; pinned live eval report — backlog.

---

## 2. Технологический стек

| Слой | Технологии | Оценка |
|------|------------|--------|
| Backend | Python 3.12, FastAPI, httpx, SQLAlchemy 2 async | Зрелый, единообразный |
| Validation | Pydantic v2, `shared/contracts` | Контракты централизованы |
| Graph / Vector | Neo4j 5, Qdrant `st_evidence_v1` | Live adapters |
| Object storage | MinIO (`source-files`, `exports`) | Ingestion + export artifacts |
| Auth | RS256 JWT, JWKS, `X-Internal-Service-Token` | User JWT + service-to-service |
| Frontend | React 19, Vite 7, Tailwind, Zustand | Real API по умолчанию |
| Edge | nginx → auth_audit / gateway | Basic auth на Grafana |
| Observability | Prometheus, Grafana, structlog JSON | RED-метрики |
| CI | ruff, pytest + cov ≥60%, vitest, compose e2e | Обязательный pipeline на PR |

---

## 3. Оценка по сервисам

Шкала: 1 — отсутствует; 3 — ядро с gaps; 4 — рабочий E2E; 5 — production-ready.

| Сервис | Порт | Зрелость | Ключевые gaps |
|--------|------|----------|---------------|
| **gateway** | 8000 | 4 | Rate limiting; thin tests strategic/lab |
| **auth_audit** | 8001 | 5 | Rate limiting |
| **orchestrator** | 8002 | 4 | God-service (~1240 строк); post-ingestion notify hook |
| **ingestion** | 8003 | 4 | Сканы/VL/OCR не в MVP-пути |
| **knowledge** | 8004 | 4 | Fact versioning UI |
| **retrieval** | 8005 | 4 | Live quality proof; `/search` без full fusion parity |
| **model** | 8006 | 5 | Pinned live eval artifact |
| **export** | 8007 | 4 | PDF renderer |
| **notification** | 8008 | 4 | Post-ingestion runtime delivery |
| **UI** | 3000 | 3.5 | `mockAdapter` в sourceResolver при mock-режиме; polish |

---

## 4. MVP vs фактическое состояние

| Требование MVP | Статус | Комментарий |
|----------------|--------|-------------|
| Полный ingestion pipeline | ✅ | orchestrator → ingestion → knowledge → retrieval |
| NormalizedDocument + SourceSpan | ✅ | parsers + MinIO |
| Claims в Neo4j, chunks в Qdrant | ✅ | live adapters |
| Query IR + hybrid retrieval + fusion | ✅ | dense + lexical + table + graph |
| Ответ в UI | ✅ | ChatPage, evidence, LocalGraph |
| RBAC + access policy | ✅ backend / ⚠️ UI | RoleSwitcher только при `VITE_USE_MOCK=true` |
| Audit log | ✅ | auth_audit + orchestrator |
| Export Markdown/JSON/JSON-LD | ✅ | orchestrator → export → MinIO |
| Export PDF | ❌ | backlog |
| Docker reproducibility + CI | ✅ | compose, seed, e2e job |
| ≥4 official questions + quality proof | ⚠️ | dataset и offline gate; live artifact — нет |
| Post-ingestion notifications | ❌ | conflict events есть; ingestion_complete runtime — нет |

**MVP checklist: ~90%.**

---

## 5. Приоритетный backlog

### P0 — продуктовые дыры

| # | Задача | Размер |
|---|--------|--------|
| 1 | Runtime `ingestion_complete` / `interest_match` из orchestrator | M |
| 2 | PDF export (server-side renderer → MinIO) | M |
| 3 | UI: исключить риск mock sources в prod-сборке (fail-fast или убрать mockAdapter из default bundle) | S |
| 4 | Pinned live eval artifact на demo corpus | S |

### P1 — production hardening

| # | Задача | Размер |
|---|--------|--------|
| 5 | Rate limiting (gateway и/или nginx) | M |
| 6 | Prod perimeter: TLS, secrets rotation, CORS, WAF decision | M |
| 7 | Search endpoint parity с hybrid query path | S |
| 8 | Pre-release checklist (health, seed, official smoke, export, audit) | S |

### P2 — архитектура и polish

| # | Задача | Размер |
|---|--------|--------|
| 9 | Декомпозиция `OrchestratorService` (ingestion/query/export runners) | L |
| 10 | MinIO purge при delete document | S |
| 11 | Review console / fact versioning (top-1) | L |

---

## 6. Безопасность

**Реализовано:** RS256 JWT, JWKS, refresh, RBAC, access filter до synthesis/export, Docker secrets, audit events, **`require_internal_service`** на `export POST /v1/jobs` и `notification /internal/v1/*` (`shared/web/auth.py`, заголовок `X-Internal-Service-Token`, `.env.example` → `INTERNAL_SERVICE_TOKEN`).

**Риски:** нет rate limiting; env auto-login в compose для demo; публичный стенд требует отдельного perimeter hardening.

---

## 7. Тестирование и CI

- **Backend:** `python scripts/run_tests.py` — suites по всем сервисам + integration + e2e (opt-in локально, **обязателен в CI** с `RUN_E2E=1`).
- **Coverage:** `COVERAGE_FAIL_UNDER=60` в `.github/workflows/ci.yml`.
- **UI:** vitest в CI; Playwright offline scenarios в `ui/e2e/`.
- **Repo audit:** `python scripts/audit_repo.py` → all checks passed.

---

## 8. Расхождения документации (исправлено в этом цикле)

| Было в docs | Факт в коде (2026-07-04) |
|-------------|--------------------------|
| Internal endpoints export/notification без auth | **Закрыто:** `Depends(require_internal_service)` |
| Export microservice «только health» | **Устарело:** полный job API + MinIO |
| Notification microservice «заглушка» | **Устарело:** владеет `notification_db`, CRUD + internal events |
| UI: 10 компонентов импортируют `api/mock/` | **Устарело:** mock catalog только в `sourceResolver/mockAdapter.js` (dev/mock path) |
| CI без coverage / e2e | **Устарело:** coverage ≥60%, compose e2e job |

---

## 9. Связанные документы

| Документ | Назначение |
|----------|------------|
| [`feature_readiness_matrix.md`](feature_readiness_matrix.md) | Детальная матрица фич и MVP 100% план |
| [`mvp.md`](../tz/mvp.md) | Definition of Done MVP |
| [`audit_report.md`](audit_report.md) | P0/P1 аудит репозитория |
| [`ml_mvp_status.md`](ml_mvp_status.md) | Статус ML MVP |
| [`prod_readiness_gap_analysis.md`](prod_readiness_gap_analysis.md) | Production gaps |
| [`domains/`](domains/) | Контекст по сервисам |

---

## Приложение A. Метрики (2026-07-04)

```
python scripts/audit_repo.py          → all checks passed
.github/workflows/ci.yml              → ruff, pytest cov≥60%, vitest, compose e2e
orchestrator app/service/service.py   → ~1240 строк
export formats                        → markdown, json, jsonld (pdf — нет)
INTERNAL_SERVICE_TOKEN                → shared/web/auth.py, .env.example
UI default                            → VITE_USE_MOCK=false (docker-compose, vite.config)
sourceResolver                        → liveAdapter при !useMock; mockAdapter при VITE_USE_MOCK=true
```
