# Домен: notification

Порт 8008.

## Статус

`not_wired` — HTTP-сервис отдаёт только `/health` и `/ready`.

## Что уже есть

- **Model:** `POST /v1/notifications/match`, `POST /v1/interests/extract` — scoring готов
- **DB-слой:** `infra/postgres/notification_db/` — `UserInterest`, `Notification`, Alembic миграция
- **Compose:** Redis и postgres подключены для planned pub/sub

## Backlog

CRUD interests, worker сопоставления с новыми источниками, доставка уведомлений в UI (`NotificationBell`).
