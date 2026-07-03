# Домен: ingestion

Порт 8003. Загрузка, парсинг, NormalizedDocument.

## Ключевые файлы

- `services/ingestion/app/` — upload, parsing, classification, metadata
- `services/ingestion/app/parsers/` — реестр адаптеров PDF, DOCX, PPTX, DOC и ZIP
- `shared/contracts/` — NormalizedDocument, SourceSpan, TableBlock и DTO нормализации сохранённых источников

## Pipeline

Файл/ZIP → task → MinIO → нормализация → NormalizedDocument → SourceSpan → Knowledge → Retrieval.

Legacy DOC конвертируется в DOCX через LibreOffice headless. Небезопасные и превышающие лимиты ZIP отклоняются. Ошибка отдельного файла фиксируется как warning; отсутствие нормализованных документов завершает задачу ошибкой.
