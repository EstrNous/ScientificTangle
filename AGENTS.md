# Правила работы агентов

**Каждый чат:** следуй этому файлу и `docs/agent_context/task_router.md`.

Единый источник hard rules (L0). Детали — в `docs/agent_context/rules_full.md`.

## Hard rules

- Рабочие ветки: `feat/*` по умолчанию; `dev` — только по явному запросу; `main` не трогать.
- Перед задачей: `git fetch origin`; на `feat/*` — `git rebase origin/dev`; на `dev` — `git pull --ff-only origin dev`.
- В `dev` не мержить локально: интеграция `feat/*` → PR на GitHub. Детали: `docs/agent_context/git_workflow.md`.
- Push: после rebase на `origin/dev` и тестов; на `feat/*` при необходимости `--force-with-lease`; never force в `dev`/`main`.
- Коммиты: `feat: сделано то-то` — одна строка, русский, без scope; в истории описывать только результат, без упоминания IDE-агентов.
- `README.md` не менять без явного запроса.
- В коде без комментариев; исключения — только внешний формат, лицензия, генератор, миграция, линтер, юридическое требование.
- Python-пакеты сервисов (`services/<name>/app/`): локальные модули — `from .module`, `from ..module`; `shared.*` и внешние пакеты — абсолютные импорты. В тестах допустим `from app.*` через PYTHONPATH как точка входа сервиса.
- Evidence-first: confirmed claims только с `SourceSpan`; слабые/unsourced — candidate layer с reason codes.
- Документация на русском; при смене структуры — обновить `docs/agent_context/project_structure.md`.
- Минимально достаточные изменения; не хардкодить demo-ответы и факты без источников.
- Не менять shared contracts, public API, миграции, ontology, security без явного решения команды.

## Как читать контекст

Не читай все файлы подряд. Следуй `docs/agent_context/task_router.md`.

Эталон для каждого чата: `docs/agent_prompts/every_chat.md`.

Полное ТЗ: `docs/nauchny_klubok_top1_tz.md`. Сжатые выдержки: `docs/tz/`.

## Адаптеры платформ

Тонкие указатели на этот файл; правила не дублируют:

| Платформа | Файл |
|-----------|------|
| Codex / OpenAI | `AGENTS.md` |
| Claude Code | `CLAUDE.md` |
| Cursor | `.cursor/rules/project.mdc` |
| GitHub Copilot | `.github/copilot-instructions.md` |
| Zed / ZCode | `ZCODE.md`, `.zed/rules/project.md` |
