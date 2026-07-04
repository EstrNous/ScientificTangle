# НорСинтез E7: операторский runbook storage (Databases)

**Дата:** 2026-07-04  
**Ветка:** `feat/nornikel-e7-db-ops-docs`  
**Этап:** E7 — Production polish

Связанные документы: [`nornikel_e7_db_ops_ownership.md`](nornikel_e7_db_ops_ownership.md), [`nornikel_e6_db_seed_report.md`](nornikel_e6_db_seed_report.md), [`nornikel_e6_db_backup_restore_gaps.md`](nornikel_e6_db_backup_restore_gaps.md).

Ограничение: без live model calls. Шаги, требующие live inference/re-embed, помечены `blocked_by_policy`.

---

## 0. Быстрые команды

| Задача | Команда |
|--------|---------|
| Health stack | `docker compose ps` + gateway `/health/all` |
| PG migrations | `python scripts/migrate_pg_layers.py` |
| Counts report | `make seed-counts` |
| Offline reseed | `make reset-reseed-offline` |
| Full reseed | `make reset-reseed` |
| PG backup | `scripts/backup_db.sh` |
| PG restore | `scripts/restore_db.sh <timestamp>` |

---

## 1. Migration fail (PostgreSQL)

### Симптомы

- Сервис не стартует: `alembic.util.exc.CommandError`, `relation already exists`, `column does not exist`.
- `python scripts/migrate_pg_layers.py` падает на одной из chains.

### Диагностика

1. Определить chain: auth_audit / orchestrator / notification_db / chat_ui_db.
2. Проверить текущую ревизию:

```bash
cd services/orchestrator
python -m alembic -c alembic.ini current
python -m alembic -c alembic.ini history --verbose | tail -5
```

3. Сверить с ожидаемым head: orchestrator `0012`, notification `0004` (см. ownership doc).

### Восстановление

| Сценарий | Действие |
|----------|----------|
| Чистая dev-среда | `docker compose down -v` (destructive) → `docker compose up -d` → `migrate_pg_layers.py` |
| Drift после restore dump | `pg_restore` → `python scripts/migrate_pg_layers.py` |
| Частично применённая ревизия | Исправить вручную только на non-prod; на prod — backup перед `alembic stamp` |
| Demo/offline baseline | `make reset-reseed-offline` после успешных migrations |

### Verify

```bash
python scripts/migrate_pg_layers.py
python scripts/seed_inventory.py --mode report
```

---

## 2. Qdrant empty / vectors missing

### Симптомы

- Search/retrieval возвращает пустые hits при наличии документов в PG.
- `seed_inventory.py --include-remote` → `vectors: 0` после full ingest.
- Ошибки `qdrant_collection_missing` в delete/index API.

### Диагностика

1. Qdrant доступен: `curl http://localhost:6333/collections/st_evidence_v1`.
2. Points count в collection.
3. PG `indexed_documents.indexed_points_count` vs Qdrant count.

### Восстановление

| Сценарий | Действие |
|----------|----------|
| Collection отсутствует | `POST retrieval /v1/index/reset` или full gate step в `seed_inventory.py --mode full` |
| Collection пустая после volume wipe | `make reset-reseed` (требует stack + `seed_demo.py` ingest) |
| Только один документ | `DELETE` + re-ingest документа через upload pipeline |
| Offline dev без corpus | `make reset-reseed-offline` — vectors=0 ожидаемо |

### Verify

```bash
python scripts/seed_inventory.py --mode report --include-remote
```

**blocked_by_policy:** проверка качества re-embed после ingest — зона BML offline/live eval, не DB ops.

---

## 3. Neo4j unavailable / graph empty

### Симптомы

- Knowledge health fail; review candidates пустые; graph UI без узлов.
- Delete document warnings: `knowledge_purge_unavailable`, `neo4j_adapter_pending`.
- Backup placeholder `neo4j.meta` вместо полного cypher dump.

### Диагностика

1. `docker compose ps` → контейнер `st-neo4j`.
2. `cypher-shell` ping: `RETURN 1`.
3. Counts: `MATCH (n) RETURN labels(n), count(*)` (ограничить на dev).

### Восстановление

| Сценарий | Действие |
|----------|----------|
| Сервис down | `docker compose up -d neo4j` (или полный stack) |
| Пустой graph после wipe | `POST knowledge /v1/graph/reset` → `seed_demo.py` / full gate |
| Partial backup restore | `restore_db.sh` neo4j cypher (может быть incomplete) → предпочтительно reset + re-ingest |
| Schema drift | graph reset вызывает `seed_schema_registry` |

### Verify

```bash
python scripts/seed_inventory.py --mode report --include-remote
```

Рекомендация production backlog: neo4j-admin dump/load (см. E6 backup gaps).

---

## 4. MinIO missing object

### Симптомы

- Source viewer 404/500 при открытии документа.
- Export download fail при валидном `export_artifacts.storage_key`.
- Ingest/upload ошибки `NoSuchKey`.
- Delete document оставил orphan objects (известный gap E7).

### Диагностика

1. Проверить bucket/object:

```bash
docker exec st-minio mc ls local/source-files/<object_key>
docker exec st-minio mc ls local/exports/<storage_key>
```

2. Сверить PG: `indexed_documents` / `export_artifacts` / `document_cascade_refs.minio_object_refs`.

### Восстановление

| Сценарий | Действие |
|----------|----------|
| Export artifact missing | Пометить job failed; пользователь re-export; purge stale PG row |
| Source file missing | Re-upload документа или restore из backup (`mc mirror` backlog) |
| Orphan после delete | Ручной `mc rm` по `minio_object_refs` если refs ещё в PG; иначе inventory по prefix `document_id` |
| Полный wipe bucket | Full gate: `seed_inventory.py --mode full` purges buckets → `seed_demo.py` |

### Scheduled backup (рекомендация)

```bash
mc mirror local/source-files /backups/source-files
mc mirror local/exports /backups/exports
```

Автоматизация не в repo E7 — cron на стороне ops.

---

## 5. Stale dictionary

### Симптомы

- Upload/query warnings о dictionary version.
- Admin UI показывает неактивную версию как active.
- Ingestion tasks с устаревшим `dictionary_version_id`.
- Retrieval payload filter `dictionary_version_id` не совпадает с активной версией.

### Диагностика

1. Neo4j: `MATCH (d:DictionaryVersion) RETURN d.id, d.version, d.is_active ORDER BY d.created_at DESC`.
2. Gateway/admin API: list dictionaries + active badge.
3. PG: `ingestion_tasks.dictionary_version_id`, `query_runs.dictionary_version_id`.

### Восстановление

| Сценарий | Действие |
|----------|----------|
| Нет активной версии | Загрузить dictionary package через admin → activate |
| Активная устарела | Upload новой версии → activate → re-ingest affected documents (offline ingest, no live model) |
| Pinning mismatch в query | Новый query run подхватит active version; старые runs сохраняют historical `dictionary_version_id` |
| Полный сброс | `seed_demo.py` seeds dictionaries + demo corpus (full gate) |

### Verify

- Admin dictionaries tab: active badge на ожидаемой версии.
- Preflight upload: нет warning `dictionary_version_missing`.
- `seed_inventory.py --include-remote` → `dictionary_versions >= 1` после full seed.

---

## 6. Retention cleanup (ручной цикл)

До появления scheduled job выполнять периодически:

### Export artifacts (TTL 30d)

1. SELECT expired rows (см. ownership doc §7.1).
2. `mc rm local/exports/<storage_key>` для каждого key.
3. DELETE FROM `export_artifacts` WHERE `expires_at < NOW()`.

### Audit CSV (TTL 7d)

1. SELECT FROM `audit_csv_exports` WHERE `created_at < NOW() - interval '7 days'`.
2. Удалить MinIO objects → DELETE rows.

### Notifications (TTL 90d)

```sql
DELETE FROM notification_match_results WHERE created_at < NOW() - interval '90 days';
DELETE FROM notifications WHERE created_at < NOW() - interval '90 days';
```

### Temp bucket

```bash
docker exec st-minio mc rm --recursive --force --older-than 7d local/temp-files/
```

---

## 7. Escalation matrix

| Инцидент | Первый шаг | Если не помогло | Blocker |
|----------|------------|-----------------|---------|
| Migration fail | `migrate_pg_layers.py` + логи alembic | PG restore / offline reseed | DBA review на prod |
| Qdrant empty | index reset | full reseed | re-ingest (**blocked_by_policy** для live quality check) |
| Neo4j down | compose restart | graph reset + seed | neo4j-admin backup backlog |
| MinIO missing | mc ls + re-upload | mirror restore | backup automation backlog |
| Stale dictionary | activate correct version | re-ingest docs | BML ingest pipeline |
| Export orphans | manual mc rm + PG delete | — | retention job backlog |

---

## 8. Связь с другими ролями E7

| Тема | Владелец |
|------|----------|
| Operator runbook (API health, eval, blocked_by_policy) | E7 Backend/ML |
| UI degraded states, health indicator | E7 Frontend |
| Orchestrator god object refactor | External Orchestrator Refactor Owner — **не трогать** в этом плане |
