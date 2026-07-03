# Отчёт аудита репозитория

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

## P1 — продуктовые gaps (не блокер)

| ID | Проблема | Статус |
|----|----------|--------|
| P1-01 | UI auth без JWT (локальный RoleSwitcher) | planned |
| P1-02 | UploadPage / SearchPage / AdminPage — placeholder | planned |
| P1-03 | ТЗ §420: «auth stub» (auth уже реализован) | planned |
| P1-04 | `EVAL_AUTH_TOKEN` вручную для eval | planned |

## Planned-инфра (не дефекты)

| Компонент | Статус | Назначение |
|-----------|--------|------------|
| Neo4j | planned | граф claims в knowledge/retrieval |
| Qdrant | planned | vector search в retrieval |
| Redis | planned | очереди orchestrator, кэш model/gateway/retrieval, pub/sub notification |
| chat_ui_db / export_db / notification_db | not_wired | заготовки DB-слоёв |
| `adapter_pending` в knowledge | planned | запись в Neo4j |
| `documents` в теле query | interim | до Qdrant/Neo4j |

## Граф compose depends_on (целевой)

```
postgres → auth_audit, orchestrator, export, notification
redis → gateway, orchestrator, ingestion, knowledge, retrieval, model, export, notification
minio → ingestion, export
neo4j → knowledge, retrieval
qdrant → retrieval
auth_audit → ingestion, orchestrator, gateway, nginx
model → knowledge, retrieval, orchestrator
ingestion, retrieval → orchestrator
orchestrator → gateway
gateway, auth_audit, ui → nginx
```

Проверка: `python scripts/audit_repo.py`
