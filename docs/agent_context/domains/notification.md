# Домен: notification

Порт 8008.

## Статус

`wired with gaps` (~82%) — HTTP-сервис владеет `notification_db`, отдаёт interests/notifications API и internal events с service token.

## API

- `GET/PUT /interests` — профиль интересов (JWT)
- `GET /notifications?since=`, `POST /notifications/read-all`, `POST /notifications/{id}/read` — список и прочтение (JWT)
- `POST /internal/v1/events` — создание уведомления (`require_internal_service`; gateway chat conflicts)
- `POST /internal/v1/match` — offline match через model `/v1/notifications/match` (`require_internal_service`)

Gateway проксирует user-facing routes на `NOTIFICATION_URL`; UI ходит в `/api/*`.

## Что уже есть

- **Model:** `POST /v1/notifications/match`, `POST /v1/interests/extract`
- **DB-слой:** `infra/postgres/notification_db/` — миграции на старте notification container
- **Runtime:** `conflict_detected` из gateway chat → internal events
- **Security:** `X-Internal-Service-Token` на router `/internal/v1/*` (`shared/web/auth.py`)

## Gaps

- Runtime delivery после ingestion (`ingestion_complete` / `interest_match`) — orchestrator hook не подключён; данные есть в seed/fixtures.
- Cursor pagination в gateway `GET /notifications` — backlog.
- WebSocket/SSE — опционально post-MVP.

## Backlog

- Orchestrator post-ingestion `ingestion_complete` / `interest_match` runtime delivery
- Redis pub/sub worker (опционально)
