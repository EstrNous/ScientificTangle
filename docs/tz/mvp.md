# MVP: точка отсечки

Выдержка из `docs/nauchny_klubok_top1_tz.md` §6 и §33. Полный текст — в основном ТЗ.

**Статус реализации (2026-07-04):** ~85% чеклиста закрыт. Детали — [`implementation_quality_report.md`](../agent_context/implementation_quality_report.md).

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

## Чеклист vs код (2026-07-04)

| Пункт | Статус | Комментарий |
|-------|--------|-------------|
| Стек поднимается | ✅ | docker-compose + healthchecks |
| UI и Gateway отвечают | ✅ | real API в compose (`VITE_USE_MOCK=false`) |
| ingestion → NormalizedDocument → SourceSpan | ✅ | parsers + MinIO |
| claims в Neo4j | ✅ | Neo4jKnowledgeAdapter |
| chunks в Qdrant | ✅ | `st_evidence_v1`, seed_demo |
| Query IR + retrieval | ✅ | hybrid retrieval: dense + lexical + table + graph fusion, planner trace, rerank |
| ответ в чат с таблицей и графом | ✅ | ChatPage, EvidenceTable, LocalGraph |
| geo/numeric фильтры базово | ✅ | Query IR + Qdrant filters: units/ranges, geo bucket/country, published year |
| audit и роли | ✅ backend / ⚠️ UI | RoleSwitcher в dev |
| export Markdown/JSON | ✅ MVP via orchestrator/gateway | `POST /api/export` → `POST /export`; `services/export` reserved boundary |
| demo script готов | ✅ | `make seed`, `make eval`, `scripts/seed_demo.py` |
| ≥4 официальных вопроса | ⚠️ | dataset готов; pinned live eval artifact — нет |

Без полного закрытия ⚠️ — не переходить к полировке и top-1 фичам.
