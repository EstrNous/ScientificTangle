# Домен: retrieval

Порт 8005. Query IR, семантический поиск, reranking, EvidenceBundle.

## Ключевые файлы

- `services/retrieval/app/api/query.py` — `/v1/query`, `/v1/search`, `/v1/documents/index`, bootstrap/reset
- `services/retrieval/app/qdrant_adapter.py` — live Qdrant adapter, collection `st_evidence_v1`, 256-dim cosine
- `services/retrieval/app/storage.py` — контракт адаптера, access filter
- `shared/contracts/` — QueryIR, EvidenceBundle, EvidenceItem

## Принципы

Поиск по проиндексированному корпусу; документы в query API не передаются. Проверка доступа выполняется до rerank и повторяется перед выдачей evidence.

## Текущий статус (2026-07-04)

**Реализовано:**

- Индексация `NormalizedDocument` → Qdrant points (source spans + table rows), `StorageWriteResult.mode=live`
- Query path: model `query-ir` → Qdrant vector search → access filter → model `rerank` → `EvidenceBundle`
- Source resolve: `POST /v1/sources/{id}/resolve`
- Access-aware payload: `access_level`, `allowed_roles`

**Gaps vs ТЗ (гибридный поиск):**

- Нет отдельного graph-channel, lexical/sparse и table-channel fusion
- `geo_filter` / `numeric_filter` из Query IR не применяются в Qdrant search (только в model gaps)
- Legacy `api/indexing.py` не смонтирован в FastAPI app

## Зависимости

model (embeddings, query-ir, rerank), Qdrant, Redis (config).
