# Домен: retrieval

Порт 8005. Query IR, гибридный поиск, EvidenceBundle.

## Ключевые файлы

- `services/retrieval/app/` — fusion, reranking, graph/table/vector search
- `shared/contracts/` — QueryIR, EvidenceBundle, EvidenceItem

## Принципы

Гибридный поиск; access-aware retrieval до синтеза ответа.

## Текущий ingestion boundary

Endpoint индексации принимает нормализованные документы и результаты Knowledge. Запись в Qdrant пока представлена типизированным `StorageWriteResult` с `mode=mock` и warning `qdrant_adapter_pending`; mock только считает будущие индексные записи.
