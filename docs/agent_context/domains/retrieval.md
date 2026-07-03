# Домен: retrieval

Порт 8005. Query IR, гибридный поиск, EvidenceBundle.

## Ключевые файлы

- `services/retrieval/app/` — fusion, reranking, graph/table/vector search
- `services/retrieval/app/storage.py` — контракт реального Qdrant-адаптера, поиск и проверка доступа
- `shared/contracts/` — QueryIR, EvidenceBundle, EvidenceItem

## Принципы

Гибридный поиск по проиндексированному корпусу; документы в query API не передаются. Проверка доступа выполняется до rerank и повторяется перед выдачей evidence.

## Текущий ingestion boundary

Endpoint индексации принимает нормализованные документы и результаты Knowledge. Запись в Qdrant пока представлена типизированным `StorageWriteResult` с `mode=mock` и warning `qdrant_adapter_pending`; mock только считает будущие индексные записи.
