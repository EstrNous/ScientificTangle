# Домен: export

Порт 8007.

## Статус

`not_wired` — HTTP-сервис отдаёт только `/health` и `/ready`.

## Что уже есть

- **Orchestrator:** `POST /export` → `export_query_run` — Markdown/JSON в памяти, `ExportJob` в `orchestrator_db`
- **Gateway:** `POST /api/export` — proxy в orchestrator
- **UI:** `ui/src/utils/reportExport.js` — клиентский экспорт MD/JSON/PDF
- **Model:** `POST /v1/jsonld/enrich` — JSON-LD payload готов, wiring в export service отсутствует
- **DB-слой:** `infra/postgres/export_db/` — схема готова, не используется сервисом

## Backlog

HTTP API export service, MinIO для артефактов, JSON-LD через model endpoint, server-side PDF.
