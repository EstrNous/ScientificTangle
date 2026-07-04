# Отчёт аудита репозитория

**Обновлено:** 2026-07-04  
**Сводка реализации vs ТЗ:** [`implementation_quality_report.md`](implementation_quality_report.md)  
**Пайплайн запроса:** [`query_pipeline.md`](query_pipeline.md)

Статусы: `open` | `planned` | `closed`

## P0 — антипаттерны кода

| ID | Проблема | Статус |
|----|----------|--------|
| P0-01 | `from app.*` в `services/*/app/` | closed |
| P0-02 | Дублирование `ExportJob` (orchestrator_db / export_db) | closed |
| P0-03 | `infra/postgres/init.sql` (dummy-схема) | closed |

## P0 — операционные костыли

| ID | Проблема | Статус |
|----|----------|--------|
| P0-10 | `make up-auth` | closed |
| P0-11 | Makefile TODO (`test`, `lint`, `e2e`, …) | closed |
| P0-12 | Несогласованные `depends_on` в compose | closed |
| P0-13 | ChatPage / GraphPage обходят `api/client.js` | closed |
| P0-14 | Устаревший `domains/auth_audit.md` | closed |
| P0-15 | `infra/scripts/` в project_structure без папки | closed |
| P0-16 | Отсутствие CI workflow | closed |

## P1 — продуктовые gaps (не блокер MVP)

| ID | Проблема | Статус |
|----|----------|--------|
| P1-01 | UI auth: RoleSwitcher остаётся в dev; prod должен опираться на JWT session | open |
| P1-02 | UploadPage / SearchPage / AdminPage — real API; риск mock sources при `VITE_USE_MOCK=true` | open |
| P1-03 | ТЗ §420: «auth stub» — auth реализован, пункт устарел | closed |
| P1-04 | `EVAL_AUTH_TOKEN` вручную для eval | open |
| P1-05 | Гибридный retrieval wired; нужен seeded/live quality proof | open |
| P1-06 | UI source refs: `sourceResolver` → `mockAdapter` при `VITE_USE_MOCK=true` | open |
| P1-07 | Нет зафиксированного live eval artifact на demo corpus | open |
| P1-08 | Rate limiting в gateway/nginx | open |
| P1-09 | Internal service auth export/notification (`X-Internal-Service-Token`) | closed |
| P1-10 | PDF export не реализован | open |
| P1-11 | Post-ingestion notification delivery (`ingestion_complete`, `interest_match`) | open |

## Инфраструктура и адаптеры

| Компонент | Статус | Факт в коде |
|-----------|--------|-------------|
| Neo4j | **closed** | `Neo4jKnowledgeAdapter` в knowledge; subgraph, conflicts, gaps, claims |
| Qdrant | **closed** | `QdrantRetrievalStorageAdapter`, collection `st_evidence_v1`, `mode=live` |
| Redis | **closed** | В compose; config в сервисах |
| MinIO | **closed** | Ingestion bucket `source-files` |
| PostgreSQL service schemas | **closed** | auth_audit, orchestrator, chat_ui, notification; export authoritative metadata в `orchestrator_db`, runtime state в Redis/MinIO |
| `chat_ui_db` | **closed** | Gateway: ChatSession, ChatMessage |
| `orchestrator_db` | **closed** | IngestionTask, QueryRun, ExportJob, audit_events |
| `export_db` | **unused** | Authoritative `ExportJob`/`export_artifacts` находятся в `orchestrator_db`; export service хранит runtime status в Redis/in-memory и artifacts в MinIO |
| `notification_db` | **wired_with_gaps** | CRUD interests/notifications, internal events с service token; post-ingestion runtime delivery — backlog |
| Export microservice | **wired_with_gaps** | `gateway → orchestrator → export → MinIO`; MD/JSON/JSON-LD; PDF — backlog; internal auth — **closed** |
| Notification microservice | **wired_with_gaps** | Gateway proxy + conflict events + internal match; post-ingestion delivery — backlog; internal auth — **closed** |

## Граф compose depends_on (целевой)

```
postgres → auth_audit, orchestrator, notification
redis → gateway, orchestrator, ingestion, knowledge, retrieval, model, export, notification
minio → ingestion, export
neo4j → knowledge, retrieval
qdrant → retrieval
auth_audit → ingestion, orchestrator, export, notification, gateway, nginx
model → knowledge, retrieval, orchestrator, export, notification
ingestion, retrieval → orchestrator
export → orchestrator, gateway
orchestrator, notification → gateway
gateway, auth_audit, ui → nginx
```

Проверка: `python scripts/audit_repo.py`
