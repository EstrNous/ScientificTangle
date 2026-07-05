# Промпт проверки качества

Перед коммитом, push, rebase или PR.

## Продукт и код

- Соответствует ли решение `docs/tz/mvp.md` и `docs/tz/agent_constraints.md`?
- Нет фич вне задачи; MVP end-to-end не сломан?
- Provenance для фактов; нет confirmed без `SourceSpan`?
- В `services/*/app/` нет `from app.*`; `shared.*` абсолютный?
- Нет лишних комментариев; документация на русском?
- `project_structure.md` обновлён при смене структуры?

## Git

- Ветка `feat/*` (или `dev` только по явному запросу); не `main`?
- Был `git fetch origin`; feat синхронизирована с `origin/dev` (rebase)?
- Нет локального merge в `dev`?
- Push только после тестов; на feat допустим `--force-with-lease`, не в `dev`/`main`?
- Нет conflict markers в файлах?
- `git status` чистый по задуманным файлам?
- Коммит: `feat: сделано то-то`?
- В истории нет упоминаний IDE-агентов?

См. `docs/agent_context/git_workflow.md`.

## Ограничения

- `README.md`, contracts, security, миграции — не тронуты без запроса?
- `AGENTS.md` синхронизирован, если менялись общие правила?
- Тесты/сборка пройдены?
