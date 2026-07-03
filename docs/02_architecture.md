# Архитектура системы Научный Клубок

## Обзор

Микросервисная архитектура для доказательной карты R&D знаний горно-металлургической отрасли. Каждый сервис — отдельное приложение на FastAPI с собственным Dockerfile, healthcheck, логами и зоной ответственности.

## Карта сервисов

| Сервис | Директория | Порт | Зона ответственности |
|--------|-----------|------|---------------------|
| UI | `ui/` | 3000 | Чат, поиск, загрузка, source viewer, граф, таблицы, review console, dashboard, admin |
| API Gateway / BFF | `services/gateway/` | 8000 | Внешние API, валидация DTO, request_id, streaming, авторизация на входе, маршрутизация, нормализация ошибок |
| Auth / Security / Audit | `services/auth_audit/` | 8001 | Роли, access policy, audit log, правила доступа, настройки администратора, retention policy |
| Orchestrator | `services/orchestrator/` | 8002 | Пайплайны ingestion, query, review, evaluation, export, notification; состояние задач, retries, timeouts |
| Ingestion | `services/ingestion/` | 8003 | Загрузка, парсинг, NormalizedDocument, TableBlock, SourceSpan, классификация, метаданные |
| Knowledge | `services/knowledge/` | 8004 | Schema Registry, доменный профиль, справочники, сущности, entity resolution, claims, граф |
| Retrieval | `services/retrieval/` | 8005 | Query IR, retrieval plan, entity linking, hybrid search (graph + dense + sparse + table + numeric + geo), fusion, reranking, EvidenceBundle |
| Model | `services/model/` | 8006 | LLM, embeddings, reranking, structured extraction, prompt templates, model routing, caching |
| Export | `services/export/` | 8007 | Markdown, PDF, JSON, JSON-LD, evidence bundle |
| Notification | `services/notification/` | 8008 | Профиль интересов, сопоставление с новыми источниками, уведомления |

## Хранилища данных

| Хранилище | Порт | Назначение |
|-----------|------|-----------|
| PostgreSQL 16 | 5432 | Пользователи, роли, audit log, задачи ingestion/query, экспорты, уведомления, интересы, состояние сервисов |
| Neo4j 5 Community | 7474/7687 | Граф знаний, schema registry, сущности, отношения, claims, measurements, source span metadata, review decisions |
| Qdrant | 6333/6334 | Векторы document chunks, source spans, table rows, captions, conclusions |
| MinIO (S3) | 9000/9001 | Исходные файлы, нормализованные артефакты, экспорты, демо-архивы, временные файлы |
| Redis 7 | 6379 | Фоновые задачи, статусы, блокировки, кэш, ограничение нагрузки |

## Общий код

`shared/` — общий пакет, подключаемый через `pyproject.toml` каждого сервиса:
- `shared/contracts/` — Pydantic-модели DTO (NormalizedDocument, SourceSpan, TableBlock, Claim, QueryIR, EvidenceBundle, AnswerPayload, ServiceInfo)
- `shared/utils/` — утилиты (generate_request_id)
- `shared/logging/` — единая конфигурация structlog (JSON-формат, контекст сервиса)
- `shared/config/` — базовый класс Settings с подключениями ко всем хранилищам

## Маршрутизация (nginx)

nginx (порт 80) проксирует запросы по prefix:
- `/api/` → gateway:8000
- `/auth/` → auth_audit:8001
- `/orchestrator/` → orchestrator:8002
- `/ingestion/` → ingestion:8003
- `/knowledge/` → knowledge:8004
- `/retrieval/` → retrieval:8005
- `/model/` → model:8006
- `/export/` → export:8007
- `/notification/` → notification:8008
- `/` → ui:3000

## Healthcheck

Каждый сервис предоставляет три эндпоинта:
- `GET /health` — живой ли сервис
- `GET /ready` — готов ли к приему запросов
- `GET /metrics` — базовая метрика (имя, версия)

Prometheus (infra/monitoring/prometheus.yml) опрашивает `/metrics` всех сервисов каждые 15 секунд.

## Структура сервиса

```
services/<name>/
  app/
    __init__.py
    main.py          — точка входа FastAPI (lifespan, routers)
    api/
      __init__.py
      health.py      — /health, /ready, /metrics
    core/
      __init__.py
      config.py      — Settings (ServiceSettings из shared)
      logging.py     — setup_logging
  tests/
    __init__.py
  Dockerfile         — python:3.12-slim + uv + healthcheck
  pyproject.toml     — зависимости + shared как path dependency
```

## Запуск

```bash
cp .env.example .env
make up      # docker compose up -d — все сервисы + инфраструктура
make build   # пересборка образов
make down    # остановка и удаление томов
make logs    # логи (SERVICE=<name> для фильтра)
```

## Онтология

`ontology/` содержит YAML-схемы:
- `core_schema.yaml` — базовая онтология (типы сущностей, связи, единицы)
- `domain_pack_mining_metallurgy.yaml` — доменный профиль горно-металлургии
- `validation_rules.yaml` — правила валидации данных

## Справочники

`dictionaries/` — заготовки для справочных данных по материалам, оборудованию, свойствам, единицам, экспертам, тегам.

## Оценка качества

`eval/` содержит:
- `gold_questions.json` — эталонные вопросы с ожидаемыми типами ответов
- `run_eval.py` — скрипт для запуска оценки через API
