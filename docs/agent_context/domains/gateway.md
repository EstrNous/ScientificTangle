# Домен: gateway

Порт 8000. API Gateway / BFF.

## Ключевые файлы

- `services/gateway/app/` — маршрутизация, валидация DTO, request_id, streaming
- `shared/contracts/` — внешние DTO

## Зависимости

Все внутренние сервисы; health-агрегация для UI.
