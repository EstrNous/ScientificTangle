# Правила умной синхронизации агентов

## Цель

Один контекст для всех агентных систем при минимальном расходе токенов.

## Уровни контекста

| Уровень | Файлы | Когда |
|---------|-------|-------|
| L0 | `AGENTS.md`, `docs/agent_prompts/every_chat.md` | Всегда |
| L1 | `task_router.md`, `rules_full.md`, `git_workflow.md`, `docs/tz/*` | По типу задачи |
| L2 | `docs/agent_prompts/before_implementation.md` | Фичи, контракты |
| L3 | `docs/agent_prompts/quality_gate.md` | Перед коммитом/PR |
| Справочно | `docs/nauchny_klubok_top1_tz.md`, `project_structure.md` | Только нужные секции |

## Обязательные файлы

- `AGENTS.md` — единственный источник hard rules
- `docs/agent_context/task_router.md` — маршрутизация чтения
- `docs/agent_context/rules_full.md` — расширенные правила
- `docs/tz/` — сжатые выдержки из ТЗ
- `docs/agent_context/project_structure.md` — карта репозитория
- `docs/agent_context/implementation_quality_report.md` — статус реализации vs ТЗ (обновлять при значимых изменениях)

## Правило синхронного обновления

Меняется общее правило → обнови `AGENTS.md` (и при необходимости `rules_full.md`, `docs/agent_prompts/`, `docs/tz/`).

Меняется статус реализации сервиса или инфра → обнови `domains/<service>.md`, при необходимости `audit_report.md`, `ml_mvp_status.md`, `implementation_quality_report.md`, `docs/tz/mvp.md`.

Адаптеры платформ (`CLAUDE.md`, `ZCODE.md`, `.cursor/rules/`, `.github/copilot-instructions.md`, `.zed/rules/`) — **только указатели**, без дублирования правил.

## Git-синхронизация

Полный workflow: `docs/agent_context/git_workflow.md`.

- Ветки: `feat/*` по умолчанию; `dev` — по запросу; не `main`.
- `git fetch origin` перед работой и перед push.
- На `feat/*`: `git rebase origin/dev`; интеграция в `dev` через PR, без локального merge.
- Конфликты: ручное разрешение + тесты; backup-ветка перед рискованным rebase.
- В коммитах и PR — только результат работы, без упоминания IDE-агентов.

## Документация и код

- Документация на русском.
- Без комментариев в коде (кроме обязательных внешних).
- Confirmed claims только с `SourceSpan`.
- Relative imports в `services/*/app/` (`from .`, `from ..`); `shared.*` — абсолютный. В тестах допустим `from app.*` через PYTHONPATH.

## Платформы

| Платформа | Точка входа |
|-----------|-------------|
| Codex | `AGENTS.md` |
| Claude Code | `CLAUDE.md` → `AGENTS.md` |
| Cursor | `.cursor/rules/project.mdc` → `AGENTS.md` |
| GitHub Copilot | `.github/copilot-instructions.md` → `AGENTS.md` |
| Zed / ZCode | `ZCODE.md`, `.zed/rules/project.md` → `AGENTS.md` |
