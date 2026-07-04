# Параллельный план улучшений Top-1

Документ задаёт порядок реализации улучшений качества ответа для трёх специалистов:

- `Backend/ML-1` — данные, нормализация, graph/eval quality.
- `Backend/ML-2` — retrieval, evidence verification, synthesis, backend wiring.
- `Frontend` — chat UX, source/auth cleanup, streaming/status UI.

План рассчитан на работу через отдельных агентов в новых чатах. Один чат берёт одну карточку: конкретный этап и конкретную роль.

## Общий протокол

- Каждый агент начинает с `AGENTS.md`, `docs/agent_context/task_router.md` и этого файла.
- Перед работой агент выполняет `git fetch origin`; рабочая база — свежий `origin/dev`.
- Каждая карточка выполняется в отдельной ветке `feat/top1-e<N>-<role>-<slug>`.
- Агент делает минимальный scope, прогоняет релевантные проверки, коммитит и пушит ветку.
- Агент не мержит в `dev`; интеграция идёт через PR на GitHub.
- Следующий этап начинается только после merge в `dev` всех PR предыдущего этапа.
- Если карточка требует ещё не смерженных изменений другой роли, она останавливается и фиксирует dependency вместо обходного решения.
- Если задача пересекается с внешним backend closure plan или чужими активными PR, она переносится в E5.

Шаблон команды для нового чата:

```text
Следуй AGENTS.md и docs/agent_context/task_router.md.
Выполни docs/agent_context/top1_parallel_execution_plan.md: этап E<N>, роль <Backend/ML-1|Backend/ML-2|Frontend>.
Работай в ветке feat/top1-e<N>-<role>-<slug>.
После реализации сделай коммит и push. В dev не мержи.
```

## Этапы и merge gates

| Этап | Backend/ML-1 | Backend/ML-2 | Frontend | Gate перед следующим этапом |
|---|---|---|---|---|
| E0. Baseline и аудит | `feat/top1-e0-bm1-eval-baseline` | `feat/top1-e0-bm2-contract-audit` | `feat/top1-e0-fe-ui-audit` | Все audit/spec PR merged в `dev` |
| E1. Safe foundation | `feat/top1-e1-bm1-fact-contracts` | `feat/top1-e1-bm2-ml-policy` | `feat/top1-e1-fe-chat-state` | Contract/spec/UI prep merged |
| E2. Data и retrieval base | `feat/top1-e2-bm1-normalization` | `feat/top1-e2-bm2-retrieval-planner` | `feat/top1-e2-fe-source-adapter` | Data/retrieval/UI prep merged |
| E3. Graph, evidence, answer | `feat/top1-e3-bm1-graph-exact` | `feat/top1-e3-bm2-evidence-synthesis` | `feat/top1-e3-fe-answer-renderer` | Evidence/answer shape merged |
| E4. Wiring и UX | `feat/top1-e4-bm1-eval-regression` | `feat/top1-e4-bm2-orchestrator-wiring` | `feat/top1-e4-fe-streaming-ux` | End-to-end feature-flagged flow merged |
| E5. После внешних backend merges | `feat/top1-e5-bm1-integration-eval` | `feat/top1-e5-bm2-live-transport-auth` | `feat/top1-e5-fe-live-cleanup` | Conflict-prone integrations merged |
| E6. Demo hardening | `feat/top1-e6-bm1-demo-quality` | `feat/top1-e6-bm2-perf-reliability` | `feat/top1-e6-fe-demo-polish` | Demo-ready PRs merged |

## E0. Baseline и аудит

Цель этапа — зафиксировать текущее состояние и не начать реализацию поверх неясных контрактов.

### Backend/ML-1: eval baseline

Ветка: `feat/top1-e0-bm1-eval-baseline`.

Что сделать:

- Проверить текущие `eval/`, `demo/official_questions.md`, `scripts/*eval*`, `Makefile`.
- Зафиксировать, какие demo/eval артефакты уже есть, какие плавающие, какие нельзя считать baseline.
- Подготовить документированный список gaps для pinned demo artifact, official questions, unsupported claims, evidence coverage.
- Не менять production query path.

Выход:

- Короткий markdown-отчёт в `docs/agent_context/` или обновление существующего eval/status документа.
- Коммит с результатом аудита и рекомендацией, какие проверки станут обязательными в E4/E6.

### Backend/ML-2: contract audit

Ветка: `feat/top1-e0-bm2-contract-audit`.

Что сделать:

- Проверить `shared/contracts/`, `services/model/app/contracts.py`, `services/retrieval/`, `services/orchestrator/app/api/query.py`, `services/gateway/app/api/query.py`.
- Описать текущие поля Query IR, EvidenceBundle, SourceSpan, QueryRunPayload и answer payload.
- Отделить уже стабильные поля от тех, которые нельзя менять без явного решения команды.
- Не добавлять новые DTO, если без этого можно обойтись аудитом.

Выход:

- Contract audit для будущих карточек E1-E4.
- Список contract freeze points и мест, где изменения допустимы только после merge gate.

### Frontend: UI audit

Ветка: `feat/top1-e0-fe-ui-audit`.

Что сделать:

- Найти компоненты, которые используют mock source refs, dev RoleSwitcher, chat answer renderer, loading states.
- Проверить `ui/src/api/`, `ui/src/components/chat/`, `ui/src/layout/`, `ui/src/stores/`.
- Составить список touchpoints для streaming, animated statuses, live source resolver и auth cleanup.
- Не удалять mock refs и RoleSwitcher на этом этапе.

Выход:

- UI audit с точными файлами и future-safe границами.
- Перечень того, что можно делать до backend readiness, и того, что переносится в E5.

## E1. Safe foundation

Цель этапа — подготовить спецификации и безопасные интерфейсные точки без рискованного production wiring.

### Backend/ML-1: fact contracts

Ветка: `feat/top1-e1-bm1-fact-contracts`.

Что сделать:

- На основе E0 определить минимальные структуры для normalized quantities, time, geo, aliases и table evidence.
- Если существующих контрактов достаточно, оформить это как документированное решение без изменения shared contracts.
- Если нужны изменения, добавить только минимальные backward-compatible поля с тестами.
- Не менять ontology, миграции и security.

Выход:

- Минимальный contract layer или явная запись, что E2 работает на существующих структурах.
- Тесты shared/model contracts, если были изменены модели.

### Backend/ML-2: ML policy

Ветка: `feat/top1-e1-bm2-ml-policy`.

Что сделать:

- Формализовать классы запросов: semantic, numeric, geo, temporal, comparative, graph-centric, mixed.
- Описать retrieval planner rules, verification reason codes, AnswerPayloadV2 expectations и synthesis policy.
- Подготовить prompt/template policy для scientific answer synthesis без подключения к production query flow.
- Не менять Qdrant adapters, orchestrator flow и gateway API.

Выход:

- Логическая спецификация planner, verification и synthesis.
- Набор reason codes: `outside_time_range`, `geo_mismatch`, `unit_mismatch`, `unsupported_claim`, `unresolved_alias`, `inaccessible_source`.

### Frontend: chat state foundation

Ветка: `feat/top1-e1-fe-chat-state`.

Что сделать:

- Подготовить UI state machine для chat answer lifecycle: parsing, retrieval, verification, synthesis, citations, done, degraded.
- Добавить graceful fallback для non-streaming ответа.
- Подготовить animated status engine на клиенте без реального transport streaming.
- Не менять live API contracts.

Выход:

- UI-компоненты/утилиты, которые можно подключить к реальным backend events в E4/E5.
- Тесты на state transitions, если в проекте уже есть подходящий тестовый слой.

## E2. Data и retrieval base

Цель этапа — дать системе нормализованные данные и deterministic retrieval planning.

### Backend/ML-1: normalization

Ветка: `feat/top1-e2-bm1-normalization`.

Что сделать:

- Реализовать или усилить извлечение normalized quantities, units, time, geo и aliases в ingestion/knowledge boundary.
- Обеспечить сохранение provenance через SourceSpan или существующие claim/measurement ids.
- Добавить coverage report по документам, таблицам, measurements и claims.
- Не реализовывать retrieval fusion.

Выход:

- Данные корпуса пригодны для строгой фильтрации.
- Есть проверки на numeric/time/geo/alias normalization и сохранение provenance.

### Backend/ML-2: retrieval planner

Ветка: `feat/top1-e2-bm2-retrieval-planner`.

Что сделать:

- Добавить deterministic `RetrievalPlan` или эквивалентный внутренний объект на основе Query IR.
- Включить trace: какие retrievers выбраны, какие фильтры применены, почему.
- Подготовить routing для semantic, lexical, table, numeric, geo, time, graph modes без обязательного полного fusion.
- Не трогать graph exact implementation из E3.

Выход:

- Retrieval service умеет объяснить план поиска.
- Есть тесты planner profiles и trace.

### Frontend: source adapter

Ветка: `feat/top1-e2-fe-source-adapter`.

Что сделать:

- Выделить source resolver abstraction в UI.
- Сохранить mock mode, но убрать прямое размазывание mock source refs по компонентам там, где это безопасно.
- Подготовить renderer hooks для future live source refs.
- Не удалять mock layer полностью.

Выход:

- UI готов к переключению mock/live source boundary в E5.
- Список оставшихся mock dependencies явно зафиксирован.

## E3. Graph, evidence, answer

Цель этапа — добавить точный graph search, evidence verification и новый формат ответа без финального production переключения.

### Backend/ML-1: graph exact search

Ветка: `feat/top1-e3-bm1-graph-exact`.

Что сделать:

- Подготовить `GraphQuerySpec` или эквивалентную структуру из Query IR.
- Добавить Cypher-шаблоны для entity-property, entity-process-measurement, geo-indicator, period-observation, comparison, conflicts, missing data.
- Возвращать `source_span_ids`, `claim_ids`, `measurement_ids` для EvidenceBundle.
- Не превращать UI graph endpoint в retrieval endpoint.

Выход:

- Neo4j становится retrieval candidate source, а не только визуализацией.
- Есть fallback: no graph evidence, partial graph evidence, graph contradiction.

### Backend/ML-2: evidence synthesis

Ветка: `feat/top1-e3-bm2-evidence-synthesis`.

Что сделать:

- Реализовать разделение evidence на verified, candidate, conflicting, unsupported.
- Применить reason codes из E1 к numeric/time/geo/entity/source filters.
- Усилить answer synthesis так, чтобы unsupported claims не попадали в confirmed layer.
- Подготовить AnswerPayloadV2 или совместимый internal payload с facts, limits, conflicts, gaps, follow-up.

Выход:

- Synthesis строится на verified evidence и явно отдаёт warnings/gaps/conflicts.
- Тесты покрывают unsupported synthesis ban и SourceSpan requirements.

### Frontend: answer renderer

Ветка: `feat/top1-e3-fe-answer-renderer`.

Что сделать:

- Добавить renderer для short answer, confirmed observations, limitations, conflicts, gaps, follow-up steps.
- Поддержать reason codes и degraded/partial evidence states на mock payloads.
- Не требовать финального backend AnswerPayloadV2, если он ещё не смержен.

Выход:

- Chat UI умеет показать новый scientific answer shape.
- Есть fallback на старый payload до E4/E5.

## E4. Wiring и UX

Цель этапа — собрать feature-flagged end-to-end flow после merge E1-E3.

### Backend/ML-1: eval regression

Ветка: `feat/top1-e4-bm1-eval-regression`.

Что сделать:

- Зафиксировать pinned demo artifact, checksum/version и правила обновления.
- Разделить suites: official questions, hybrid retrieval, access filtering, unsupported claims, answer completeness.
- Добавить regression report для comparison до/после.

Выход:

- Quality gate готов для E6 и последующих PR.
- Demo/eval больше не зависит от плавающего корпуса.

### Backend/ML-2: orchestrator wiring

Ветка: `feat/top1-e4-bm2-orchestrator-wiring`.

Что сделать:

- Подключить planner, graph/table candidates, verification и synthesis в query path за feature flag.
- Обновить gateway/orchestrator/retrieval/model wiring только после merge E1-E3.
- Сохранить backward-compatible fallback.
- Не подключать внешние source/auth/streaming изменения, если они ещё в чужих PR.

Выход:

- End-to-end query flow работает в staged/flagged режиме.
- Тесты покрывают fallback и новый flow.

### Frontend: streaming UX

Ветка: `feat/top1-e4-fe-streaming-ux`.

Что сделать:

- Подключить UI state machine к доступным backend events, если E4 backend уже даёт их.
- Если transport ещё не готов, оставить authoritative fallback на non-streaming mode.
- Подготовить growing markdown renderer и status transitions без layout shifts.

Выход:

- UI одинаково работает в streaming и non-streaming сценариях.
- Feature flag включает новый UX без удаления старого поведения.

## E5. После внешних backend merges

Цель этапа — выполнить конфликтные интеграции только после стабилизации чужих backend PR.

### Backend/ML-1: integration eval

Ветка: `feat/top1-e5-bm1-integration-eval`.

Что сделать:

- Проверить merged source/search/graph/auth/export changes против pinned eval.
- Зафиксировать regressions и contract drift.
- Не исправлять unrelated backend issues в этой ветке.

Выход:

- Интеграционный eval report.
- Список обязательных fixes перед E6.

### Backend/ML-2: live transport and auth

Ветка: `feat/top1-e5-bm2-live-transport-auth`.

Что сделать:

- Подключить live streaming transport, source refs, auth/session claims и export/notification dependencies только после их стабилизации.
- Убрать временные adapters только там, где есть stable replacement.
- Сохранить feature flags для rollback.

Выход:

- Backend live dependencies готовы для UI cleanup.
- Нет локального merge в `dev`.

### Frontend: live cleanup

Ветка: `feat/top1-e5-fe-live-cleanup`.

Что сделать:

- Перевести компоненты с mock source refs на live source resolver.
- Убрать dev RoleSwitcher из production path после готовности auth/session flow.
- Подключить реальные streaming/status events.
- Не удалять dev-only инструменты, если они нужны для локального mock режима и явно изолированы.

Выход:

- Production chat/source/auth UX работает на live contracts.
- Mock mode остаётся только как осознанный dev/test boundary.

## E6. Demo hardening

Цель этапа — довести систему до демонстрационного состояния и защитить от регрессий.

### Backend/ML-1: demo quality

Ветка: `feat/top1-e6-bm1-demo-quality`.

Что сделать:

- Прогнать official questions и regression suites.
- Проверить unsupported claim rate, SourceSpan coverage, answer completeness, conflict/gap behavior.
- Подготовить финальный quality report.

Выход:

- Demo quality report с понятным pass/fail.
- Список известных ограничений без маскировки demo-ответами.

### Backend/ML-2: perf reliability

Ветка: `feat/top1-e6-bm2-perf-reliability`.

Что сделать:

- Прогнать query path smoke/perf checks.
- Проверить degraded mode, fallback, timeout/retry behavior.
- Убедиться, что feature flags не ломают default flow.

Выход:

- Perf/reliability report.
- Исправления только в пределах query path reliability.

### Frontend: demo polish

Ветка: `feat/top1-e6-fe-demo-polish`.

Что сделать:

- Проверить chat UX на desktop/mobile.
- Убедиться, что статусы, sources, warnings, conflicts и gaps не перекрываются и не ломают layout.
- Убрать визуальный шум, оставив рабочий интерфейс без маркетинговых экранов.

Выход:

- UI готов к demo flow.
- Состояния loading, partial, degraded, empty и error проверены.

## Что делать только после backend readiness

Эти задачи запрещено брать до E5, если нет явно смерженного backend основания:

- удаление `api/mock/` source refs из живых компонентов;
- удаление dev RoleSwitcher из основного сценария;
- подключение реального streaming transport;
- подключение actual graph/source/search trace в UI;
- финальный перевод production chat на AnswerPayloadV2;
- интеграция export/notification dependencies в UI flows.

## Минимальный quality gate для каждой карточки

- `git diff --check`.
- `git status -sb` перед коммитом.
- Релевантные unit/integration/UI тесты по затронутой зоне.
- Если тесты не запускались, агент обязан написать причину в финальном ответе.
- Коммит одной строкой на русском в формате `feat: сделано то-то`.
- Push только своей `feat/*` ветки; после rebase — только `--force-with-lease` и только для своей feature-ветки.
