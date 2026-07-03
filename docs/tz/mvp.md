# MVP: точка отсечки

Выдержка из `docs/nauchny_klubok_top1_tz.md` §6 и §33. Полный текст — в основном ТЗ.

## Когда MVP готов

Команда проходит полный end-to-end без ручных правок в БД и консоли в момент демо.

## Обязательный pipeline

Загрузка файлов/ZIP → исходники → парсинг → NormalizedDocument → SourceSpan → справочники → сущности → числа → claims → Neo4j → Qdrant (chunks/table rows) → Query IR → гибридный + графовый + табличный поиск → fusion → проверка источников → ответ в UI (таблица, источники, локальный граф).

## Обязательные свойства

- Ответы на ≥4 официальных вопроса в базовом виде; каждая ключевая строка — с источником.
- Числа выделены; география хотя бы: отечественная / зарубежная / неизвестно.
- Unsupported claims явно помечены.
- Роли: админ, исследователь, внешний партнёр; access policy на документы.
- Audit log: запросы, просмотры источников, экспорт.
- Воспроизводимый запуск: docker compose, `.env.example`, Makefile, seed, healthchecks.

## Чеклист (кратко)

Стек поднимается; UI и Gateway отвечают; ingestion task → NormalizedDocument → SourceSpan; claims в Neo4j; chunks в Qdrant; Query IR + retrieval + fusion; ответ в чат с таблицей и графом; geo/numeric фильтры базово; audit и роли; export Markdown/JSON; demo script готов.

Без этого — не переходить к полировке и top-1 фичам.
