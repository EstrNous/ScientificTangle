# E0 Backend/ML-1: eval baseline audit

**Дата:** 2026-07-04
**Ветка:** `feat/top1-e0-bm1-eval-baseline`
**Scope:** аудит `eval/`, `demo/official_questions.md`, `scripts/*eval*`, `Makefile`; production query path не менялся.

## Вывод

В репозитории уже есть минимальная eval-инфраструктура для Top-1: `eval/gold_questions.json`, `eval/run_eval.py`, `demo/official_questions.md`, `scripts/eval_yandex_live.py`, цель `make eval` и тесты отдельных метрик runner-а. Это пригодно как стартовая спецификация вопросов и метрик, но ещё не является pinned demo baseline.

Baseline сейчас нельзя считать воспроизводимым, потому что в git нет committed `eval/reports/latest.*` или versioned live report, нет checksum/version для demo corpus, official questions не привязаны к `SourceSpan`, а corpus-derived regression set сгенерирован из узкого корпуса и содержит повторяющиеся формулировки.

## Найденные артефакты

| Артефакт | Статус | Что зафиксировано |
|----------|--------|-------------------|
| `eval/gold_questions.json` | stable seed spec | `schema_version=gold_questions.v2`, 4 official MVP questions, 12 corpus regression questions |
| `demo/official_questions.md` | stable mirror | Ссылается на `eval/gold_questions.json` как источник истины для `official-001` ... `official-004` |
| `eval/run_eval.py` | usable runner | Прогоняет `/api/query`, считает evidence-first/top-1 метрики, пишет Markdown/JSON в `eval/reports/latest.*` и timestamped копии |
| `eval/gold_mining.py` | dev-only generator | Генерирует corpus-derived candidates из `NormalizedDocument.source_spans`; выход не является baseline без review |
| `eval/yandex_disk_corpus.py` | floating corpus helper | Скачивает публичный Yandex Disk corpus; результат зависит от внешнего ресурса и локального состояния |
| `demo/seed_data/mvp_normalized_documents.json` | minimal seed corpus | 4 normalized documents, 4 source spans, 4 tables, 4 claims |
| `scripts/eval_yandex_live.py` | opt-in live smoke | Требует `RUN_MODEL_TESTS=1`, auth login и поднятый стек; проверяет only official questions |
| `scripts/eval_auth_token.py` | operational helper | Получает token для ручного `EVAL_AUTH_TOKEN` |
| `Makefile eval` | local command | Запускает `eval/run_eval.py` с `--official-only` и token из `EVAL_AUTH_TOKEN` |

## Текущая eval coverage

| Набор | Кол-во | Evidence expectation | Ограничения |
|-------|--------|----------------------|-------------|
| Official MVP | 4 | `expected_source_span_ids` пустые у всех 4 | Нельзя измерить real citation/evidence recall against gold spans |
| Corpus regression | 12 | У всех есть один `expected_source_span_id` | Только 6 уникальных текстов вопросов; большая часть вопросов про один документ `Cerro Matoso` |
| Numeric checks | 6 вопросов | `official-001` + 5 corpus questions | Проверка ищет значения/units в JSON ответа, а не нормализованный fact graph |
| Geo checks | 1 вопрос | `official-004` | Только expected strings `Россия`, `зарубежная практика` |
| Time checks | 1 вопрос | `official-003` | `relative_years=5` есть в gold, но нет pinned source spans |

## Что можно считать baseline сейчас

- Список official MVP questions: `official-001` ... `official-004`.
- Схему gold dataset `gold_questions.v2` как входной формат для E4/E6.
- Метрики runner-а как стартовый набор: `citation_coverage`, `numeric_correctness`, `query_ir_constraint_recall`, `evidence_recall_at_k`, `unsupported_claim_rate`, `answer_completeness`, `geo_correctness`, `access_leak_rate`, `jsonld_provenance_coverage`, `query_trace_completeness`, latency p50/p95.
- Минимальный local command contract: `make eval` для official-only и `python eval/run_eval.py --documents ...` для расширенного прогона.

## Что плавающее

- `eval/reports/latest.*` генерируется локально и сейчас не зафиксирован в репозитории.
- Yandex Disk corpus зависит от внешнего URL и не имеет committed manifest/checksum в текущем дереве.
- Live eval зависит от поднятого Docker stack, seeded auth, `EVAL_AUTH_TOKEN`, Yandex secrets и состояния Qdrant/Neo4j.
- `make eval` по умолчанию не передаёт `--documents`, поэтому не фиксирует input corpus в metadata, кроме `input_documents_count=0`.
- `scripts/eval_yandex_live.py` использует gateway payload shape напрямую и не пишет versioned report в `eval/reports/`.

## Что нельзя считать baseline

- Official questions как evidence baseline: у них нет `expected_source_span_ids`.
- Corpus regression как полноценный Top-1 benchmark: набор узкий, auto-mined и требует human review.
- `unsupported_claim_rate` как строгую метрику качества ответа: сейчас это rough count по точкам/точкам с запятой и числу warnings.
- `answer_completeness` как semantic metric: сейчас это substring match по `answer_outline`.
- Отчёты `eval/reports/*` как командный артефакт: директория описана в документации, но committed report отсутствует.

## Gaps для следующих этапов

### Pinned demo artifact

- Зафиксировать versioned eval report: `eval/reports/<run_id>.json`, `<run_id>.md` и обновляемый `latest.*`.
- Добавить manifest для input corpus: file list, sha256, source URL или локальный seed version, timestamp, service URLs, feature flags.
- В report metadata включать git commit, branch, `gold_questions` schema/version, corpus checksum, official-only/full-suite mode.

### Official questions

- Для каждого `official-*` добавить reviewed expected evidence: `expected_source_span_ids` или отдельный reviewed mapping file, если source ids зависят от ingestion.
- Разделить official suite на semantic/numeric/time/geo/comparative tags, чтобы E4 мог включать selective gates.
- Для `official-003` зафиксировать абсолютный evaluation window на дату прогона или правило вычисления `relative_years`.

### Unsupported claims

- Ввести reviewed negative cases: вопросы, где корректный ответ должен вернуть gaps/limitations без confirmed claims.
- Сделать метрику unsupported claims зависимой от answer payload layers, а не только от warning count.
- Проверять, что candidate/unsupported layer не попадает в confirmed facts без `SourceSpan`.

### Evidence coverage

- Для official suite нужен non-empty expected evidence set, иначе `citation_coverage` превращается в проверку наличия любого evidence.
- Для corpus suite нужно расширить source diversity: несколько документов, таблицы, measurements, claims, geo/time examples.
- Добавить отдельный access filtering fixture с `expected_forbidden_source_span_ids`, чтобы `access_leak_rate=0.0` стал обязательным gate.

## Рекомендация для E4/E6 quality gate

E4 должен сделать обязательными:

- `git diff --check`.
- Unit/integration tests для eval runner: `python -m pytest tests/integration/test_eval_runner.py tests/integration/test_access_leak.py`.
- Official-only eval smoke на поднятом seeded stack: `make eval`.
- Full eval с pinned corpus и metadata: `python eval/run_eval.py --documents <pinned_manifest_or_seed> --output-base eval/reports/<run_id>`.
- Проверку committed report schema: `schema_version=ml_eval_report.v1`, `total_questions`, `answered_200`, `with_evidence`, `dashboard_data.metric_status`.

E6 должен сделать обязательными:

- Official questions pass/fail без degraded fallback.
- `citation_coverage >= 0.8` только после заполнения official expected spans.
- `unsupported_claim_rate <= 0.1` с layer-aware подсчётом.
- `access_leak_rate == 0.0` на dedicated access suite.
- `jsonld_provenance_coverage == 1.0` для export-ready path.
- p95 latency threshold для live stack, сейчас runner уже считает `latency_ms_p95`.

## Связанные проверки в коде

- `tests/integration/test_eval_runner.py` покрывает `build_report` dashboard data и нормализацию raw eval documents через ingestion.
- `tests/integration/test_access_leak.py` покрывает `access_leak_rate` и сбор source span ids.
- `tests/e2e/test_official_questions_smoke.py` проверяет наличие core metrics в report builder.
