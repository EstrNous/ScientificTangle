# Промпт перед имплементацией

Читать при фичах, контрактах и нетривиальных изменениях. Для мелких фиксов достаточно `task_router.md`.

1. Определи тип задачи в `docs/agent_context/task_router.md` и прочитай перечисленные файлы.
2. Git: `docs/agent_context/git_workflow.md` — по умолчанию `feat/*`, не локальный merge в `dev`.
3. `git fetch origin`; на `feat/*` — `git rebase origin/dev` (или создай feat от актуального `dev`).
4. Найди существующие контракты, тесты, стиль решения.
5. Для Python-сервиса: в `app/` — relative imports; `shared.*` — абсолютный.
6. Для model/evidence-first: confirmed → `SourceSpan`; слабое → candidates с reason codes.
7. Сформулируй план, риски, критерии проверки.
8. Только после этого меняй код.

Не начинай с больших файлов. Не добавляй комментарии в код.
