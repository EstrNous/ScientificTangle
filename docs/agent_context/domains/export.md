# Домен: export

Порт 8007.

## Статус

`wired with gaps` — authoritative path: `POST /api/export` → gateway → `POST /export` в orchestrator → `POST /v1/jobs` в export → MinIO artifact. Gateway скачивает artifact напрямую из export через `GET /api/export/jobs/{id}/artifact`.

## Граница

- **Orchestrator (authoritative):** `export_jobs` + `export_artifacts` в `orchestrator_db`, access revalidation, audit `document_exported`, вызов export service
- **Export service:** рендер Markdown/JSON/JSON-LD, upload в MinIO bucket `exports`, job status cache (Redis/in-memory), status/download API

Export payload включает answer, evidence, sources, graph, gaps, conflicts, `QueryIR`, `retrieval_trace`, role/access scope, warnings и `latency_ms`. Перед выдачей orchestrator повторно resolve-ит каждый `SourceSpan`; при drift доступа возвращается `export_access_changed` и пишется audit `access_denied`.

## API

| Endpoint | Назначение |
|----------|------------|
| `POST /v1/jobs` | Создать и обработать export job (internal, orchestrator) |
| `GET /v1/jobs/{id}` | Статус job (JWT) |
| `GET /v1/jobs/{id}/artifact` | Скачать артефакт из MinIO (JWT) |
| Gateway `GET /api/export/jobs/{id}/artifact` | Proxy download |

## Форматы

- `markdown`, `json` — из export document
- `jsonld` — export service вызывает model enrichment
- `pdf` — backlog (P3)

## Зависимости

MinIO (`exports`), Redis, model (JSON-LD), auth_audit/JWT principal, orchestrator (caller), gateway (download proxy).

## Gaps

- Internal `POST /v1/jobs` пока не защищён service-to-service auth.
- PDF renderer не подключён.
