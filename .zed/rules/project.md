# ScientificTangle Agent Rules

Перед работой прочитай:

- `AGENTS.md`
- `docs/nauchny_klubok_top1_tz.md`
- `docs/agent_prompts/system.md`
- `docs/agent_prompts/before_implementation.md`
- `docs/agent_context/project_structure.md`
- `docs/agent_context/sync_rules.md`

Правила:

- Работай только в `dev` или `feat/*`.
- В `main` не работай, не пушь и не мержь; перенос из `dev` в `main` делает человек вручную.
- Перед push, PR или merge создавай проверочную копию ветки.
- В коммитах, push/PR-описаниях и публичной истории не упоминай Cursor, Codex, Claude, Antigravity, ZCode или другую агентную систему; описывай только результат работы.
- Не добавляй комментарии в код.
- Документацию веди на русском.
- При изменении структуры проекта обновляй общий агентный контекст.
- Не меняй `README.md` без отдельного явного запроса.
- Коммиты: `feat: сделано то-то`, одна строка, русский язык, без scope.
