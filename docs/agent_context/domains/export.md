# Домен: export

Порт 8007. Заглушка HTTP; DB-слой готов в `infra/postgres/export_db/`.

## Статус

`not_wired` — сервис отдаёт только `/health`; `ExportJob` в отдельной БД export_db, согласован с orchestrator_db.
