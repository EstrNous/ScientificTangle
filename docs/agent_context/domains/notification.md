# Домен: notification

Порт 8008.

## Статус

`wired` — HTTP-сервис владеет `notification_db`, отдаёт interests/notifications API и internal events.

## API

- `GET/PUT /interests` — профиль интересов (JWT)
- `GET /notifications?since=`, `POST /notifications/read-all`, `POST /notifications/{id}/read` — список и прочтение (JWT)
- `POST /internal/v1/events` — создание уведомления (service-to-service, gateway chat conflicts)
- `POST /internal/v1/match` — offline match через model `/v1/notifications/match`

Gateway проксирует user-facing routes на `NOTIFICATION_URL`; UI по-прежнему ходит в `/api/*`.

## Что уже есть

- **Model:** `POST /v1/notifications/match`, `POST /v1/interests/extract`
- **DB-слой:** `infra/postgres/notification_db/` — миграции на старте notification container
- **Runtime:** `conflict_detected` из gateway chat → internal events

## Gaps

- Internal endpoints `/internal/v1/events` и `/internal/v1/match` пока без service-to-service auth.
- Runtime delivery после ingestion (`ingestion_complete` / `interest_match`) не доведена до полного event flow.

## Backlog

- Orchestrator post-ingestion `ingestion_complete` / `interest_match` runtime delivery
- Redis pub/sub worker
- Cursor pagination в gateway `GET /notifications`
