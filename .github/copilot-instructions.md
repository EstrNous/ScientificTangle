# Инструкции для GitHub Copilot

Используй обязательный контекст проекта:

- `AGENTS.md`
- `docs/nauchny_klubok_top1_tz.md`
- `docs/agent_prompts/system.md`
- `docs/agent_prompts/before_implementation.md`
- `docs/agent_context/project_structure.md`
- `docs/agent_context/sync_rules.md`

Работай строго по ТЗ: перед имплементацией продумай план, риски и проверку, не добавляй комментарии в код, веди документацию на русском, обновляй общий агентный контекст при изменении структуры, не меняй `README.md` без отдельного явного запроса. Коммиты должны быть в формате `feat: сделано то-то`: одна строка, русский язык, без scope.
