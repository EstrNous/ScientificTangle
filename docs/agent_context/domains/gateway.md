# Домен: gateway

Порт 8000. API Gateway / BFF.

## Ключевые файлы

- `services/gateway/app/` — маршрутизация, валидация DTO, request_id, streaming
- `shared/contracts/` — внешние DTO

Query API включает синхронный запуск с сохранением результата, чтение run, SourceSpan, локального графа и access-aware поиск.

## Зависимости

Все внутренние сервисы; health-агрегация для UI.
