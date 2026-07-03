# Git-workflow для агентов

Цель: не ломать `dev`, не копить конфликты, не мержить вслепую.

## Ветки

| Ветка | Кто пишет | Как попадает в `dev` |
|-------|-----------|----------------------|
| `main` | только человек | вручную из `dev` |
| `dev` | редко, мелкие правки с явным запросом | push напрямую только если пользователь попросил |
| `feat/*` | агент по умолчанию | **через PR на GitHub**, не локальный merge |

Агент **не делает локальный merge** `feat/*` → `dev` и **не мержит в `main`**.

## Старт задачи

```bash
git fetch origin
```

### Работа в `feat/*` (по умолчанию)

```bash
git switch dev
git pull --ff-only origin dev
git switch -c feat/<кратко-о-задаче>    # или switch на существующую feat/*
```

Если `feat/*` уже есть:

```bash
git switch feat/<имя>
git fetch origin
git rebase origin/dev
```

При конфликте на rebase — см. раздел «Конфликты». Не продолжай rebase вслепую.

### Прямая работа в `dev`

Только по явному запросу пользователя. Перед правками:

```bash
git switch dev
git fetch origin
git pull --ff-only origin dev
```

## Во время работы

- Короткоживущие `feat/*`; один логический scope на ветку.
- Перед долгой сессией или перед push снова: `git fetch origin` и `git rebase origin/dev` на `feat/*`.
- Минимальный diff; не трогать чужие незакоммиченные файлы.
- Не коммитить секреты, `.env`, локальные артефакты.

## Перед push

1. `git fetch origin`
2. На `feat/*`: `git rebase origin/dev` (предпочтительно) или, если rebase неуместен, `git merge origin/dev` **только внутри feat-ветки**
3. Прогнать релевантные тесты
4. `git status` — только нужные файлы
5. Push:

```bash
git push -u origin HEAD
```

После rebase, если ветка уже была на remote:

```bash
git push --force-with-lease origin HEAD
```

`--force-with-lease` — **только** для своей `feat/*`, **никогда** для `dev` и `main`.

## Интеграция в `dev` (без локального merge)

Стандартный путь:

1. Push `feat/*`
2. `gh pr create` → base `dev`
3. Дождаться CI / проверок
4. Merge через GitHub (squash или merge commit — как принято в репо)

Локальный merge в `dev` агенту **не нужен** и **не делается**, если пользователь явно не попросил.

## Проверка без merge в `dev`

Если нужно убедиться, что ветка сойдётся с `dev`:

**Вариант A — предпочтительный:** PR + CI на GitHub.

**Вариант B — локально, без изменения `dev`:**

```bash
git fetch origin
git branch backup/<имя-feat>-<дата> HEAD
git worktree add ../st-check-<имя> -b check/<имя> origin/dev
cd ../st-check-<имя>
git merge --no-ff --no-commit origin/feat/<имя>   # или merge локальной feat
# тесты; при конфликте — разобрать здесь
git merge --abort                                   # если только проверка
cd -
git worktree remove ../st-check-<имя>
```

Или одноразовая ветка:

```bash
git fetch origin
git branch backup/check-$(git rev-parse --short HEAD)
git switch -c check/feat-test origin/dev
git merge --no-commit feat/<имя>
# тесты → git merge --abort → git switch feat/<имя> → git branch -D check/feat-test
```

`dev` при этом остаётся на `origin/dev`.

## Конфликты

1. Остановись. Не делай `git checkout --ours` / `--theirs` на весь файл по умолчанию.
2. Открой каждый конфликтный файл; пойми обе стороны (`<<<<<<<`, `=======`, `>>>>>>>`).
3. Собери осмысленный итог: сохрани намеренные изменения с обеих сторон, убери дубли.
4. `git add` только после ручной правки. Для rebase: `git rebase --continue`. Для merge в feat: `git merge --continue`.
5. Прогони тесты затронутого кода.
6. Если не уверен — `git rebase --abort` или `git merge --abort`, опиши пользователю файлы и блокеры.

Запрещено:

- force-push в `dev` / `main`
- `git push --force` без `--force-with-lease` на shared-ветках
- оставлять conflict markers в коде
- «решать» конфликт удалением чужой логики без проверки

## Коммиты

Формат: `feat: сделано то-то` — одна строка, русский, без scope.

В коммитах и PR — только суть изменений, без упоминания IDE-агентов.

## Резервная копия перед риском

Перед rebase, force-with-lease или неочевидным разрешением конфликта:

```bash
git branch backup/<текущая-ветка>-<YYYYMMDD-HHMM> HEAD
```

## Если агент оказался в `main`

```bash
git switch dev
git pull --ff-only origin dev
git switch -c feat/<задача>
```

Не коммитить в `main`.
