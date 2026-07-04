# НорСинтез E5: ownership product events storage (Databases)

**Дата:** 2026-07-04  
**Ветка:** `feat/nornikel-e5-db-product-events`  
**Этап:** E5 — Export, Notifications, Audit

Связанные документы: [`nornikel_parallel_execution_plan.md`](nornikel_parallel_execution_plan.md), [`nornikel_e1_db_storage_ownership.md`](nornikel_e1_db_storage_ownership.md).

---

## 1. Миграции этапа

| Ревизия | Путь | Изменения |
|---------|------|-----------|
| `0012` | `services/orchestrator/storage/versions/0012_add_product_events_storage.py` | MinIO metadata в `export_artifacts`, `completed_at` и cursor-индекс `export_jobs`, таблица `audit_csv_exports` |
| `0004` | `infra/postgres/notification_db/storage/versions/0004_add_product_notification_indexes.py` | keyset `(user_id, type, created_at, id)` и unread+since индекс для notifications |

Authoritative export boundary: **orchestrator** (`export_jobs` + `export_artifacts` + MinIO bucket `exports`). `export_db/0001` остаётся deprecated stub.

---

## 2. Storage repositories

| Модуль | Назначение |
|--------|------------|
| `infra/postgres/orchestrator_db/product_events_storage.py` | Export jobs/artifacts с MinIO refs, audit cursor+filters, audit CSV export records, CSV serialization |
| `infra/postgres/orchestrator_db/workflow_storage.py` | Review/delete/admin audit (без изменений E5) |
| `infra/postgres/notification_db/workflow_repository.py` | Incremental notification poll (`since`/cursor) |

---

## 3. MinIO metadata

| Поле | Таблица | Назначение |
|------|---------|------------|
| `bucket_name` | `export_artifacts`, `audit_csv_exports` | Bucket `exports` из `infra/minio/buckets.txt` |
| `storage_key` | `export_artifacts`, `audit_csv_exports` | Object key внутри bucket |
| `byte_size`, `checksum` | `export_artifacts` | Integrity/size для download |
| `expires_at` | `export_artifacts` | Retention marker для cleanup job |

---

## 4. Fixtures и seed

| Артефакт | Путь |
|----------|------|
| Offline product events pack | `infra/fixtures/e5/product_events.json` |
| Loader/validator | `infra/postgres/orchestrator_db/e5_fixtures.py` |
| Seed script | `infra/postgres/orchestrator_db/seed_e5_fixtures.py` |

Seed включает E4 evidence fixtures и добавляет export job+artifacts, product audit events, notification events, completed audit CSV export.

---

## 5. Retention / cleanup (операторские заметки)

| Объект | Рекомендуемый TTL | Cleanup scope |
|--------|-------------------|---------------|
| `export_artifacts` (MinIO `exports/`) | 30 дней | PG row + MinIO object по `expires_at` |
| `audit_csv_exports` | 7 дней | PG row + MinIO object по `storage_key` |
| `notifications` | 90 дней | PG `notifications` + `notification_match_results` по `created_at` |
| `audit_events` | без авто-purge E5 | Cursor export only; long-term retention — E7 ops |

`scripts/reset_pg_demo.py` truncates `audit_csv_exports` перед `export_artifacts`.

---

## 6. Зависимости

| ID | Статус | Комментарий |
|----|--------|-------------|
| Export API wiring | **E5 BML** | `POST /api/export`, job polling, MinIO upload |
| Notification product source | **E5 BML** | ingestion/review/query conflict events |
| Audit/Export UI | **E5 FE** | ExportPanel, audit CSV download, notification center |

**blocked_by_policy:** live models не вызывались.
