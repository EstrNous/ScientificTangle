# E5 Backend/ML-1: integration eval

**Дата:** 2026-07-04  
**Ветка:** `feat/top1-e5-bm1-integration-eval`  
**Scope:** проверка merged source/search/graph/auth/export изменений против pinned eval без запуска реальных моделей.

## Результат

E5 проверил внешний backend merge `2ae38cf` (`feat/backend-mvp-followup`) поверх E4 gate. Production query path не менялся, live eval не запускался.

Проверенные зоны merge:

- source/search: `services/retrieval/app/api/query.py`, `services/retrieval/app/qdrant_adapter.py`;
- graph: `services/knowledge/adapters/neo4j_adapter.py`, `services/knowledge/app/api/graph.py`;
- auth/access: повторная фильтрация source/search/evidence по ролям и `access_levels`;
- export: `services/orchestrator/app/service/service.py` revalidates source access before export;
- dictionary pinning: `shared/contracts/models.py`, `services/orchestrator/storage/versions/0007_add_dictionary_pinning.py`, `services/*/app/api/dictionaries.py`;
- eval gates: `eval/run_eval.py`, `eval/pinned_demo_artifact.json`, `eval/regression_suites.json`, `tests/e2e/test_official_questions_smoke.py`.

## Pinned eval integrity

Pinned inputs не изменились после внешнего backend merge:

| Файл | Manifest sha256 | Текущий sha256 | Статус |
|---|---|---|---|
| `eval/gold_questions.json` | `8f98910198215edd37de23716f02bcc1f47fdbde91e383ff5d1a05cf5d3c12a0` | `8f98910198215edd37de23716f02bcc1f47fdbde91e383ff5d1a05cf5d3c12a0` | ok |
| `demo/seed_data/mvp_normalized_documents.json` | `4b1131075f0219e83138138b63ed4b1ee450e400b074a75c89267de58eeacb08` | `4b1131075f0219e83138138b63ed4b1ee450e400b074a75c89267de58eeacb08` | ok |
| `demo/official_questions.md` | `967204c1fbdad4fbc74d725662c53f047aadfc9cf66f0273492adf5f57853a25` | `967204c1fbdad4fbc74d725662c53f047aadfc9cf66f0273492adf5f57853a25` | ok |

Вывод: E5 не требует пересоздания pinned artifact. Реальные ответы моделей по-прежнему нельзя коммитить в `eval/pinned_demo_artifact.json` или рядом с ним.

## Contract drift

Зафиксированный drift после backend follow-up:

| ID | Зона | Изменение | Риск для eval | Статус |
|---|---|---|---|---|
| E5-D-01 | `QueryRunPayload` | добавлено optional `dictionary_version_id` | runner не ломается, но live `/query` теперь зависит от active dictionary в orchestrator | E6 preflight required |
| E5-D-02 | `IngestionTaskPayload` | добавлены `task_kind`, `dictionary_version_id`, union report | additive для eval; важно для demo seed и audit events | accepted |
| E5-D-03 | Retrieval payload | добавлены `published_year`, `dictionary_version_id`, lower-case geo payload keys | влияет на time/geo filtering; pinned inputs не менялись | watch in live suite |
| E5-D-04 | Source/search access | source resolve, search и rerank path повторно фильтруют access | ожидаемое усиление; access suite должен остаться `access_leak_rate=0.0` | must verify live |
| E5-D-05 | Export | export revalidates source access and returns `export_access_changed` on drift | правильно для security; eval runner это не покрывает | covered by orchestrator tests |
| E5-D-06 | E2E official smoke | тест теперь seed-ит dictionary, query, source, graph, search, export, audit | полный gate требует stack и реальные сервисы; не запускать до разрешения моделей | deferred |

Breaking drift в frozen `SourceSpan`, `EvidenceItem.source_span`, `AnswerPayload.answer_text/confidence` и `QueryRunPayload` core fields не найден. Добавления в shared contracts backward-compatible.

## Regression status

Локальные проверки карточки должны оставаться без live model calls:

- `python -m pytest tests/integration/test_eval_runner.py tests/integration/test_access_leak.py` — passed, 8 tests;
- `python -m pytest shared/tests/test_contracts.py` — passed, 7 tests;
- `python -m pytest services/retrieval/tests/test_query.py` with retrieval `PYTHONPATH` — failed: `test_denied_evidence_is_not_sent_to_reranking` sees allowed evidence only, but `source_span.document_id` drifted from source document id `allowed` to stable span id `e626250896e8bd3d` before rerank;
- `python -m pytest services/orchestrator/tests/test_query_service.py` with orchestrator `PYTHONPATH` — not collected in this environment because `sqlalchemy` is not installed;
- `git diff --check` — passed.

Live проверки не выполнялись, потому что организаторы запретили запускать реальные модели. Команды E4 `eval/run_eval.py --suite ...` остаются только для seeded stack после отдельного разрешения.

## Обязательные fixes перед E6

Перед E6 `demo-quality` необходимо:

1. Добавить preflight в live eval runbook: active dictionary должен быть создан и активирован до `/api/query`, иначе запросы завершатся `active_dictionary_required`.
2. Запускать live eval только после `scripts/seed_demo.py` или эквивалентного seed-пайплайна, который фиксирует `dictionary_version_id` в ingestion/query metadata.
3. Для `access_filtering` расширить fixture beyond `corpus-001`: нужны reviewed forbidden spans после auth-backed corpus review.
4. Для export/source regression добавить отдельный live smoke вне `eval/run_eval.py`, потому что текущий runner проверяет только `/api/query`.
5. Разобрать retrieval source identity drift до E6: либо восстановить исходный `document_id` в rerank evidence, либо явно закрепить новый контракт, если `document_id == source_span_id` стал намеренным internal shape.
6. Перед финальным gate подготовить окружение с orchestrator test dependencies (`sqlalchemy` и service deps), чтобы `services/orchestrator/tests/test_query_service.py` был обязательной проверкой.
7. После разрешения моделей сохранить только Markdown/JSON reports в `eval/reports/`, не менять pinned inputs и не коммитить live model answers как baseline artifact.

## Dependency

На момент проверки `origin/dev` содержит E4 PR #56, #57, #58 и backend follow-up PR #59. Явного blocker на несмёрженный PR другой роли для этой E5 Backend/ML-1 карточки не обнаружено. E6 всё ещё зависит от разрешения на live model/seeded stack run и от готовности команды принять live eval artifact.
