# НорСинтез E1: ownership storage-слоя (Databases)

**Дата:** 2026-07-04  
**Ветка:** `feat/nornikel-e1-db-core-storage`  
**Этап:** E1 — Storage и API foundation

Связанные документы: [`nornikel_parallel_execution_plan.md`](nornikel_parallel_execution_plan.md), [`nornikel_e0_db_baseline.md`](nornikel_e0_db_baseline.md).

---

## 1. Миграции этапа

| Ревизия | Путь | Таблицы / изменения |
|---------|------|---------------------|
| `0008` | `services/orchestrator/storage/versions/0008_add_core_storage_foundation.py` | `review_decisions`, `export_artifacts`, tombstone-поля `indexed_documents`, cursor-индексы `audit_events`, composite-индекс `export_jobs` |
| `0002` | `infra/postgres/notification_db/storage/versions/0002_add_core_notification_storage.py` | `reference_type` в `notifications`, `extracted_entities`, `notification_match_results` |

`export_db/0001` не расширялся: authoritative владелец export jobs — **orchestrator** (`export_jobs` + `export_artifacts`).

---

## 2. Таблица владельцев

| Таблица | Сервис-владелец | Alembic chain | Назначение |
|---------|-----------------|---------------|------------|
| `review_decisions` | orchestrator | orchestrator `0008` | Durable PG-состояние review decision; кандидаты остаются в Neo4j |
| `indexed_documents` (+ deletion fields) | orchestrator | orchestrator `0008` | Реестр документов, tombstone/deletion_status для delete workflow |
| `export_jobs` | orchestrator | orchestrator `0002`/`0006` | Задачи экспорта query run |
| `export_artifacts` | orchestrator | orchestrator `0008` | MinIO/storage refs артефактов export job |
| `audit_events` (+ cursor index) | orchestrator | orchestrator `0004`/`0008` | Product audit; keyset pagination по `(user_id, created_at, id)` |
| `user_interests` | gateway (notification_db layer) | notification `0001` | Профиль интересов; JSONB snapshot |
| `extracted_entities` | gateway (notification_db layer) | notification `0002` | Нормализованные сущности из interests extract |
| `notifications` (+ `reference_type`) | gateway (notification_db layer) | notification `0001`/`0002` | In-app уведомления |
| `notification_match_results` | gateway (notification_db layer) | notification `0002` | Offline match results до создания notification |
| `admin_settings` | gateway (chat_ui_db) | chat_ui `0001` | Admin save (без изменений E1) |
| `export_jobs` (duplicate) | export service stub | export_db `0001` | **Deprecated duplicate** — не authoritative |

---

## 3. Индексы под фильтры E1

| Область | Индекс | Поля |
|---------|--------|------|
| Review | `ix_review_decisions_status` | `status` |
| Review | `ix_review_decisions_status_decided_at` | `status`, `decided_at` |
| Review | `ix_review_decisions_document_id` | `document_id` |
| Review | `ix_review_decisions_source_span_id` | `source_span_id` |
| Delete | `ix_indexed_documents_deletion_status` | `deletion_status` |
| Delete | `ix_indexed_documents_deleted_at` | `deleted_at` |
| Export | `ix_export_jobs_user_status_created` | `user_id`, `status`, `created_at` |
| Export artifacts | `ix_export_artifacts_export_job_id` | `export_job_id` |
| Audit cursor | `ix_audit_events_user_created_id` | `user_id`, `created_at`, `id` |
| Notifications poll | `ix_notifications_user_created` | `user_id`, `created_at` |
| Notifications unread | `ix_notifications_user_unread` | `user_id`, `is_read` |
| Interests entities | `ix_extracted_entities_user_id` | `user_id` |
| Match results | `ix_notification_match_results_user_id` | `user_id` |

---

## 4. Seed / reset

| Скрипт | Изменение E1 |
|--------|--------------|
| `scripts/reset_pg_demo.py` | TRUNCATE для `review_decisions`, `export_artifacts`, `extracted_entities`, `notification_match_results` (дочерние таблицы первыми) |
| `infra/postgres/notification_db/seed.py` | Idempotent seed: `reference_type` в demo notifications, `extracted_entities` при создании interests |

---

## 5. Зависимости и backlog

| ID | Статус | Комментарий |
|----|--------|-------------|
| Neo4j review queue | E2 | PG `review_decisions` — durable state; candidates в graph |
| Cascade delete cross-store | E2 | Tombstone fields готовы; MinIO/Qdrant/Neo4j refs — E2 |
| export_db duplicate | E5 | Deprecate или full `services/export` boundary |
| Audit CSV export | E5 | Cursor index готов; CSV storage — E5 |

**blocked_by_policy:** не применимо (live models не вызывались).
