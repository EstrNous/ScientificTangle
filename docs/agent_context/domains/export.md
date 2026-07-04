# Домен: export

Порт 8007.

## Статус

`wired with gaps` (~86%) — authoritative path: `POST /api/export` → gateway → `POST /export` в orchestrator → `POST /v1/jobs` в export → MinIO artifact. Gateway скачивает artifact через `GET /api/export/jobs/{id}/artifact`.

## Граница

- **Orchestrator (authoritative):** `export_jobs` + `export_artifacts` в `orchestrator_db`, access revalidation, audit `document_exported`, вызов export service с `X-Internal-Service-Token`
- **Export service:** рендер Markdown/JSON/JSON-LD, upload в MinIO bucket `exports`, job status cache (Redis/in-memory), status/download API

Export payload включает answer, evidence, sources, graph, gaps, conflicts, `QueryIR`, `retrieval_trace`, role/access scope, warnings и `latency_ms`. Перед выдачей orchestrator повторно resolve-ит каждый `SourceSpan`; при drift доступа возвращается `export_access_changed` и пишется audit `access_denied`.

## API

| Endpoint | Назначение |
|----------|------------|
| `POST /v1/jobs` | Создать и обработать export job (internal, `require_internal_service`) |
| `GET /v1/jobs/{id}` | Статус job (JWT) |
| `GET /v1/jobs/{id}/artifact` | Скачать артефакт из MinIO (JWT) |
| Gateway `GET /api/export/jobs/{id}/artifact` | Proxy download |

## Форматы

- `markdown`, `json`, `jsonld` — реализованы в export service
- `pdf` — backlog

## Зависимости

MinIO (`exports`), Redis, model (JSON-LD enrich), auth_audit/JWT principal, orchestrator (caller с service token), gateway (download proxy).

## Gaps

- PDF renderer не подключён.
- Async queue и retention policy для больших export jobs — backlog.
