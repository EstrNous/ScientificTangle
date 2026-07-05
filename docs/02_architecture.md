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

**Dev** (`docker-compose.dev.yml`, `nginx.dev.conf`): nginx на порту 80 проксирует:

- `/api/` → gateway:8000
- `/api/auth/` → auth_audit:8001
- `/.well-known/jwks.json` → auth_audit:8001
- `/orchestrator/`, `/ingestion/`, `/knowledge/`, `/retrieval/`, `/model/` → прямые debug routes (только dev)
- `/grafana/` → grafana:3000 (basic auth)
- `/` → ui:3000

**Prod** (`docker-compose.prod.yml`, `nginx.prod.conf.template`): только HTTPS edge:

- `/api/*`, `/api/auth/`, `/.well-known/jwks.json` → auth_audit / gateway
- `/grafana/` → grafana (basic auth)
- `/health` → gateway probe
- `/` → ui
- export/notification — только через gateway `/api/*`, наружу не публикуются

Product API path: UI → nginx `/api` → gateway → orchestrator / notification / export.

## Healthcheck

Каждый сервис предоставляет три эндпоинта:
- `GET /health` — живой ли сервис
- `GET /ready` — готов ли к приему запросов
- `GET /metrics` — Prometheus exposition format (HTTP counters и histogram latency)

Prometheus ([`infra/monitoring/prometheus.yml`](infra/monitoring/prometheus.yml)) опрашивает `/metrics` всех сервисов каждые 15 секунд. Grafana доступна по `http://localhost/grafana/` (nginx basic auth, credentials в `.env`).

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
      dependencies.py — сборка зависимостей прикладного слоя
      logging.py     — setup_logging
    db/              — модели, сессии и репозитории сервиса при наличии БД
    service/         — прикладная логика и адаптеры внешних систем
  storage/           — Alembic-миграции сервиса при наличии собственной схемы
  tests/
    __init__.py
  Dockerfile         — python:3.12-slim + uv + healthcheck
  pyproject.toml     — зависимости + shared как path dependency
```

## Запуск

```bash
cp .env.example .env
make up          # dev: compose + dev overlay, все host ports
make prod        # prod: .env + TLS + закрытый периметр + seed
make prod-demo   # prod + demo corpus
make build
make down
make logs        # SERVICE=<name> для фильтра
```

Prod runbook: [`docs/agent_context/prod_compose_runbook.md`](agent_context/prod_compose_runbook.md).

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

## Статус реализации (2026-07-04)

Ядро end-to-end pipeline реализовано: ingestion → Neo4j → Qdrant → query → answer в UI.

| Компонент | Статус |
|-----------|--------|
| 9 backend-сервисов в compose | ✅ все подняты |
| auth_audit (JWT, RBAC, audit) | ✅ |
| ingestion (parsers, MinIO) | ✅ |
| knowledge (Neo4j live) | ✅ |
| retrieval (Qdrant live) | ⚠️ vector + rerank; graph/table/lexical fusion — backlog |
| model (13 v1 endpoints, Yandex + fallback) | ✅ |
| orchestrator (ingestion + query + export) | ✅ |
| gateway (BFF, chat_db) | ✅ |
| export / notification microservices | ⚠️ HTTP-заглушки; логика частично в orchestrator/model |
| UI (15 страниц, real API) | ⚠️ mock source catalog в части компонентов |

Детали: [`docs/agent_context/implementation_quality_report.md`](agent_context/implementation_quality_report.md), пайплайн запроса: [`docs/agent_context/query_pipeline.md`](agent_context/query_pipeline.md).
