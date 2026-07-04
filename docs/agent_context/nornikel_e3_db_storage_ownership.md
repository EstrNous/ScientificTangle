# НорСинтез E3: ownership workflow storage (Databases)

**Дата:** 2026-07-04  
**Ветка:** `feat/nornikel-e3-db-workflow-state`  
**Этап:** E3 — User workflows

Связанные документы: [`nornikel_parallel_execution_plan.md`](nornikel_parallel_execution_plan.md), [`nornikel_e2_db_storage_ownership.md`](nornikel_e2_db_storage_ownership.md).

---

## 1. Миграции этапа

| Ревизия | Путь | Изменения |
|---------|------|-----------|
| `0010` | `services/orchestrator/storage/versions/0010_add_workflow_state_storage.py` | `cascade_status`, `cascade_steps`, `last_error` в `document_cascade_refs`; cursor-индексы audit/review |
| `0003` | `infra/postgres/notification_db/storage/versions/0003_add_workflow_notification_indexes.py` | keyset `(user_id, created_at, id)` для notifications и match results |

---

## 2. Workflow repositories

| Модуль | Назначение |
|--------|------------|
| `infra/postgres/orchestrator_db/workflow_storage.py` | Review decision + audit, delete cascade state, admin save + audit, audit cursor pagination |
| `infra/postgres/notification_db/workflow_repository.py` | Interests + normalized entities, match results, notification incremental poll |
| `infra/postgres/common/cursor.py` | encode/decode keyset cursor |

Транзакции: `async with session.begin()` для delete/review/admin/interests; rollback при исключении.

---

## 3. Fixtures и seed

| Артефакт | Путь |
|----------|------|
| Offline workflow pack | `infra/fixtures/e3/workflow_state.json` |
| Loader | `infra/postgres/orchestrator_db/e3_fixtures.py` |
| Seed script | `infra/postgres/orchestrator_db/seed_e3_fixtures.py` |

Seed включает E2 review/source/delete fixtures и добавляет interests entities, notification matches, review action, admin setting, delete target document.

---

## 4. Зависимости

| ID | Статус | Комментарий |
|----|--------|-------------|
| Workflow API wiring | E3 BML | Storage готов; endpoints — BML |
| Workflow UI | E3 FE | Seed/fixtures для e2e smoke |
| Cross-store delete execution | E3 BML | PG cascade metadata + status; MinIO/Qdrant/Neo4j purge — BML |

**blocked_by_policy:** live models не вызывались.
