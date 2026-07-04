# Домен: export

Порт 8007.

## Статус

`wired` — HTTP API, MinIO artifacts, orchestrator integration, JSON-LD через model.

## Граница

- **Orchestrator (authoritative):** `export_jobs` + `export_artifacts` в `orchestrator_db`, access revalidation, audit `document_exported`
- **Export service:** рендер Markdown/JSON/JSON-LD, upload в MinIO bucket `exports`, job status cache (Redis/in-memory), download API

## API

| Endpoint | Назначение |
|----------|------------|
| `POST /v1/jobs` | Создать и обработать export job (internal, orchestrator) |
| `GET /v1/jobs/{id}` | Статус job (JWT) |
| `GET /v1/jobs/{id}/artifact` | Скачать артефакт из MinIO (JWT) |
| Gateway `GET /api/export/jobs/{id}/artifact` | Proxy download |

## Форматы

- `markdown`, `json` — из export document
- `jsonld` — `POST model/v1/jsonld/enrich`
- `pdf` — backlog (P3)

## Зависимости

MinIO (`exports`), Redis, model (JSON-LD), orchestrator (caller).
