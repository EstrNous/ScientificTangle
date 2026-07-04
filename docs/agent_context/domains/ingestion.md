# Домен: ingestion

Порт 8003. Загрузка, парсинг, NormalizedDocument.

## Ключевые файлы

- `services/ingestion/app/api/documents.py` — normalize endpoints
- `services/ingestion/app/parsers/` — реестр адаптеров PDF, DOCX, PPTX, DOC и ZIP
- `services/ingestion/app/service/storage.py` — MinIO bucket `source-files`
- `shared/contracts/` — NormalizedDocument, SourceSpan, TableBlock

## Pipeline

Файл/ZIP → task → MinIO → нормализация → NormalizedDocument → SourceSpan → Knowledge → Retrieval.

Legacy DOC конвертируется в DOCX через LibreOffice headless. Небезопасные и превышающие лимиты ZIP отклоняются. Ошибка отдельного файла фиксируется как warning; отсутствие нормализованных документов завершает задачу ошибкой.

## Текущий статус (2026-07-04)

**Реализовано:** upload через orchestrator, SHA-256, MinIO, parsers для PDF/DOCX/PPTX/DOC/ZIP, `POST /v1/documents/normalize` для text/table fallback.

**Gaps:** VL/OCR не обязателен для MVP; сканы и изображения без текстового слоя — backlog.
