# НорСинтез E7: ownership, migrations, backup/restore, seed/reset, retention (Databases)

**Дата:** 2026-07-04  
**Ветка:** `feat/nornikel-e7-db-ops-docs`  
**Этап:** E7 — Production polish

Связанные документы: [`nornikel_parallel_execution_plan.md`](nornikel_parallel_execution_plan.md), [`nornikel_e7_db_ops_runbook.md`](nornikel_e7_db_ops_runbook.md), [`nornikel_e6_db_seed_report.md`](nornikel_e6_db_seed_report.md), [`nornikel_e6_db_backup_restore_gaps.md`](nornikel_e6_db_backup_restore_gaps.md), [`nornikel_e5_db_storage_ownership.md`](nornikel_e5_db_storage_ownership.md), [`nornikel_e1_db_storage_ownership.md`](nornikel_e1_db_storage_ownership.md).

---

## 1. Цель E7

Свести операторскую картину storage-слоя НорСинтез после E0–E6: владельцы, миграции, backup/restore, seed/reset, retention и проверенные cleanup policies для удалённых документов и export artifacts. Без изменения production behavior и без live models.

---

## 2. Store map и владельцы

| Store | Runtime | Сервис-владелец данных | Операторские скрипты |
|-------|---------|------------------------|----------------------|
| PostgreSQL `scientific_tangle` | docker compose | auth_audit, orchestrator, gateway layers (notification, chat_ui) | `scripts/migrate_pg_layers.py`, `scripts/backup_db.sh`, `scripts/restore_db.sh`, `scripts/reset_pg_demo.py` |
| Neo4j | docker compose | knowledge | `POST /v1/graph/reset`, `scripts/backup_db.sh` (partial) |
| Qdrant `st_evidence_v1` | docker compose | retrieval | `POST /v1/index/reset` |
| MinIO buckets | docker compose | ingestion (source), orchestrator (exports) | `infra/minio/buckets.txt`, full gate purge в `scripts/seed_inventory.py` |
| Redis | docker compose | cache/ephemeral | out of scope E7 backup |

Authoritative export boundary: **orchestrator** (`export_jobs`, `export_artifacts`, bucket `exports`). `infra/postgres/export_db` — deprecated stub.

---

## 3. PostgreSQL: Alembic chains (head)

| Chain | Путь | Head | Назначение |
|-------|------|------|------------|
| auth_audit | `services/auth_audit/storage` | `0002` | `users`, `refresh_sessions`, identity lifecycle |
| orchestrator | `services/orchestrator/storage` | `0012` | query runs, ingestion, indexed docs, review, export, audit, cascade refs |
| notification_db | `infra/postgres/notification_db/storage` | `0004` | interests, notifications, match results |
| chat_ui_db | `infra/postgres/chat_ui_db/storage` | `0001` | admin settings, chat sessions |
| export_db | `infra/postgres/export_db/storage` | `0001` | **deprecated** duplicate export tables |

Применение всех chains:

```bash
python scripts/migrate_pg_layers.py
```

Compose поднимает auth_audit и orchestrator migrations при старте; gateway layers — через `migrate_pg_layers.py` или CI.

### 3.1 Ключевые таблицы по фичам (сводка E1–E5)

| Область | Таблицы | Документ этапа |
|---------|---------|----------------|
| Review | `review_decisions` + Neo4j candidates | E1, E2 |
| Source resolve | `source_span_lookup` | E2 |
| Delete cascade | `indexed_documents` tombstone, `document_cascade_refs` | E1, E2, E3 |
| Interests / notifications | `user_interests`, `extracted_entities`, `notifications`, `notification_match_results` | E1, E3, E5 |
| Export / audit product | `export_jobs`, `export_artifacts`, `audit_events`, `audit_csv_exports` | E1, E5 |
| Evidence access | access fields в `indexed_documents`, `source_span_lookup` | E4 (migration `0011`) |
| Admin | `admin_settings` (chat_ui_db) | E1 |

Детали по этапам: [`nornikel_e1_db_storage_ownership.md`](nornikel_e1_db_storage_ownership.md), [`nornikel_e2_db_storage_ownership.md`](nornikel_e2_db_storage_ownership.md), [`nornikel_e3_db_storage_ownership.md`](nornikel_e3_db_storage_ownership.md), [`nornikel_e5_db_storage_ownership.md`](nornikel_e5_db_storage_ownership.md).

---

## 4. Neo4j, Qdrant, MinIO

### 4.1 Neo4j

- Labels: `Document`, `SourceSpan`, `Candidate*`, `DictionaryVersion`, claims/entities.
- Review queue candidates — в graph; durable decision state — PG `review_decisions`.
- Schema bootstrap: knowledge `seed_schema_registry` (вызывается при graph reset).

### 4.2 Qdrant

- Collection: `st_evidence_v1`.
- Payload indexes: `document_id`, `access_level`, `dictionary_version_id`, `highlight_*`, `table_row_id`, geo/numeric/time filters (E4).
- Bootstrap: retrieval `POST /v1/index/reset` → recreate collection + indexes.

### 4.3 MinIO buckets

| Bucket | Владелец | Содержимое |
|--------|----------|------------|
| `source-files` | ingestion | Исходные PDF/файлы документов |
| `normalized-artifacts` | ingestion | Нормализованные артефакты |
| `exports` | orchestrator | Export job artifacts (`export_artifacts.storage_key`) |
| `demo-archives` | demo/seed | Demo corpus archives |
| `temp-files` | transient | Временные upload; ручной cleanup |

Список: `infra/minio/buckets.txt`.

---

## 5. Backup / restore

Полная матрица: [`nornikel_e6_db_backup_restore_gaps.md`](nornikel_e6_db_backup_restore_gaps.md).

| Store | Backup | Restore | Примечание E7 |
|-------|--------|---------|---------------|
| PostgreSQL | `scripts/backup_db.sh` → `postgres.dump` | `scripts/restore_db.sh` + опционально `migrate_pg_layers.py` | **primary** source of truth для product state |
| Neo4j | partial (APOC cypher export) | partial cypher-shell | При gap — `reset-reseed` full gate |
| Qdrant | **нет скрипта** | **нет** | Восстановление через re-index / full gate |
| MinIO | **нет скрипта** | **нет** | `mc mirror` — рекомендация ops (runbook) |

Verify после restore:

```bash
python scripts/seed_inventory.py --mode report --include-remote
```

---

## 6. Seed / reset

Полный отчёт: [`nornikel_e6_db_seed_report.md`](nornikel_e6_db_seed_report.md).

| Режим | Команда | Требования |
|-------|---------|------------|
| Counts only | `make seed-counts` | PostgreSQL; remote optional |
| Offline fixtures | `make reset-reseed-offline` | PostgreSQL only; E2–E5 PG fixtures |
| Full stack | `make reset-reseed` | PG + Neo4j + Qdrant + MinIO + `seed_demo.py` |

`scripts/reset_pg_demo.py` — TRUNCATE demo/product tables в порядке FK (включая `audit_csv_exports` → `export_artifacts`).

**blocked_by_policy:** full gate с corpus ingest не требует live models, но требует поднятый stack; live answer quality — вне scope.

---

## 7. Retention и cleanup policies (verified E7)

### 7.1 Export artifacts

| Аспект | Статус | Детали |
|--------|--------|--------|
| TTL marker | **implemented** | `export_artifacts.expires_at`, default 30 дней (`DEFAULT_EXPORT_ARTIFACT_RETENTION_DAYS` в `product_events_storage.py`) |
| Index для purge | **implemented** | `ix_export_artifacts_expires_at` (migration `0012`) |
| Scheduled cleanup job | **not implemented** | Нет cron/worker; оператор выполняет SQL + MinIO delete по runbook |
| MinIO object on export | **implemented** | BML upload в bucket `exports`; PG хранит `bucket_name`, `storage_key`, `checksum` |

Операторский purge (ручной, до появления job):

```sql
SELECT id, storage_key, bucket_name, expires_at
FROM export_artifacts
WHERE expires_at IS NOT NULL AND expires_at < NOW();
```

Затем удалить objects в MinIO `exports/` и строки в PG.

### 7.2 Audit CSV exports

| Аспект | Статус | Детали |
|--------|--------|--------|
| Storage | **implemented** | `audit_csv_exports` + MinIO `exports/` |
| Recommended TTL | **documented** | 7 дней (константа в `product_events_storage.py`) |
| Auto-purge | **not implemented** | Ручной cleanup по `created_at` / `storage_key` |

### 7.3 Notifications

| Аспект | Статус | Детали |
|--------|--------|--------|
| Recommended TTL | **documented** | 90 дней для `notifications` и `notification_match_results` |
| Auto-purge | **not implemented** | Ручной DELETE по `created_at` |

### 7.4 Audit events

| Аспект | Статус | Детали |
|--------|--------|--------|
| Long-term retention | **no auto-purge** | Cursor export через UI/API; архивирование — ops decision |
| Pagination | **implemented** | Keyset cursor `(user_id, created_at, id)` |

### 7.5 Deleted documents

| Шаг cleanup | Статус | Механизм |
|-------------|--------|----------|
| PG tombstone | **implemented** | `indexed_documents.deletion_status=completed`, `deleted_at`, `tombstone_reason` |
| PG source spans | **implemented** | DELETE from `source_span_lookup` |
| PG cascade refs | **implemented** | DELETE `document_cascade_refs` |
| Qdrant vectors | **implemented** | `DELETE /v1/documents/{id}/index` → filter by `document_id` |
| Neo4j graph | **implemented** | `DELETE /v1/documents/{id}/graph` → DETACH DELETE Document + spans + linked |
| MinIO source objects | **gap** | `document_cascade_refs.minio_object_refs` хранит refs, но orchestrator `DELETE /documents/{id}` **не** вызывает `remove_object`; объекты в `source-files` остаются до ручного purge |
| Review decisions for doc | **partial** | Прямой delete API не вызывает `purge_document_pg_refs`; orphan decisions возможны — см. runbook |

Warnings в ответе delete: `retrieval_purge_unavailable`, `knowledge_purge_unavailable`, `*_purge_failed`, `*_purge_endpoint_missing`.

### 7.6 Temp MinIO bucket

Bucket `temp-files` — без автоматического TTL в коде E7. Рекомендация: периодический `mc rm --older-than` (runbook).

---

## 8. Итог E7 Databases

| Область | Статус |
|---------|--------|
| Ownership / migrations docs | **closed** |
| Backup/restore matrix | **closed** (gaps Qdrant/MinIO задокументированы) |
| Seed/reset gate | **closed** (E6) |
| Retention constants + indexes | **closed** |
| Automated retention jobs | **open backlog** — ops runbook until job lands |
| MinIO purge on document delete | **open backlog** — metadata есть, auto-purge нет |
| Live model re-embed after restore | **blocked_by_policy** |

**Dependency:** E6 validator merged в `origin/dev` (PR #93 area); новых blockers на несмёрженные PR ролей E7 нет.

Инцидентный runbook: [`nornikel_e7_db_ops_runbook.md`](nornikel_e7_db_ops_runbook.md).
