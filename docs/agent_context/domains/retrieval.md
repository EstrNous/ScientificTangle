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
- Query path: model `query-ir` → Qdrant dense search + lexical/table scroll + graph evidence → fusion → source access revalidation → model `rerank` → `EvidenceBundle`
- Source resolve: `POST /v1/sources/{id}/resolve`
- Access-aware payload: `access_level`, `allowed_roles`
- `retrieval_trace`: channel counts (`dense`, `lexical`, `table`, `graph`), raw/fused/accessible/reranked counts, planner dump
- Qdrant filters: source type, dictionary version, geo bucket/country, numeric units/ranges, `published_year`

**Remaining gaps:**

- Нужно подтвердить качество hybrid retrieval на seeded official e2e report; live answer quality остаётся `blocked_by_policy`
- Legacy `api/indexing.py` не смонтирован в FastAPI app

## Зависимости

model (embeddings, query-ir, rerank), Qdrant, Redis (config).
