# НорСинтез E2: ownership storage review/source/delete (Databases)

**Дата:** 2026-07-04  
**Ветка:** `feat/nornikel-e2-db-review-source-data`  
**Этап:** E2 — Dataset, SourceSpan, Review

Связанные документы: [`nornikel_parallel_execution_plan.md`](nornikel_parallel_execution_plan.md), [`nornikel_e1_db_storage_ownership.md`](nornikel_e1_db_storage_ownership.md).

---

## 1. Миграции этапа

| Ревизия | Путь | Таблицы / изменения |
|---------|------|---------------------|
| `0009` | `services/orchestrator/storage/versions/0009_add_review_source_delete_storage.py` | `source_span_lookup`, `document_cascade_refs` |

---

## 2. Таблица владельцев

| Объект | Сервис-владелец | Назначение |
|--------|-----------------|------------|
| `review_decisions` (E1) | orchestrator | Durable PG-состояние review decision |
| `source_span_lookup` | orchestrator | PG lookup highlight/page/table_row для source resolve |
| `document_cascade_refs` | orchestrator | Cross-store refs для cascade delete |
| Neo4j `Candidate*` | knowledge | Кандидаты review queue |
| Neo4j `SourceSpan` props | knowledge | `table_row_id`, `highlight_start`, `highlight_end` |
| Qdrant payload | retrieval | `page`, `highlight_start`, `highlight_end`, `table_row_id` indexes |

---

## 3. Review queue storage

- Кандидаты читаются из Neo4j: `LIST_REVIEW_CANDIDATES` + `Neo4jKnowledgeAdapter.list_review_candidates`.
- PG durable state: `ReviewStorageRepository` (`ensure_pending_decision`, `upsert_decision`, `list_decisions`).
- Связка candidate↔decision: unique `(candidate_id, candidate_type)` в `review_decisions`.

---

## 4. Source span lookup

| Слой | Поля | Индексы |
|------|------|---------|
| PG `source_span_lookup` | `highlight_start`, `highlight_end`, `page`, `table_row_id` | `document_id`, `page`, `table_row_id`, `(document_id, page)` |
| Qdrant payload | aliases `highlight_*`, `table_row_id` | keyword/integer indexes via bootstrap |
| Neo4j `SourceSpan` | optional node properties | `document_id`, `page_number`, `table_row_id` |

---

## 5. Document deletion cascade metadata

`document_cascade_refs` хранит JSONB-списки:

- `source_span_ids`, `claim_ids`, `vector_point_ids`
- `graph_node_refs` — `{label, node_id}`
- `minio_object_refs` — `{bucket, object_key}`

Tombstone-поля `indexed_documents` остаются из E1; E3 реализует delete workflow.

---

## 6. Fixtures и seed

| Артефакт | Путь |
|----------|------|
| Offline fixture pack | `infra/fixtures/e2/review_source_delete.json` |
| Loader/validator | `infra/postgres/orchestrator_db/e2_fixtures.py` |
| Seed script | `infra/postgres/orchestrator_db/seed_e2_fixtures.py` |

`scripts/reset_pg_demo.py` включает `source_span_lookup`, `document_cascade_refs`.

---

## 7. Зависимости и backlog

| ID | Статус | Комментарий |
|----|--------|-------------|
| Review API endpoints | E3 BML | Storage готов; wiring в workflow — E3 |
| Shared `SourcePayload` highlight fields | E1/E4 BML | Storage aliases в Qdrant/PG; contract fields — BML |
| Cascade delete execution | E3 | Metadata готова; cross-store purge — E3 |
| Gold dataset reviewed spans | E2 BML | DB fixtures без live models |

**blocked_by_policy:** live models не вызывались.
