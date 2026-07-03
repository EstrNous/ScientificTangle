# ZCode / Zed Agent Instructions

Перед любыми изменениями прочитай:

- `AGENTS.md`
- `docs/nauchny_klubok_top1_tz.md`
- `docs/agent_prompts/system.md`
- `docs/agent_prompts/before_implementation.md`
- `docs/agent_context/project_structure.md`
- `docs/agent_context/sync_rules.md`

Главные ограничения:

- Работать строго по ТЗ.
- Перед кодом обдумывать план и риски.
- Перед началом работы стянуть актуальный `dev`: `git fetch origin dev` и `git pull --ff-only origin dev`.
- Работать только в `dev` или `feat/*`.
- Новые `feat/*` ветки создавать только от актуального локального `dev`.
- В `main` не работать, не пушить и не мержить; перенос из `dev` в `main` делает человек вручную.
- Перед push, PR или merge создавать проверочную копию ветки.
- В коммитах, push/PR-описаниях и публичной истории не упоминать Cursor, Codex, Claude, Antigravity, ZCode или другую агентную систему; описывать только результат работы.
- Не добавлять комментарии в код.
- Вести документацию на русском.
- Обновлять общий агентный контекст при изменении структуры.
- Не трогать `README.md` без явного запроса.
- Держать изменения минимальными.
- Коммиты писать в формате `feat: сделано то-то`.
