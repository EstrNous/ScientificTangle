# Маршрутизатор контекста по типу задачи

**Каждый чат:** следуй `AGENTS.md` и этим маршрутам. Читай только перечисленные файлы. Не загружай полное ТЗ без необходимости.

## Всегда (L0)

`AGENTS.md` — подхватывается платформой автоматически или через адаптер.

## ML / model service

1. `docs/agent_context/domains/model.md`
2. `docs/agent_context/ml_mvp_status.md`
3. `services/model/app/`, `services/model/tests/`, `shared/contracts/` по задаче

## Быстрый фикс, тест, рефакторинг в одном сервисе

1. `docs/agent_context/domains/<service>.md` — если есть; иначе релевантный раздел `docs/agent_context/project_structure.md`
2. Файлы сервиса, контракты, тесты по задаче

## Новый endpoint, контракт, DTO

1. `docs/tz/contracts.md`
2. `shared/contracts/` и OpenAPI затронутого сервиса
3. `docs/agent_prompts/before_implementation.md`
4. Доменный файл из `docs/agent_context/domains/`

## Фича / MVP-функциональность

1. `docs/tz/mvp.md`
2. `docs/tz/agent_constraints.md`
3. `docs/agent_prompts/before_implementation.md`
4. `docs/agent_context/project_structure.md` — только затронутые разделы

## Архитектура, кросс-сервисные изменения

1. `docs/tz/index.md` — выбрать нужные секции полного ТЗ
2. `docs/nauchny_klubok_top1_tz.md` — только выбранные секции, не целиком
3. `docs/agent_context/rules_full.md`
4. `docs/agent_prompts/before_implementation.md`

## Изменение структуры репозитория или агентных правил

1. `docs/agent_context/sync_rules.md`
2. `docs/agent_context/project_structure.md`
3. `AGENTS.md` и при необходимости `docs/agent_context/rules_full.md`

## Перед коммитом или PR

1. `docs/agent_prompts/quality_gate.md`
2. `docs/agent_context/git_workflow.md` — если push, rebase или PR

## Оценка реализации vs ТЗ, обновление документации

1. `docs/tz/mvp.md` — чеклист MVP
2. `docs/agent_context/implementation_quality_report.md` — сводная оценка
3. `docs/agent_context/audit_report.md` — P0/P1 gaps
4. `docs/agent_context/ml_mvp_status.md` — ML slice
5. `docs/agent_context/domains/` — статусы по сервисам
6. `docs/agent_context/project_structure.md` — при смене структуры

## Новый чат

Шаблон: `docs/agent_prompts/new_chat.md`
