# E0 Backend/ML: baseline контрактов, API и eval

**Ветка:** `feat/nornikel-e0-bml-contract-audit`
**Дата:** 2026-07-04
**Scope:** только аудит `shared/contracts`, gateway/orchestrator/model/retrieval/export/notification API и eval inputs. Production behavior не менялся. Live model вызовы не запускались.

Связанные документы: [`nornikel_parallel_execution_plan.md`](nornikel_parallel_execution_plan.md), [`nornikel_e0_db_baseline.md`](nornikel_e0_db_baseline.md), [`nornikel_e0_fe_ui_audit.md`](nornikel_e0_fe_ui_audit.md).

## 1. Текущее покрытие контрактов

| Область | Текущий контракт | Статус | Файлы |
|---|---|---|---|
| Query run | `QueryRunPayload`, `QueryRunResponse`, `QueryIR`, `EvidenceBundle`, `AnswerPayload` | stable для текущего query path | `shared/contracts/models.py`, `services/gateway/app/api/query.py`, `services/orchestrator/app/api/query.py` |
| Source | `SourceSpan`, `SourcePayload`, `SearchResultPayload` | есть базовый payload с offsets и access policy; нет явных highlight/bindings полей | `shared/contracts/models.py`, `services/retrieval/app/api/query.py` |
| Export | `ExportRequest`, `ExportPayload` | есть direct markdown/json response из orchestrator; отдельный `services/export` пока health-only | `shared/contracts/models.py`, `services/orchestrator/app/api/query.py`, `services/export/app/main.py` |
| Notifications | `NotificationMatchRequest/Response` есть только в model service; gateway list/read возвращает `list[dict]` | частично | `services/model/app/contracts.py`, `services/gateway/app/api/notifications.py` |
| User interests | `UserInterestExtractionRequest/Response` есть только в model service | частично; нет пользовательского GET/PUT API | `services/model/app/contracts.py`, `services/model/app/api/v1.py` |
| Strategic/eval dashboard | `StrategicEvaluationPayload` есть для UI dashboard | не является eval report artifact contract | `shared/contracts/models.py`, `services/gateway/app/api/admin.py` |
| Audit | `AuditEvent` есть, list endpoint с limit/offset/action/user_id | базово покрыто | `shared/contracts/models.py`, `services/gateway/app/api/admin.py`, `services/orchestrator/app/api/audit.py` |
| Evidence-first model | confirmed artifacts требуют `SourceSpan`; candidates требуют reason codes | covered | `services/model/app/contracts.py` |

## 2. API baseline

### Gateway

- Query/export/source/search: `POST /query`, `POST /query/stream`, `GET /runs/{run_id}`, `POST /export`, `GET /source/{source_span_id}`, `GET /graph/subgraph`, `GET /search`.
- Documents: `POST /documents/upload`, `GET /tasks/{task_id}`.
- Dictionaries: upload/list/active/activate endpoints.
- Notifications: `GET /notifications`, `POST /notifications/read-all`, `POST /notifications/{notification_id}/read`.
- Admin/audit/analytics: admin summary, stats, audit events, strategic metrics/evaluation, lab coverage, user/policy patch.

Gaps: нет `GET/PUT /interests`, нет `DELETE /documents/{document_id}`, нет review queue/decision endpoints, notifications не имеют typed shared payload и `since` cursor, export не имеет async job list/result API.

### Orchestrator

- Query/export/source/search mirror: `POST /query/run`, `POST /query/stream`, `GET /runs/{run_id}`, `POST /export`, `GET /source/{source_span_id}`, `GET /graph/subgraph`, `GET /search`.
- Ingestion/dictionaries/audit endpoints существуют.

Gaps: нет review API, interests API, document delete API. `services/orchestrator/app/service/service.py` не трогался в этой карточке.

### Model service

`services/model/app/api/v1.py` содержит 13 v1 endpoints: schemas, prompts, status, embeddings, structured extraction, query-ir, rerank, answer synthesis, conflicts, gaps, interests extraction, notification matching, jsonld enrichment.

No-live baseline: deterministic fallback доступен; Yandex provider остается opt-in через env. Live smoke `services/model/tests/test_yandex_live_smoke.py` требует `RUN_MODEL_TESTS=1` и credentials, поэтому для E0 помечен `blocked_by_policy`.

### Retrieval

`services/retrieval/app/api/query.py` содержит bootstrap/reset/index/plan/query/search/source resolve. Qdrant payload indexes включают `source_span_id`, `source_type`, `document_source_type`, `access_level`, `allowed_roles`, numeric/time/geo/dictionary поля.

Gaps для будущих этапов: source resolve возвращает 404 `source_not_found` для denied/missing, нет typed `access_denied` payload; `SourcePayload` не содержит highlight ranges, row/column bindings или page rendering metadata.

### Export и notification services

`services/export` и `services/notification` сейчас включают health/ready/metrics/error handlers, но не имеют product endpoints. Рабочие product API на E0 находятся в gateway/orchestrator или model service.

## 3. Missing DTO и контрактные gaps

| DTO / payload | Текущее состояние | Нужный владелец этапа |
|---|---|---|
| `ReviewDecisionPayload` | отсутствует в shared/model/gateway/orchestrator | Backend/ML E1 после DB foundation |
| Review queue item/result | отсутствует | Backend/ML E1/E3 |
| Interests profile GET/PUT payload | отсутствует; есть только model extraction response | Backend/ML E1/E3 |
| Notification product payload | gateway возвращает `list[dict]`; нет shared typed list item, cursor, match result reference payload | Backend/ML E1/E5 |
| Delete document result | отсутствует; нет delete endpoint | Backend/ML E1/E3 после DB/storage ownership |
| Export job payload | есть direct `ExportPayload`; нет async job status/result/list contract | Backend/ML E1/E5 |
| Eval report payload | `StrategicEvaluationPayload` не покрывает `eval/run_eval.py` report schema, suites, blocked reasons и artifact metadata | Backend/ML E1/E6 |
| Source highlight fields | `SourceSpan` хранит offsets/text; `SourcePayload` не задает highlight ranges/snippet/page/table row bindings | Backend/ML E1/E4 совместно с Frontend |
| Conflict/gap ids in query payload | `EvidenceBundle.gaps/conflicts` сейчас `list[str]`; нет typed conflict/gap payload with ids and source refs | Backend/ML E2/E4 |

## 4. Eval и dataset baseline

| Артефакт | Состояние |
|---|---|
| `demo/official_questions.md` | mirror для `official-001` ... `official-004`; source of truth указан как `eval/gold_questions.json` |
| `eval/gold_questions.json` | schema `gold_questions.v2`; 4 official + 12 corpus-derived questions |
| Official expected spans | у всех 4 official вопросов `expected_source_span_ids` пустые; strict citation recall по official suite пока `blocked_by_data` |
| Corpus regression expected spans | у 12 corpus questions есть по одному expected span; у access filtering suite сейчас один corpus question |
| `eval/pinned_demo_artifact.json` | фиксирует input checksums и запрещает коммитить live model answers |
| `eval/regression_suites.json` | suites: `official_questions`, `hybrid_retrieval`, `access_filtering`, `unsupported_claims`, `answer_completeness` |
| `eval/reports/` | versioned reports в текущем tree отсутствуют |

Live gates:

| Gate | Статус E0 | Причина |
|---|---|---|
| Yandex live smoke | `blocked_by_policy` | требует live model credentials/call |
| Live official eval через `eval/run_eval.py` | `blocked_by_policy` | вызывает поднятый backend/model path и может использовать live model |
| Live answer quality | `blocked_by_policy` | E0-E7 запрещают generated live answer quality claims |
| Live latency p95 | `blocked_by_policy` | E0-E7 запрещают live latency p95 claims |

No-live проверки, которые можно использовать до E6:

- Contract/schema unit tests для `shared/contracts` и `services/model/tests/test_model_v1.py`.
- Runner/report unit tests без вызова внешних моделей, если они не требуют поднятого live stack.
- Static validation of pinned artifact checksums and suite references.

## 5. Dataset access checklist для E2

Где лежит corpus:

- Pinned normalized demo corpus: `demo/seed_data/mvp_normalized_documents.json`.
- Official questions: `eval/gold_questions.json` и mirror `demo/official_questions.md`.
- Corpus-derived reviewed candidates: `eval/gold_questions.json` поле `corpus_regression_questions`.
- Downloader внешнего публичного корпуса: `eval/yandex_disk_corpus.py`; output не pinned и зависит от внешнего состояния.

Как reviewить expected `SourceSpan`:

1. Запускать только offline/deterministic ingestion/retrieval path или использовать уже committed normalized corpus.
2. Для `official-001` выбрать spans по salts/Ca/Mg/Na 200-300 mg/l и dry residue <= 1000 mg/dm3.
3. Для `official-002` выбрать spans по catholyte circulation, nickel electrowinning и optimal flow speed.
4. Для `official-003` выбрать spans по Au/Ag/PGM, matte/slag и window "последние 5 лет"; дату окна фиксировать явно в eval metadata.
5. Для `official-004` выбрать spans по mine water injection, Russia/foreign practice и economics.
6. Каждый expected span должен быть воспроизводимым stable id из `shared.utils.source_span`, а не ручным текстовым ответом.
7. Если source id зависит от нового ingestion run и не воспроизводится из committed corpus, помечать `blocked_by_data`, а не подменять answer text.

Что нельзя коммитить:

- Live model answers, generated official answers или latency claims.
- Локальные outputs `eval/yandex_disk_corpus.py`, если они не оформлены отдельным pinned artifact с checksum.
- Secrets: `YANDEX_API_KEY`, `YANDEX_FOLDER_ID`, auth tokens, downloaded private corpus.
- Непроверенные facts без `SourceSpan`.

Работы, где нужен полный dataset и владелец Backend/ML:

| Работа | Этап | Статус после E0 |
|---|---|---|
| Reviewed expected spans for official questions | E2 | `blocked_by_data` до review corpus |
| Gap/conflict/review fixtures без live models | E2 | pending |
| Typed eval report payload and no-live report status | E1/E6 | pending |
| Offline retrieval quality report by channel | E4/E6 | pending |
| Live eval artifact | после E7 и отдельного разрешения | `blocked_by_policy` |

## 6. Dependencies

На момент E0 явной зависимости от несмёрженного PR другой роли для этой карточки не обнаружено. Будущие implementation stages зависят от DB foundation для delete/review/interests persistence и от Frontend source highlight requirements, но E0 audit не блокируется.
