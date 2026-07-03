# Домен: ingestion

Порт 8003. Загрузка, парсинг, NormalizedDocument.

## Ключевые файлы

- `services/ingestion/app/` — upload, parsing, classification, metadata
- `shared/contracts/` — NormalizedDocument, SourceSpan, TableBlock

## Pipeline

Файл/ZIP → task → storage → NormalizedDocument → SourceSpan → downstream (knowledge, model).
