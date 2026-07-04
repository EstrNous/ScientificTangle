# Домен: notification

Порт **8008**. Владелец **`notification_db`**.

## Статус реализации

| Область | Статус | Примечание |
|---------|--------|------------|
| HTTP API (interests, list/read) | **готово** | JWT, gateway proxy `/api/*` |
| Internal API (`/internal/v1/events`, `/match`) | **готово** | `X-Internal-Service-Token` |
| Runtime `ingestion_complete` | **готово** | orchestrator после ingestion pipeline |
| Runtime `interest_match` | **готово** | orchestrator → `/internal/v1/match` |
| Runtime `conflict_detected` | **готово** | gateway chat → `/internal/v1/events` |
| Dedup `(user_id, type, reference_id)` | **готово** | миграция `0005`, idempotent insert |
| Cursor pagination | **готово** | `GET /notifications?cursor=`, `next_cursor` |
| Redis pub/sub delivery worker | **готово** | фоновый worker + publish `created` |
| UI poll + toast | **готово** | `NotificationBell`, `?since=` |
| Push / SSE / WebSocket в UI | **не сделано** | подписчик на `created` channel — backlog gateway/UI |

**Итог:** product notification path закрыт для MVP; live push в браузер — отдельная задача.

## Архитектура доставки

```text
Orchestrator ──HTTP──► POST /internal/v1/events|match ──► notification_db
Gateway chat ──HTTP──► POST /internal/v1/events (conflict_detected)

Любой producer ──Redis──► scientific_tangle:notifications:delivery
                              │
                              ▼
                    NotificationDeliveryWorker
                              │
                              ▼
                         notification_db
                              │
                              ▼
              publish scientific_tangle:notifications:created
                              │
                              ▼
                    (будущий SSE/WebSocket gateway)
```

**Основной путь в compose:** HTTP internal API (orchestrator, gateway).  
**Альтернатива:** publish в Redis delivery channel (тот же payload, что internal API).

## API

### Публичные (JWT)

| Method | Path | Описание |
|--------|------|----------|
| GET | `/interests` | Профиль интересов |
| PUT | `/interests` | Сохранение; при пустых `interests` — model `/v1/interests/extract` |
| GET | `/notifications?since=&cursor=` | Список; `since` — poll новых, `cursor` — keyset pagination |
| POST | `/notifications/read-all` | Прочитать все |
| POST | `/notifications/{id}/read` | Прочитать одно |

Ответ списка: `NotificationListPayload` — `items`, `unread_count`, `next_cursor`.

### Internal (service token)

| Method | Path | Описание |
|--------|------|----------|
| POST | `/internal/v1/events` | Создать уведомление |
| POST | `/internal/v1/match` | Interest match через model `/v1/notifications/match` |

После persist публикуется событие в Redis `created` channel (если pub/sub включён).

## Продуктовые решения

| Событие | Получатель | `reference_id` | `reference_type` |
|---------|------------|----------------|------------------|
| `ingestion_complete` | uploader (`task.user_id`) | `str(ingestion_task.id)` | `ingestion_task` |
| `interest_match` | uploader | `document_id` | `document` |
| `conflict_detected` | пользователь query | `query_run` id | `query_run` |

- Одно `ingestion_complete` на ingestion task.
- `interest_match` — вызов `/match` на документ с непустыми artifacts.
- Повторная доставка с тем же `(user_id, type, reference_id)` не создаёт дубль.

## Redis pub/sub

| Channel | Назначение | Формат |
|---------|------------|--------|
| `scientific_tangle:notifications:delivery` | Вход worker: создать уведомление | `{"kind":"event"\|"match","request_id":"...","payload":{...}}` |
| `scientific_tangle:notifications:created` | Выход: уведомление сохранено | `{"request_id":"...","notification":{...NotificationPayload}}` |

`kind=event` — payload как `NotificationEventCreate`.  
`kind=match` — payload как `InternalMatchRequest` (`user_id`, `document_id`, `artifacts`).

Worker стартует в lifespan notification container; `/ready` требует running worker, если `NOTIFICATION_REDIS_PUBSUB_ENABLED=true`.

## Конфигурация (env)

| Переменная | Default | Описание |
|------------|---------|----------|
| `NOTIFICATION_URL` | `http://notification:8008` | URL для orchestrator/gateway |
| `NOTIFICATION_LIST_LIMIT` | `20` | Размер страницы списка |
| `MATCH_SCORE_THRESHOLD` | `0.4` | Порог model match |
| `NOTIFICATION_REDIS_PUBSUB_ENABLED` | `true` | Redis worker on/off |
| `NOTIFICATION_REDIS_DELIVERY_CHANNEL` | `scientific_tangle:notifications:delivery` | Вход worker |
| `NOTIFICATION_REDIS_CREATED_CHANNEL` | `scientific_tangle:notifications:created` | Fan-out после persist |
| `INTERNAL_SERVICE_TOKEN` | — | Обязателен для internal API |
| `REDIS_URL` | `redis://redis:6379/0` | Redis из `ServiceSettings` |

Локальные тесты: `NOTIFICATION_REDIS_PUBSUB_ENABLED=false`.

## DB и миграции

`infra/postgres/notification_db/storage/versions/` — `0001`…`0005`.

- `0005` — unique index `uq_notifications_user_type_reference_id`.

Миграции при старте notification container (`Dockerfile` CMD).

## Код сервиса

| Путь | Роль |
|------|------|
| `app/api/factory.py` | Lifespan: DB, JWKS, Redis bus, delivery worker |
| `app/api/notifications.py`, `interests.py`, `events.py` | Routes |
| `app/service/notification_service.py` | CRUD, interests |
| `app/service/matching_service.py` | Model match |
| `app/service/delivery_handler.py` | Обработка Redis/единый create path |
| `app/service/delivery_worker.py` | Subscribe delivery channel |
| `app/service/redis_bus.py` | Publish created/delivery |

## Интеграции

| Caller | Как |
|--------|-----|
| Gateway | Proxy JWT API; conflicts → internal events |
| Orchestrator | HTTP internal после `_run_ingestion_pipeline` |
| UI | Gateway `/api/notifications`, poll `since` |
| Будущие producers | HTTP internal **или** Redis delivery channel |

## Backlog (после MVP)

- Gateway SSE/WebSocket подписка на `created` channel (убрать poll-only UX).
- Orchestrator опциональный publish в Redis вместо HTTP (сейчас только HTTP).
- Scheduled purge notifications (retention 90 дней — manual ops).
