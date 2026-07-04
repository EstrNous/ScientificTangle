# E7 Backend/ML: operator runbook

Дата: 2026-07-04

## Назначение

Runbook описывает no-live эксплуатационный контур Backend/ML для НорСинтез после E6. Он не включает live model eval, Yandex smoke, live latency p95 и generated answer quality: эти проверки остаются `blocked_by_policy` до отдельного post-E7 разрешения.

## Чистый старт

Базовый запуск локального стека:

```powershell
git fetch origin
git switch dev
git pull --ff-only origin dev
python scripts/generate_auth_keys.py
docker compose up -d
```

Если нужно пересобрать контейнеры:

```powershell
docker compose build
docker compose up -d
```

Сброс локального стека удаляет volumes:

```powershell
docker compose down -v
```

## Seed и reset

Минимальный seed:

```powershell
make seed
```

No-live inventory отчёт:

```powershell
make seed-counts
```

Offline reseed gate:

```powershell
make reset-reseed-offline
```

Full reseed gate требует поднятый Docker stack и доступные PostgreSQL, Neo4j, Qdrant, MinIO:

```powershell
make reset-reseed
```

Если `reset-reseed` падает на внешней инфраструктуре, сначала проверить health сервисов и storage runbook DB-роли E7. Backend/ML не должен подменять storage failures demo-ответами или synthetic фактическими данными.

## Health

Быстрая проверка контейнеров:

```powershell
docker compose ps
```

Логи конкретного сервиса:

```powershell
make logs SERVICE=gateway
make logs SERVICE=orchestrator
make logs SERVICE=model
make logs SERVICE=retrieval
```

Backend/ML smoke без live models:

```powershell
python scripts/run_tests.py
```

Model service tests можно запускать только в deterministic/offline режиме. Не задавать `YANDEX_API_KEY` и не включать live smoke в рамках E0-E7.

## Offline eval

Основной no-live gate:

```powershell
python eval/offline_quality_gate.py
```

Makefile target:

```powershell
make eval-offline-quality
```

Gate пишет артефакты:

- `eval/reports/offline_readiness.json`;
- `eval/reports/offline_readiness.md`.

Опционально gate можно усилить заранее подготовленным offline report:

```powershell
python eval/offline_quality_gate.py --report eval/reports/latest.json
make eval-offline-quality EVAL_OFFLINE_ARGS="--report eval/reports/latest.json"
```

`eval/demo_quality_gate.py` без `--report` ожидаемо возвращает blocked overall, потому что live eval report отсутствует. Для no-live readiness использовать `eval/offline_quality_gate.py`.

## Интерпретация статусов

`pass` означает, что проверка закрыта offline-данными или deterministic кодом.

`warn` означает, что нет критического fail, но есть известные no-live ограничения.

`blocked_by_policy` означает запрет live model call в E0-E7. Такой статус не надо обходить моками, demo-ответами или commit-артефактами live answers.

`blocked_by_data` означает, что полный корпус ещё не нормализован до reviewed `SourceSpan` expectations. Временный demo `SourceSpan` для official MVP questions уже зафиксирован, но его нельзя выдавать за покрытие всего корпуса.

`fail` означает дефект gate. Исправление должно идти в роли-владельце и не должно затрагивать `services/orchestrator/app/service/service.py` refactor.

## Evidence-first правила

Confirmed artifacts допустимы только с `SourceSpan`.

Weak или unsourced результаты должны оставаться candidate layer с reason codes.

Generated answer quality from external models не является подтверждённой метрикой до post-E7 live plan.

Export должен повторно учитывать access scope и не включать restricted sources для неподходящей роли.

## Export и notifications

Authoritative export boundary после E5 остаётся в orchestrator: `POST /export` возвращает Markdown или JSON, а JSON-LD/PDF явно остаются backlog.

ML JSON-LD enrichment готов как model endpoint, но production export wiring для JSON-LD не подключён.

Notifications production flow закрыт для query conflict events. Runtime delivery для `ingestion_complete` и `interest_match` остаётся P1 risk до отдельной межсервисной доставки.

## Deferred live-model plan

После E7 и отдельного разрешения команды можно создать новый план:

1. Поднять clean stack с seed.
2. Настроить Yandex secrets через окружение, не коммитя `.env`.
3. Запустить Yandex smoke.
4. Запустить live eval на official questions и corpus regression suite.
5. Сравнить offline и live reports.
6. Зафиксировать live answer quality и latency p95 только в live artifacts.

До этого live checks остаются `blocked_by_policy`.

## Dependency на внешний refactor

Large refactor `services/orchestrator/app/service/service.py` принадлежит External Orchestrator Refactor Owner. E7 Backend/ML фиксирует операционные зависимости и риски, но не дробит этот god object и не переносит его обязанности.
