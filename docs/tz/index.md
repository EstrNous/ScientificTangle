# Навигация по ТЗ

Полный документ: `docs/nauchny_klubok_top1_tz.md`. Читай целевые секции, не весь файл.

## Сжатые выдержки для агентов

| Файл | Содержание |
|------|------------|
| `docs/tz/mvp.md` | Definition of Done MVP, чеклист + статус реализации |
| `docs/tz/agent_constraints.md` | Принципы, запреты, правила для агентов |
| `docs/tz/contracts.md` | Shared DTO и точки синхронизации |

## Статус реализации vs ТЗ

| Документ | Назначение |
|----------|------------|
| [`implementation_quality_report.md`](../agent_context/implementation_quality_report.md) | Полная оценка по сервисам, стеку, gaps |
| [`ml_mvp_status.md`](../agent_context/ml_mvp_status.md) | ML/model slice |
| [`audit_report.md`](../agent_context/audit_report.md) | P0/P1 аудит, инфра-статусы |
| [`query_pipeline.md`](../agent_context/query_pipeline.md) | Сквозной query path |

## Секции полного ТЗ

| Секция | Тема |
|--------|------|
| §1–5 | Цель продукта, хакатон, demo-сценарии |
| §6, §33 | MVP cutoff и чеклист → также `docs/tz/mvp.md` |
| §8 | Продуктовые принципы → также `docs/tz/agent_constraints.md` |
| §12–14 | Архитектура, ingestion, query |
| §16 | Безопасность и аудит |
| §20 | Структура репозитория |
| §28 | Точки синхронизации → также `docs/tz/contracts.md` |
| §35, §37 | Правила агентов, запреты → также `docs/tz/agent_constraints.md` |
